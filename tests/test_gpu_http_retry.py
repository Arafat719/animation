from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient

from animation_studio.providers.gpu import GPUJobRequest, GPUProviderError, MockGPUProvider
from animation_studio.providers.gpu_http import HTTPGPUProvider
from animation_studio.workers.mock_gpu import create_app

REQUEST = GPUJobRequest(
    operation='mock.noop', prompt='নদী', model_name='mock-worker', model_version='1'
)


@pytest.fixture
def bridge():
    worker = MockGPUProvider()
    with TestClient(create_app(token='test-token', provider=worker)) as api:

        def forward(request):
            response = api.request(
                request.method,
                request.url.path,
                content=request.content,
                headers=dict(request.headers),
            )
            return httpx.Response(response.status_code, content=response.content)

        yield worker, forward


def test_response_lost_after_submission_creates_one_job(bridge):
    worker, forward = bridge
    calls = []

    def transport(request):
        calls.append(request.headers['Idempotency-Key'])
        response = forward(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout('response lost')
        return response

    with HTTPGPUProvider(
        'http://127.0.0.1',
        token='test-token',
        backoff_seconds=0,
        transport=httpx.MockTransport(transport),
    ) as provider:
        job = provider.submit(REQUEST, idempotency_key='retained-key')
        assert calls == ['retained-key', 'retained-key']
        assert job.job_id == 'mock-gpu-1'
        assert provider.submit(REQUEST, idempotency_key='retained-key') == job
        with pytest.raises(GPUProviderError) as error:
            provider.submit(
                REQUEST.model_copy(update={'prompt': 'different'}), idempotency_key='retained-key'
            )
        assert error.value.code == 'idempotency_conflict'
    assert worker.submit(REQUEST).job_id == 'mock-gpu-2'


def test_end_to_end_boundary(bridge):
    worker, forward = bridge
    with HTTPGPUProvider(
        'http://127.0.0.1', token='test-token', transport=httpx.MockTransport(forward)
    ) as provider:
        assert provider.health_check().healthy
        assert provider.capabilities().operations == ('mock.noop',)
        first = provider.submit(REQUEST)
        second = provider.submit(REQUEST)
        assert first.job_id != second.job_id
        worker.advance(first.job_id)
        assert provider.status(first.job_id).progress == 50
        assert provider.cancel(first.job_id).status == 'cancelled'
        assert provider.cancel(first.job_id).status == 'cancelled'
        assert provider.status(second.job_id).status == 'queued'


def test_atomic_concurrent_replay(bridge):
    worker, forward = bridge

    def submit(_):
        with HTTPGPUProvider(
            'http://127.0.0.1', token='test-token', transport=httpx.MockTransport(forward)
        ) as provider:
            return provider.submit(REQUEST, idempotency_key='same-key').job_id

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert set(pool.map(submit, range(8))) == {'mock-gpu-1'}
    assert worker.submit(REQUEST).job_id == 'mock-gpu-2'


@pytest.mark.parametrize('failure', ['connect', 'read', 429, 502, 503, 504])
def test_transient_failure_retry_cap_and_backoff(failure, monkeypatch):
    calls, sleeps = [], []
    monkeypatch.setattr('animation_studio.providers.gpu_http.time.sleep', sleeps.append)

    def transport(request):
        calls.append(request)
        if failure == 'connect':
            raise httpx.ConnectError('secret must not escape')
        if failure == 'read':
            raise httpx.ReadTimeout('secret must not escape')
        return httpx.Response(failure)

    with (
        HTTPGPUProvider(
            'http://127.0.0.1', token='test-token', transport=httpx.MockTransport(transport)
        ) as provider,
        pytest.raises(GPUProviderError) as error,
    ):
        provider.health_check()
    assert error.value.code == ('timeout' if failure in ('read', 504) else 'unavailable')
    assert 'secret' not in str(error.value)
    assert len(calls) == 3 and sleeps == [0.1, 0.2]
    assert all(0 < call.extensions['timeout']['connect'] <= 10 for call in calls)


@pytest.mark.parametrize(
    'status,code',
    [
        (401, 'unauthorized'),
        (403, 'unauthorized'),
        (404, 'not_found'),
        (409, 'idempotency_conflict'),
        (422, 'invalid_input'),
        (500, 'invalid_response'),
        (302, 'invalid_response'),
    ],
)
def test_permanent_errors_not_retried(status, code):
    calls = []

    def transport(request):
        calls.append(request)
        return httpx.Response(status)

    with (
        HTTPGPUProvider(
            'http://127.0.0.1', token='test-token', transport=httpx.MockTransport(transport)
        ) as provider,
        pytest.raises(GPUProviderError) as error,
    ):
        provider.health_check()
    assert error.value.code == code and len(calls) == 1


def test_elapsed_budget_stops_before_retry(monkeypatch):
    now = [0.0]
    calls = []
    monkeypatch.setattr('animation_studio.providers.gpu_http.time.monotonic', lambda: now[0])

    def transport(request):
        calls.append(request)
        now[0] += 0.95
        raise httpx.ReadTimeout('lost')

    with (
        HTTPGPUProvider(
            'http://127.0.0.1', token='test-token', transport=httpx.MockTransport(transport)
        ) as provider,
        pytest.raises(GPUProviderError) as error,
    ):
        provider.health_check(timeout_seconds=1)
    assert error.value.code == 'timeout' and len(calls) == 1


@pytest.mark.parametrize('body', [b'not-json', b'{}', b'{"healthy":true}'])
def test_invalid_response_not_retried(body):
    calls = []

    def transport(request):
        calls.append(request)
        return httpx.Response(200, content=body)

    with (
        HTTPGPUProvider(
            'http://127.0.0.1', token='test-token', transport=httpx.MockTransport(transport)
        ) as provider,
        pytest.raises(GPUProviderError) as error,
    ):
        provider.health_check()
    assert error.value.code == 'invalid_response' and len(calls) == 1


@pytest.mark.parametrize('key', ['', 'bad key', 'x' * 129])
def test_invalid_key_is_rejected_without_submission(bridge, key):
    worker, forward = bridge
    with (
        HTTPGPUProvider(
            'http://127.0.0.1', token='test-token', transport=httpx.MockTransport(forward)
        ) as provider,
        pytest.raises(GPUProviderError),
    ):
        provider.submit(REQUEST, idempotency_key=key)
    assert worker.submit(REQUEST).job_id == 'mock-gpu-1'


@pytest.mark.parametrize('timeout', [True, 0, -1, float('nan'), float('inf')])
def test_invalid_timeout(timeout):
    def forbidden(_):
        pytest.fail('Invalid timeout must not send a request')

    with (
        HTTPGPUProvider(
            'http://127.0.0.1', token='test-token', transport=httpx.MockTransport(forbidden)
        ) as provider,
        pytest.raises(GPUProviderError) as error,
    ):
        provider.health_check(timeout_seconds=timeout)
    assert error.value.code == 'invalid_input'


@pytest.mark.parametrize(
    'url',
    [
        'http://remote.example',
        'https://user:pass@example.com',
        'https://example.com/path',
        'https://example.com?token=x',
    ],
)
def test_unsafe_origin_rejected(url):
    with pytest.raises(ValueError):
        HTTPGPUProvider(url, token='test-token')


def test_real_socket_read_timeout():
    import socket
    from threading import Event, Thread

    stop = Event()
    accepted = Event()
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    listener.settimeout(2)

    def silent_peer():
        connection, _ = listener.accept()
        with connection:
            accepted.set()
            stop.wait(2)

    thread = Thread(target=silent_peer)
    thread.start()
    try:
        with (
            HTTPGPUProvider(
                f'http://127.0.0.1:{listener.getsockname()[1]}', token='test-token', max_retries=0
            ) as provider,
            pytest.raises(GPUProviderError) as error,
        ):
            provider.health_check(timeout_seconds=0.05)
        assert accepted.is_set()
        assert error.value.code == 'timeout'
    finally:
        stop.set()
        thread.join(3)
        listener.close()
        assert not thread.is_alive()


def test_cancel_response_lost_retries_safely(bridge):
    worker, forward = bridge
    calls = []

    def transport(request):
        response = forward(request)
        if request.url.path == '/cancel':
            calls.append(request)
            if len(calls) == 1:
                raise httpx.ReadError('lost cancel response')
        return response

    with HTTPGPUProvider(
        'http://127.0.0.1',
        token='test-token',
        backoff_seconds=0,
        transport=httpx.MockTransport(transport),
    ) as provider:
        job = provider.submit(REQUEST)
        assert provider.cancel(job.job_id).status == 'cancelled'
        assert worker.status(job.job_id).status == 'cancelled'
        assert len(calls) == 2


def test_late_response_is_not_success(monkeypatch):
    now = [0.0]
    monkeypatch.setattr('animation_studio.providers.gpu_http.time.monotonic', lambda: now[0])

    def transport(_):
        now[0] = 2
        return httpx.Response(
            200, json={'healthy': True, 'provider_name': 'mock', 'provider_version': '1'}
        )

    with (
        HTTPGPUProvider(
            'http://127.0.0.1', token='test-token', transport=httpx.MockTransport(transport)
        ) as provider,
        pytest.raises(GPUProviderError) as error,
    ):
        provider.health_check(timeout_seconds=1)
    assert error.value.code == 'timeout'
