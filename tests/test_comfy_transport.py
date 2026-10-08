import socket
import threading
import time
import traceback

import httpx
import pytest
from pydantic import SecretStr

from animation_studio.providers import comfy_transport as module
from animation_studio.providers.comfy_config import ComfyEndpointConfig
from animation_studio.providers.image import ImageProviderError

TOKEN = 'synthetic-private-token'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('No network allowed')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


def config():
    return ComfyEndpointConfig(origin='https://selected.invalid', token=SecretStr(TOKEN))


def client(handler):
    return module.create_mock_comfy_transport(config(), transport=httpx.MockTransport(handler))


def request(c, **kwargs):
    return c.request('POST', 'prompt', deadline=time.monotonic() + 2, payload={}, **kwargs)


def test_production_factory_no_dispatch(monkeypatch):
    seen = []
    original = httpx.HTTPTransport.__init__

    def init(self, **kwargs):
        seen.append(kwargs)
        original(self, **kwargs)

    monkeypatch.setattr(httpx.HTTPTransport, '__init__', init)
    monkeypatch.setenv('HTTPS_PROXY', 'https://foreign.invalid')
    c = module.create_comfy_transport(config())
    assert seen == [{'verify': True, 'trust_env': False, 'retries': 0}]
    assert not c.is_mock
    c.close()
    c.close()
    with pytest.raises(ImageProviderError, match='closed'):
        request(c)


def test_selected_origin_and_body():
    calls = []

    def handler(r):
        calls.append(r)
        assert str(r.url) == 'https://selected.invalid/prompt'
        assert r.headers['authorization'] == 'Bearer ' + TOKEN
        assert r.headers['accept-encoding'] == 'identity'
        assert r.content == b'{}'
        assert all(0 < n <= 2 for n in r.extensions['timeout'].values())
        return httpx.Response(200, content=b'{}', headers={'content-type': 'application/json'})

    c = client(handler)
    try:
        result = request(c)
        assert result.content == b'{}' and result.content_type == 'application/json'
        assert c.is_mock and len(calls) == 1
    finally:
        c.close()


@pytest.mark.parametrize('status', [301, 302, 307, 308, 401, 403, 429, 500])
def test_no_redirect_or_retry(status):
    calls = []

    def handler(r):
        calls.append(r)
        return httpx.Response(status, headers={'location': 'https://foreign.invalid/' + TOKEN})

    c = client(handler)
    try:
        with pytest.raises(ImageProviderError) as error:
            request(c)
        assert len(calls) == 1
        assert TOKEN not in ''.join(traceback.format_exception(error.value))
    finally:
        c.close()


@pytest.mark.parametrize('error_type', [httpx.ConnectError, httpx.ReadError, httpx.ReadTimeout])
def test_transport_error_sanitized(error_type):
    calls = []

    def handler(r):
        calls.append(r)
        raise error_type(TOKEN)

    c = client(handler)
    try:
        with pytest.raises(ImageProviderError) as caught:
            request(c)
        assert TOKEN not in ''.join(traceback.format_exception(caught.value))
        assert len(calls) == 1
    finally:
        c.close()


@pytest.mark.parametrize(
    'change',
    [
        {'path': '//foreign.invalid'},
        {'timeout': True},
        {'deadline': float('nan')},
        {'deadline': 0},
        {'method': 'DELETE'},
        {'params': {}},
    ],
)
def test_invalid_zero_dispatch(change):
    c = client(lambda r: pytest.fail('Must not dispatch'))
    try:
        with pytest.raises(ImageProviderError):
            c.request(
                **({'method': 'POST', 'path': 'prompt', 'deadline': time.monotonic() + 2} | change)
            )
    finally:
        c.close()


class Stream(httpx.SyncByteStream):
    def __init__(self, *, failure=None, close_failure=False):
        self.failure = failure
        self.close_failure = close_failure
        self.closed = 0

    def __iter__(self):
        yield b'x' * 65536
        if self.failure:
            raise self.failure

    def close(self):
        self.closed += 1
        if self.close_failure:
            raise OSError(TOKEN)


@pytest.mark.parametrize('failure', [None, httpx.ReadError(TOKEN), httpx.ReadTimeout(TOKEN)])
def test_stream_cleanup(failure):
    stream = Stream(failure=failure)
    c = client(lambda r: httpx.Response(200, stream=stream))
    try:
        if failure:
            with pytest.raises(ImageProviderError):
                request(c)
        else:
            assert len(request(c).content) == 65536
        assert stream.closed >= 1
    finally:
        c.close()


