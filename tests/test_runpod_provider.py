import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from animation_studio.providers.gpu import GPUProviderError
from animation_studio.providers.runpod import RunPodGPUProvider
from animation_studio.workers.mock_gpu import create_app

# Run the same boundary checks against the adapter, not copies of assertions.
from tests.test_gpu_provider import (  # noqa: F401
    request_model,
    test_contract_invalid_deadline,
    test_contract_submit_status_cancel,
    test_contract_unknown_job,
)


@pytest.fixture
def provider():
    with TestClient(create_app(token='worker-fixture')) as app:

        def worker(request):
            assert request.url.host == 'fixturepod-8091.proxy.runpod.net'
            assert request.headers['Authorization'] == 'Bearer worker-fixture'
            response = app.request(
                request.method,
                request.url.path,
                content=request.content,
                headers=dict(request.headers),
            )
            return httpx.Response(response.status_code, content=response.content)

        def control(request):
            assert str(request.url) == 'https://rest.runpod.io/v1/pods/fixturepod'
            assert request.method == 'GET'
            assert request.headers['Authorization'] == 'Bearer api-fixture'
            return httpx.Response(
                200,
                json={
                    'id': 'fixturepod',
                    'desiredStatus': 'RUNNING',
                    'env': {'PRIVATE': 'not-returned'},
                },
            )

        with make(control, worker) as adapter:
            yield adapter


def make(control, worker=lambda _: httpx.Response(503)):
    return RunPodGPUProvider(
        pod_id='fixturepod',
        worker_port=8091,
        api_key=SecretStr('api-fixture'),
        worker_token=SecretStr('worker-fixture'),
        control_transport=httpx.MockTransport(control),
        worker_transport=httpx.MockTransport(worker),
    )


def test_snapshot_allowlists_metadata(provider):
    result = provider.pod_snapshot()
    assert result.model_dump() == {'pod_id': 'fixturepod', 'desired_status': 'RUNNING'}
    assert 'not-returned' not in repr(result)


@pytest.mark.parametrize('state', ['EXITED', 'TERMINATED', 'FUTURE_STATE'])
def test_desired_state_is_not_worker_health(state):
    with make(
        lambda _: httpx.Response(200, json={'id': 'fixturepod', 'desiredStatus': state})
    ) as adapter:
        assert adapter.pod_snapshot().desired_status == (
            state if state != 'FUTURE_STATE' else 'UNKNOWN'
        )


@pytest.mark.parametrize(
    'status,code',
    [
        (401, 'unauthorized'),
        (403, 'unauthorized'),
        (404, 'not_found'),
        (429, 'unavailable'),
        (503, 'unavailable'),
        (504, 'timeout'),
        (302, 'invalid_response'),
    ],
)
def test_control_errors_no_retry(status, code):
    calls = []

    def control(request):
        calls.append(request)
        return httpx.Response(status, text='secret-error-body')

    with make(control) as adapter, pytest.raises(GPUProviderError) as error:
        adapter.pod_snapshot()
    assert error.value.code == code and len(calls) == 1
    assert 'secret-error-body' not in str(error.value)


@pytest.mark.parametrize(
    'body',
    [
        [],
        {},
        {'id': 'other', 'desiredStatus': 'RUNNING'},
        {'id': 'fixturepod'},
        {'id': 'fixturepod', 'desiredStatus': None},
    ],
)
def test_invalid_metadata(body):
    with (
        make(lambda _: httpx.Response(200, json=body)) as adapter,
        pytest.raises(GPUProviderError) as error,
    ):
        adapter.pod_snapshot()
    assert error.value.code == 'invalid_response'


@pytest.mark.parametrize(
    'exception,code', [(httpx.ReadTimeout, 'timeout'), (httpx.ConnectError, 'unavailable')]
)
def test_transport_error(exception, code):
    def control(_):
        raise exception('private-details')

    with make(control) as adapter, pytest.raises(GPUProviderError) as error:
        adapter.pod_snapshot()
    assert error.value.code == code
    assert 'private-details' not in str(error.value)


def test_live_transport_and_env_disabled():
    with pytest.raises(TypeError, match='mock transports'):
        RunPodGPUProvider(
            pod_id='fixturepod',
            worker_port=8091,
            api_key=SecretStr('api'),
            worker_token=SecretStr('worker'),
            control_transport=None,
            worker_transport=None,
        )
    with pytest.raises(ValueError, match='fixture credentials'):
        RunPodGPUProvider.from_env('https://example.com')


@pytest.mark.parametrize('timeout', [0, -1, True, float('nan'), float('inf')])
def test_invalid_timeout_no_request(timeout):
    def forbidden(_):
        pytest.fail('Must not send')

    with make(forbidden) as adapter, pytest.raises(GPUProviderError) as error:
        adapter.pod_snapshot(timeout_seconds=timeout)
    assert error.value.code == 'invalid_input'
