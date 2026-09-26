import httpx
import pytest
from pydantic import SecretStr

from animation_studio.providers.gpu import GPUProviderError
from animation_studio.providers.runpod_lifecycle import RunPodLifecycle


def adapter(handler):
    return RunPodLifecycle(
        pod_id='fixture123',
        api_key=SecretStr('fixture-secret'),
        transport=httpx.MockTransport(handler),
    )


def test_protocol_and_followup_observation():
    requests = []
    responses = iter(
        [
            httpx.Response(200, json={'id': 'fixture123', 'desiredStatus': 'RUNNING'}),
            httpx.Response(200),
            httpx.Response(204),
            httpx.Response(404),
        ]
    )

    def handle(request):
        requests.append((request.method, str(request.url)))
        assert request.headers['authorization'] == 'Bearer fixture-secret'
        assert request.extensions['timeout']['read'] == 10
        return next(responses)

    client = adapter(handle)
    try:
        assert client.inspect().desired_status == 'RUNNING'
        assert client.stop() is None
        assert client.terminate() is None
        observation = client.inspect()
        assert observation.present is False
        assert observation.desired_status is None
        base = 'https://rest.runpod.io/v1/pods/fixture123'
        assert requests == [
            ('GET', base),
            ('POST', base + '/stop'),
            ('DELETE', base),
            ('GET', base),
        ]
    finally:
        client.close()


@pytest.mark.parametrize('operation', ['inspect', 'stop', 'terminate'])
@pytest.mark.parametrize(
    'status,code',
    [
        (401, 'unauthorized'),
        (403, 'unauthorized'),
        (429, 'unavailable'),
        (503, 'unavailable'),
        (504, 'timeout'),
        (302, 'invalid_response'),
        (202, 'invalid_response'),
    ],
)
def test_rejection_single_attempt_and_no_body_leak(operation, status, code):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(
            status, text='fixture-secret', headers={'location': 'https://elsewhere.test'}
        )

    client = adapter(handle)
    try:
        with pytest.raises(GPUProviderError) as error:
            getattr(client, operation)()
        assert error.value.code == code
        assert 'fixture-secret' not in str(error.value)
        assert len(calls) == 1
    finally:
        client.close()


@pytest.mark.parametrize('operation', ['inspect', 'stop', 'terminate'])
@pytest.mark.parametrize(
    'exception,code', [(httpx.ReadTimeout, 'timeout'), (httpx.ConnectError, 'unavailable')]
)
def test_ambiguous_failure_never_retries(operation, exception, code):
    calls = []

    def handle(request):
        calls.append(request)
        raise exception('fixture-secret', request=request)

    client = adapter(handle)
    try:
        with pytest.raises(GPUProviderError) as error:
            getattr(client, operation)()
        assert error.value.code == code
        assert 'fixture-secret' not in str(error.value)
        assert len(calls) == 1
    finally:
        client.close()


@pytest.mark.parametrize(
    'body',
    [
        [],
        {},
        {'id': 'other', 'desiredStatus': 'EXITED'},
        {'id': 'fixture123', 'desiredStatus': None},
        {'id': 'fixture123', 'desiredStatus': ' '},
    ],
)
def test_invalid_observation(body):
    client = adapter(lambda _: httpx.Response(200, json=body))
    try:
        with pytest.raises(GPUProviderError, match='Invalid lifecycle observation'):
            client.inspect()
    finally:
        client.close()


@pytest.mark.parametrize('operation', ['stop', 'terminate'])
def test_missing_mutation_target_is_not_success(operation):
    client = adapter(lambda _: httpx.Response(404))
    try:
        with pytest.raises(GPUProviderError) as error:
            getattr(client, operation)()
        assert error.value.code == 'not_found'
    finally:
        client.close()


@pytest.mark.parametrize('timeout', [True, 0, -1, float('nan'), float('inf'), '10'])
def test_invalid_timeout_without_request(timeout):
    def forbidden(_):
        pytest.fail('Unexpected request')

    client = adapter(forbidden)
    try:
        with pytest.raises(GPUProviderError) as error:
            client.stop(timeout_seconds=timeout)
        assert error.value.code == 'invalid_input'
    finally:
        client.close()


def test_live_transport_rejected():
    with pytest.raises(TypeError, match='mock transport'):
        RunPodLifecycle(pod_id='fixture123', api_key=SecretStr('fixture'), transport=None)


@pytest.mark.parametrize('pod_id', ['', '../other', 'a/b', 'A123', None])
def test_invalid_target(pod_id):
    with pytest.raises(ValueError, match='Pod ID'):
        RunPodLifecycle(
            pod_id=pod_id,
            api_key=SecretStr('fixture'),
            transport=httpx.MockTransport(lambda _: httpx.Response(200)),
        )