def test_primary_and_cleanup_retention():
    stream = Stream(close_failure=True)
    c = client(lambda r: httpx.Response(403, stream=stream))
    with pytest.raises(ImageProviderError, match='rejected') as caught:
        request(c)
    assert caught.value.cleanup_handle is c
    assert TOKEN not in ''.join(traceback.format_exception(caught.value))
    stream.close_failure = False
    c.close()
    assert stream.closed == 2
    c.close()


def test_client_close_failure_retry(monkeypatch):
    c = client(lambda r: httpx.Response(200))
    original = c._transport.close
    calls = []

    def fail():
        calls.append(1)
        raise OSError(TOKEN)

    monkeypatch.setattr(c._transport, 'close', fail)
    with pytest.raises(ImageProviderError) as caught:
        c.close()
    assert caught.value.cleanup_handle is c
    assert TOKEN not in ''.join(traceback.format_exception(caught.value))
    with pytest.raises(ImageProviderError, match='closed'):
        request(c)
    monkeypatch.setattr(c._transport, 'close', original)
    c.close()
    assert c._client_closed


def test_cancel_no_dispatch():
    event = threading.Event()
    event.set()
    c = client(lambda r: pytest.fail('Must not dispatch'))
    try:
        with pytest.raises(ImageProviderError) as caught:
            request(c, cancel=event)
        assert caught.value.code == 'cancelled'
    finally:
        c.close()


@pytest.mark.parametrize(
    'headers',
    [
        {'content-encoding': 'gzip'},
        {'content-length': '99999999999999999999'},
        {'content-length': 'bad'},
    ],
)
def test_response_header_rejection(headers):
    stream = Stream()
    c = client(lambda r: httpx.Response(200, headers=headers, stream=stream))
    try:
        with pytest.raises(ImageProviderError):
            request(c)
        assert stream.closed
    finally:
        c.close()


def test_stream_cap(monkeypatch):
    monkeypatch.setattr(module, 'MAX_RESPONSE_BYTES', 10)
    stream = Stream()
    c = client(lambda r: httpx.Response(200, stream=stream))
    try:
        with pytest.raises(ImageProviderError, match='too large'):
            request(c)
        assert stream.closed
    finally:
        c.close()


def test_deadline_after_dispatch(monkeypatch):
    clock = [1.0]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    stream = Stream()

    def handler(r):
        clock[0] = 3
        return httpx.Response(200, stream=stream)

    c = client(handler)
    try:
        with pytest.raises(ImageProviderError) as caught:
            c.request('GET', 'object_info/SaveImage', deadline=2)
        assert caught.value.code == 'timeout'
        assert stream.closed
    finally:
        c.close()


@pytest.mark.parametrize('stop_kind', ['deadline', 'cancel'])
def test_stop_during_stream_closes_response(monkeypatch, stop_kind):
    clock = [1.0]
    event = threading.Event()
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])

    class SlowStream(Stream):
        def __iter__(self):
            yield b'x' * 65536
            if stop_kind == 'deadline':
                clock[0] = 3.0
            else:
                event.set()
            yield b'y' * 65536

    stream = SlowStream()
    c = client(lambda r: httpx.Response(200, stream=stream))
    try:
        with pytest.raises(ImageProviderError) as caught:
            c.request('GET', 'object_info/SaveImage', deadline=2, cancel=event)
        assert caught.value.code == ('timeout' if stop_kind == 'deadline' else 'cancelled')
        assert stream.closed
    finally:
        c.close()


def test_interrupt_preserved_and_response_closed():
    failure = KeyboardInterrupt()
    stream = Stream(failure=failure)
    c = client(lambda r: httpx.Response(200, stream=stream))
    try:
        with pytest.raises(KeyboardInterrupt) as caught:
            request(c)
        assert caught.value is failure
        assert stream.closed
    finally:
        c.close()


def test_live_boundary_not_accepted_by_existing_executor():
    from animation_studio.providers.comfy_http import ComfyHTTPExecutor

    c = module.create_comfy_transport(config())
    try:
        with pytest.raises(TypeError):
            ComfyHTTPExecutor(authenticated_client=c)
    finally:
        c.close()
