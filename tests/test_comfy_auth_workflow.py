import hashlib

import httpx
import pytest
from pydantic import SecretStr
from test_comfy_http import PROMPT_ID, Server

from animation_studio.providers.comfy_auth import MockComfyAuthenticatedClient
from animation_studio.providers.comfy_config import ComfyEndpointConfig
from animation_studio.providers.comfy_durable_image import DurableComfyImageProvider
from animation_studio.providers.comfy_http import ComfyHTTPExecutor
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_journal import _fingerprint
from animation_studio.providers.comfy_v2_executor import DurableComfyExecutorV2
from animation_studio.providers.comfy_workflow import (
    MODEL_NAME,
    MODEL_VERSION,
    build_image_workflow,
)
from animation_studio.providers.image import ImageProviderError, ImageRequest


def test_authenticated_durable_image_and_recovery(tmp_path, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('No sockets')

    monkeypatch.setattr(socket, 'socket', forbidden)
    tmp_path.chmod(0o700)
    request = ImageRequest(
        prompt='A house', model_name=MODEL_NAME, model_version=MODEL_VERSION, seed=42
    )
    graph = build_image_workflow(request)
    server = Server(graph)

    def handler(req):
        assert req.url.host == 'selected.invalid'
        assert req.headers['authorization'] == 'Bearer synthetic-token'
        return server(req)

    client = MockComfyAuthenticatedClient(
        ComfyEndpointConfig(origin='https://selected.invalid', token=SecretStr('synthetic-token')),
        transport=httpx.MockTransport(handler),
    )
    executor = ComfyHTTPExecutor(authenticated_client=client)
    context = ComfyExecutionContext(
        mode='mock',
        job_id=PROMPT_ID,
        graph_sha256=_fingerprint(graph),
        origin=executor.origin,
        deployment_id=PROMPT_ID,
        runtime_manifest_sha256='a' * 64,
        model_manifest_sha256='b' * 64,
    )
    durable = DurableComfyExecutorV2(executor, tmp_path, context)
    provider = DurableComfyImageProvider(durable, tmp_path / 'output')
    try:
        first = provider.generate(request)
        saved = durable.store.path.read_bytes()
        assert b'synthetic-token' not in saved
        server.calls.clear()
        recovered = provider.recover(request)
        assert recovered.is_mock and recovered.path != first.path
        assert recovered.sha256 == hashlib.sha256(server.png).hexdigest()
        assert all(r.method == 'GET' for r in server.calls)
        assert durable.store.path.read_bytes() == saved
        with pytest.raises(ValueError):
            DurableComfyExecutorV2(
                executor,
                tmp_path,
                context.model_copy(update={'origin': 'https://other.invalid:443/'}),
            )
    finally:
        executor.close()


@pytest.mark.parametrize(
    'params',
    [
        None,
        {'filename': '../secret', 'subfolder': '', 'type': 'output'},
        {'filename': 'animation_sdxl_turbo_x.png', 'subfolder': '../', 'type': 'output'},
        {'filename': 'animation_sdxl_turbo_x.png', 'subfolder': '', 'type': 'input'},
        {
            'filename': 'animation_sdxl_turbo_x.png',
            'subfolder': '',
            'type': 'output',
            'token': 'secret',
        },
        {},
        [],
    ],
)
def test_invalid_view_before_auth_dispatch(params):
    calls = []
    client = MockComfyAuthenticatedClient(
        ComfyEndpointConfig(origin='https://selected.invalid', token=SecretStr('synthetic')),
        transport=httpx.MockTransport(lambda r: calls.append(r)),
    )
    try:
        with pytest.raises(ImageProviderError), client.stream('GET', 'view', params=params):
            pass
        assert not calls
    finally:
        client.close()


@pytest.mark.parametrize('stage', ['preflight', 'submit', 'recovery'])
@pytest.mark.parametrize('status', [302, 401, 403])
def test_auth_failure_preserves_durable_contract(tmp_path, stage, status):
    tmp_path.chmod(0o700)
    graph = build_image_workflow(
        ImageRequest(prompt='A house', model_name=MODEL_NAME, model_version=MODEL_VERSION, seed=42)
    )
    server = Server(graph)
    failing = False

    def handler(req):
        assert req.url.host == 'selected.invalid'
        assert req.headers['authorization'] == 'Bearer synthetic-token'
        if failing:
            server.calls.append(req)
            return httpx.Response(
                status, text='synthetic-token', headers={'Location': 'https://other.invalid/'}
            )
        if stage == 'preflight' or (stage == 'submit' and req.url.path == '/prompt'):
            server.calls.append(req)
            return httpx.Response(status, text='synthetic-token')
        return server(req)

    client = MockComfyAuthenticatedClient(
        ComfyEndpointConfig(origin='https://selected.invalid', token=SecretStr('synthetic-token')),
        transport=httpx.MockTransport(handler),
    )
    executor = ComfyHTTPExecutor(authenticated_client=client)
    context = ComfyExecutionContext(
        mode='mock',
        job_id=PROMPT_ID,
        graph_sha256=_fingerprint(graph),
        origin=executor.origin,
        deployment_id=PROMPT_ID,
        runtime_manifest_sha256='a' * 64,
        model_manifest_sha256='b' * 64,
    )
    durable = DurableComfyExecutorV2(executor, tmp_path, context)
    try:
        saved = None
        if stage == 'recovery':
            durable.execute(graph)
            saved = durable.store.path.read_bytes()
            server.calls.clear()
            failing = True
        with pytest.raises(ImageProviderError) as caught:
            if stage == 'recovery':
                durable.recover(graph)
            else:
                durable.execute(graph)
        assert 'synthetic-token' not in str(caught.value)
        if stage == 'preflight':
            assert not durable.store.path.exists()
            assert len(server.calls) == 1
        elif stage == 'submit':
            with durable.store.locked():
                assert durable.store.read().state == 'intent'
            assert sum(req.method == 'POST' for req in server.calls) == 1
            count = len(server.calls)
            with pytest.raises(ImageProviderError):
                durable.execute(graph)
            with pytest.raises(ImageProviderError):
                durable.recover(graph)
            assert len(server.calls) == count
        else:
            assert durable.store.path.read_bytes() == saved
            assert len(server.calls) == 1 and server.calls[0].method == 'GET'
    finally:
        executor.close()
