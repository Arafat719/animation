import socket

import httpx
import pytest
from pydantic import SecretStr
from test_comfy_http import Server
from test_comfy_http import graph as graph_fixture

from animation_studio.providers.comfy_config import ComfyEndpointConfig
from animation_studio.providers.comfy_http import ComfyExecutionError, ComfyHTTPExecutor
from animation_studio.providers.comfy_transport import (
    create_comfy_transport,
    create_mock_comfy_transport,
)

graph = graph_fixture


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('No network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


def config():
    return ComfyEndpointConfig(
        origin='https://selected.invalid', token=SecretStr('synthetic-token')
    )


@pytest.mark.parametrize('forged', [False, True])
def test_live_rejected_even_with_forged_label(forged):
    boundary = create_comfy_transport(config())
    try:
        if forged:
            boundary._is_mock = True
        with pytest.raises(TypeError):
            ComfyHTTPExecutor(transport_client=boundary)
    finally:
        boundary.close()


def test_label_readonly_and_conflicting_clients_rejected():
    boundary = create_mock_comfy_transport(config(), transport=httpx.MockTransport(lambda r: None))
    try:
        with pytest.raises(AttributeError):
            boundary.is_mock = False
        with pytest.raises(TypeError):
            ComfyHTTPExecutor(
                transport_client=boundary, transport=httpx.MockTransport(lambda r: None)
            )
    finally:
        boundary.close()


def test_provenance_rechecked_before_request(graph):
    calls = []
    boundary = create_mock_comfy_transport(
        config(), transport=httpx.MockTransport(lambda r: calls.append(r))
    )
    executor = ComfyHTTPExecutor(transport_client=boundary)
    try:
        boundary._is_mock = False
        with pytest.raises(TypeError):
            executor.execute(graph)
        assert not calls
    finally:
        executor.close()


def test_cleanup_handle_survives_executor_error(graph):
    class BrokenStream(httpx.SyncByteStream):
        broken = True

        def __iter__(self):
            yield b''

        def close(self):
            if self.broken:
                raise OSError('synthetic-private-cleanup')

    stream = BrokenStream()
    boundary = create_mock_comfy_transport(
        config(), transport=httpx.MockTransport(lambda r: httpx.Response(403, stream=stream))
    )
    executor = ComfyHTTPExecutor(transport_client=boundary)
    try:
        with pytest.raises(ComfyExecutionError) as caught:
            executor.execute(graph)
        assert caught.value.cleanup_handle is boundary
        assert caught.value.receipt is None
        assert 'synthetic-private-cleanup' not in str(caught.value)
    finally:
        stream.broken = False
        executor.close()


def test_invalid_mime_rejected_without_reading_body(graph):
    class MustNotRead(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            pytest.fail('MIME must be checked before reading')
            yield b''

        def close(self):
            self.closed = True

    stream = MustNotRead()
    server = Server(graph)
    server.override = lambda r: httpx.Response(
        200, headers={'content-type': 'text/html'}, stream=stream
    )
    boundary = create_mock_comfy_transport(config(), transport=httpx.MockTransport(server))
    executor = ComfyHTTPExecutor(transport_client=boundary)
    try:
        with pytest.raises(ComfyExecutionError, match='content type'):
            executor.execute(graph)
        assert stream.closed and len(server.calls) == 1
    finally:
        executor.close()
