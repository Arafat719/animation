import logging
import traceback

import httpx
import pytest
from pydantic import SecretStr

from animation_studio.providers.comfy_auth import MockComfyAuthenticatedClient
from animation_studio.providers.comfy_config import ComfyEndpointConfig
from animation_studio.providers.image import ImageProviderError

TOKEN = 'synthetic-auth-token'


def config():
    return ComfyEndpointConfig(origin='https://selected.invalid', token=SecretStr(TOKEN))


def test_selected_origin_injection_no_sockets(monkeypatch, caplog):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('No network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setenv('HTTPS_PROXY', 'https://other.invalid')
    calls = []

    def handler(request):
        calls.append(request)
        assert request.headers['authorization'] == 'Bearer ' + TOKEN
        assert request.url.host == 'selected.invalid'
        assert request.url.scheme == 'https'
        return httpx.Response(200, content=b'{}')

    client = MockComfyAuthenticatedClient(config(), transport=httpx.MockTransport(handler))
    try:
        with caplog.at_level(logging.DEBUG):
            assert client.request('GET', 'object_info/SaveImage') == b'{}'
            assert client.request('POST', 'prompt', payload={'prompt': {}}) == b'{}'
        assert len(calls) == 2 and TOKEN not in caplog.text + repr(client)
    finally:
        client.close()


@pytest.mark.parametrize('status', [301, 302, 307, 308, 401, 403, 429, 500])
def test_reject_no_follow_retry_or_secret_error(status, caplog):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status, headers={'Location': 'https://other.invalid/' + TOKEN}, content=TOKEN.encode()
        )

    client = MockComfyAuthenticatedClient(config(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ImageProviderError) as error:
            client.request('POST', 'prompt', payload={})
        assert len(calls) == 1
        assert error.value.code == 'execution_failed'
        assert TOKEN not in str(error.value) + repr(error.value) + caplog.text
    finally:
        client.close()


@pytest.mark.parametrize(
    'error_type,code', [(httpx.ReadError, 'execution_failed'), (httpx.ReadTimeout, 'timeout')]
)
def test_transport_errors_sanitized(error_type, code):
    calls = []

    def handler(request):
        calls.append(request)
        raise error_type(TOKEN, request=request)

    client = MockComfyAuthenticatedClient(config(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ImageProviderError) as error:
            client.request('POST', 'prompt', payload={})
        assert error.value.code == code and len(calls) == 1
        assert TOKEN not in ''.join(traceback.format_exception(error.value))
    finally:
        client.close()


@pytest.mark.parametrize(
    'path',
    [
        'https://other.invalid/prompt',
        '//other.invalid/view',
        '/view',
        '../view',
        'view?token=x',
        'view#x',
        'view\\x',
        'view\n',
        'view%2f',
        '',
    ],
)
def test_route_injection_no_dispatch(path):
    calls = []
    client = MockComfyAuthenticatedClient(
        config(), transport=httpx.MockTransport(lambda r: calls.append(r))
    )
    try:
        with pytest.raises(ImageProviderError):
            client.request('GET', path)
        assert not calls
    finally:
        client.close()


def test_live_transport_rejected():
    with pytest.raises(TypeError):
        MockComfyAuthenticatedClient(config(), transport=None)


def test_response_cap():
    client = MockComfyAuthenticatedClient(
        config(),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, content=b'x' * (16 * 1024 * 1024 + 1))
        ),
    )
    try:
        with pytest.raises(ImageProviderError, match='too large'):
            client.request('GET', 'object_info/SaveImage')
    finally:
        client.close()
