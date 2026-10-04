import copy
import io
import json
from pathlib import Path
from threading import Event

import httpx
import pytest
from PIL import Image

from animation_studio.providers.comfy_http import MAX_JSON_BYTES, ComfyHTTPExecutor
from animation_studio.providers.comfy_image import ComfyImageProvider
from animation_studio.providers.comfy_workflow import (
    MODEL_NAME,
    MODEL_VERSION,
    build_image_workflow,
)
from animation_studio.providers.image import ImageProviderError, ImageRequest

PROMPT_ID = '12345678-1234-4234-8234-123456789abc'


@pytest.fixture
def graph():
    return build_image_workflow(
        ImageRequest(
            prompt='নদীর পাশে বাড়ি', model_name=MODEL_NAME, model_version=MODEL_VERSION, seed=42
        )
    )


def history(graph):
    return {
        PROMPT_ID: {
            'prompt': [0, PROMPT_ID, graph, {}, ['7']],
            'status': {'status_str': 'success', 'completed': True, 'messages': []},
            'outputs': {
                '7': {
                    'images': [
                        {
                            'filename': 'animation_sdxl_turbo_00001_.png',
                            'subfolder': '',
                            'type': 'output',
                        }
                    ]
                }
            },
        }
    }


class Server:
    def __init__(self, graph):
        self.graph = graph
        self.calls = []
        self.pending = 0
        self.history = history(graph)
        self.receipt = {'prompt_id': PROMPT_ID, 'number': 0, 'node_errors': {}}
        self.override = None
        content = io.BytesIO()
        Image.new('RGB', (512, 512)).save(content, format='PNG')
        self.png = content.getvalue()

    def __call__(self, request):
        self.calls.append(request)
        if self.override:
            result = self.override(request)
            if result is not None:
                return result
        if request.url.path.startswith('/object_info/'):
            inventory = json.loads(
                (Path(__file__).parent / 'fixtures/comfy_object_info.json').read_text()
            )
            kind = request.url.path.rsplit('/', 1)[1]
            return httpx.Response(200, json={kind: inventory[kind]} if kind in inventory else {})
        if request.url.path == '/prompt':
            assert request.method == 'POST'
            assert json.loads(request.content) == {'prompt': self.graph}
            return httpx.Response(200, json=self.receipt)
        if request.url.path == f'/history/{PROMPT_ID}':
            if self.pending:
                self.pending -= 1
                return httpx.Response(200, json={})
            return httpx.Response(200, json=self.history)
        if request.url.path == f'/api/jobs/{PROMPT_ID}/cancel':
            assert request.method == 'POST'
            return httpx.Response(200, json={'cancelled': True})
        assert request.url.path == '/view'
        assert dict(request.url.params) == self.history[PROMPT_ID]['outputs']['7']['images'][0]
        return httpx.Response(200, headers={'content-type': 'image/png'}, content=self.png)


@pytest.fixture(params=['plain', 'auth'])
def setup(graph, request):
    server = Server(graph)
    if request.param == 'plain':
        executor = ComfyHTTPExecutor(
            transport=httpx.MockTransport(server), poll_interval=0.001, max_polls=3
        )
    else:
        from pydantic import SecretStr

        from animation_studio.providers.comfy_auth import MockComfyAuthenticatedClient
        from animation_studio.providers.comfy_config import ComfyEndpointConfig

        client = MockComfyAuthenticatedClient(
            ComfyEndpointConfig(origin='https://selected.invalid', token=SecretStr('test-token')),
            transport=httpx.MockTransport(server),
        )
        executor = ComfyHTTPExecutor(authenticated_client=client, poll_interval=0.001, max_polls=3)
    yield server, executor
    executor.close()


def test_full_adapter_path(setup, graph, tmp_path, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('No real network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    server, executor = setup
    server.pending = 1
    result = ComfyImageProvider(executor, tmp_path).generate(
        ImageRequest(
            prompt=graph['2']['inputs']['text'],
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            seed=42,
        )
    )
    assert result.is_mock and result.path.read_bytes() == server.png
    assert result.seed == 42 and result.width == result.height == 512
    assert [r.url.path for r in server.calls] == [
        '/prompt',
        f'/history/{PROMPT_ID}',
        f'/history/{PROMPT_ID}',
        '/view',
    ]


@pytest.mark.parametrize(
    'receipt',
    [
        {},
        {'prompt_id': '../view'},
        {'prompt_id': PROMPT_ID, 'node_errors': {'7': {}}},
        {'prompt_id': PROMPT_ID, 'node_errors': {}, 'error': 'bad'},
        {'prompt_id': 4, 'node_errors': {}},
    ],
)
def test_bad_receipt(setup, graph, receipt):
    server, executor = setup
    server.receipt = receipt
    with pytest.raises(ImageProviderError):
        executor.execute(graph)
    assert len(server.calls) == 1


@pytest.mark.parametrize('status', [302, 400, 401, 403, 429, 500])
def test_http_rejection_no_retry_or_redirect(setup, graph, status):
    server, executor = setup
    server.override = lambda r: httpx.Response(
        status, headers={'location': 'https://other.invalid/'}
    )
    with pytest.raises(ImageProviderError) as caught:
        executor.execute(graph)
    assert caught.value.code == 'execution_failed'
    assert len(server.calls) == 1


@pytest.mark.parametrize(
    'failure,code', [(httpx.ReadTimeout, 'timeout'), (httpx.ConnectError, 'execution_failed')]
)
def test_ambiguous_submit_no_retry(setup, graph, failure, code):
    server, executor = setup

    def fail(request):
        raise failure('private details', request=request)

    server.override = fail
    with pytest.raises(ImageProviderError) as caught:
        executor.execute(graph)
    assert caught.value.code == code and 'private' not in str(caught.value)
    assert len(server.calls) == 1


@pytest.mark.parametrize('body', [b'[]', b'{', b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff'])
def test_bad_json(setup, graph, body):
    server, executor = setup
    server.override = lambda r: httpx.Response(
        200, headers={'content-type': 'application/json'}, content=body
    )
    with pytest.raises(ImageProviderError):
        executor.execute(graph)


@pytest.mark.parametrize(
    'change',
    [
        'wrong_id',
        'failed',
        'incomplete',
        'wrong_graph',
        'empty_images',
        'multiple_images',
        'wrong_node',
        'traversal',
        'subfolder',
        'input',
    ],
)
def test_invalid_history(setup, graph, change):
    server, executor = setup
    server.history = copy.deepcopy(server.history)
    entry = server.history[PROMPT_ID]
    reference = entry['outputs']['7']['images'][0]
    if change == 'wrong_id':
        entry['prompt'][1] = 'other'
    elif change == 'failed':
        entry['status']['status_str'] = 'error'
    elif change == 'incomplete':
        entry['status']['completed'] = False
    elif change == 'wrong_graph':
        entry['prompt'][2]['5']['inputs']['seed'] = 100
    elif change == 'empty_images':
        entry['outputs']['7']['images'] = []
    elif change == 'multiple_images':
        entry['outputs']['7']['images'].append(reference)
    elif change == 'wrong_node':
        entry['outputs']['6'] = entry['outputs'].pop('7')
    elif change == 'traversal':
        reference['filename'] = '../private.png'
    elif change == 'subfolder':
        reference['subfolder'] = '../'
    else:
        reference['type'] = 'input'
    with pytest.raises(ImageProviderError):
        executor.execute(graph)
    assert len(server.calls) == 2


def test_poll_bound(setup, graph):
    server, executor = setup
    server.pending = 100
    with pytest.raises(ImageProviderError) as caught:
        executor.execute(graph)
    assert caught.value.code == 'timeout'
    assert len(server.calls) == 5
    assert server.calls[-1].url.path == f'/api/jobs/{PROMPT_ID}/cancel'


@pytest.mark.parametrize('stage', ['before', '/prompt', f'/history/{PROMPT_ID}', '/view'])
def test_cancellation(setup, graph, stage):
    server, executor = setup
    cancel = Event()
    if stage == 'before':
        cancel.set()
    else:

        def hook(request):
            if request.url.path == stage:
                cancel.set()

        server.override = hook
    with pytest.raises(ImageProviderError) as caught:
        executor.execute(graph, cancel=cancel)
    assert caught.value.code == 'cancelled'
    assert not any(r.url.path == '/interrupt' for r in server.calls)
    if stage == 'before':
        assert not server.calls


class Chunks(httpx.SyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    def __iter__(self):
        yield from self.chunks

    def close(self):
        self.closed = True


def test_stream_limit_without_content_length(setup, graph):
    server, executor = setup
    stream = Chunks([b'x' * 65536] * (MAX_JSON_BYTES // 65536 + 1))
    server.override = lambda r: httpx.Response(
        200, headers={'content-type': 'application/json'}, stream=stream
    )
    with pytest.raises(ImageProviderError, match='byte limit'):
        executor.execute(graph)
    assert stream.closed


@pytest.mark.parametrize(
    'headers',
    [
        {'content-type': 'text/html'},
        {'content-type': 'application/json', 'content-length': str(MAX_JSON_BYTES + 1)},
        {'content-type': 'application/json', 'content-encoding': 'gzip'},
    ],
)
def test_response_headers(setup, graph, headers):
    server, executor = setup
    stream = Chunks([b'{}'])
    server.override = lambda r: httpx.Response(200, headers=headers, stream=stream)
    with pytest.raises(ImageProviderError):
        executor.execute(graph)
    assert stream.closed


def test_deadline_checked_after_response(setup, graph, monkeypatch):
    server, executor = setup
    now = [10.0]
    monkeypatch.setattr('animation_studio.providers.comfy_http.time.monotonic', lambda: now[0])

    def advance(request):
        now[0] += 61

    server.override = advance
    with pytest.raises(ImageProviderError) as caught:
        executor.execute(graph)
    assert caught.value.code == 'timeout' and len(server.calls) == 1


@pytest.mark.parametrize(
    'options',
    [
        {'timeout_seconds': 0},
        {'timeout_seconds': float('nan')},
        {'poll_interval': True},
        {'max_polls': 0},
        {'max_polls': 1001},
    ],
)
def test_invalid_configuration(options):
    with pytest.raises(ValueError):
        ComfyHTTPExecutor(transport=httpx.MockTransport(lambda r: httpx.Response(200)), **options)


def test_live_transport_rejected():
    with pytest.raises(TypeError):
        ComfyHTTPExecutor(transport=None)


def test_image_stream_limit(setup, graph, monkeypatch):
    server, executor = setup
    monkeypatch.setattr('animation_studio.providers.comfy_http.MAX_IMAGE_BYTES', 100)
    stream = Chunks([b'x' * 101])
    server.override = lambda r: (
        httpx.Response(200, headers={'content-type': 'image/png'}, stream=stream)
        if r.url.path == '/view'
        else None
    )
    with pytest.raises(ImageProviderError, match='byte limit'):
        executor.execute(graph)
    assert stream.closed and len(server.calls) == 3


@pytest.mark.parametrize('stop', ['cancel', 'timeout'])
def test_midstream_stop(setup, graph, monkeypatch, stop):
    server, executor = setup
    cancel = Event()
    now = [10.0]
    monkeypatch.setattr('animation_studio.providers.comfy_http.time.monotonic', lambda: now[0])

    class SlowStream(Chunks):
        def __iter__(self):
            yield b'x' * 65536
            if stop == 'cancel':
                cancel.set()
            else:
                now[0] += 61
            yield b'x' * 65536

    stream = SlowStream([])
    server.override = lambda r: (
        httpx.Response(200, headers={'content-type': 'application/json'}, stream=stream)
        if r.url.path.startswith('/history/')
        else None
    )
    with pytest.raises(ImageProviderError) as caught:
        executor.execute(graph, cancel=cancel)
    assert caught.value.code == ('cancelled' if stop == 'cancel' else 'timeout')
    assert stream.closed


def test_bad_download_not_saved(setup, graph, tmp_path):
    server, executor = setup
    server.png = b'not png'
    with pytest.raises(ImageProviderError) as caught:
        ComfyImageProvider(executor, tmp_path).generate(
            ImageRequest(
                prompt=graph['2']['inputs']['text'],
                model_name=MODEL_NAME,
                model_version=MODEL_VERSION,
                seed=42,
            )
        )
    assert caught.value.code == 'invalid_image'
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('stage', ['/prompt', f'/history/{PROMPT_ID}', '/view'])
@pytest.mark.parametrize('dispatched', [True, False])
def test_targeted_cancel_receipt(setup, graph, stage, dispatched):
    from animation_studio.providers.comfy_http import ComfyExecutionError

    server, executor = setup
    cancel = Event()

    def hook(request):
        if request.url.path == stage:
            cancel.set()
        if request.url.path == f'/api/jobs/{PROMPT_ID}/cancel':
            return httpx.Response(200, json={'cancelled': dispatched})

    server.override = hook
    with pytest.raises(ComfyExecutionError) as caught:
        executor.execute(graph, cancel=cancel)
    error = caught.value
    assert error.code == 'cancelled'
    assert error.receipt.prompt_id == PROMPT_ID
    assert error.cancellation.dispatched is dispatched
    assert error.cancellation.error_code is None
    assert [r.url.path for r in server.calls if r.method == 'POST'] == [
        '/prompt',
        f'/api/jobs/{PROMPT_ID}/cancel',
    ]
    assert server.calls[-1].extensions['timeout']['read'] <= 5


@pytest.mark.parametrize(
    'failure,expected',
    [
        ('timeout', 'timeout'),
        ('disconnect', 'execution_failed'),
        ('http', 'execution_failed'),
        ('malformed', 'execution_failed'),
        ('wrong_type', 'execution_failed'),
        ('missing', 'execution_failed'),
    ],
)
def test_cleanup_failure_preserves_primary(setup, graph, failure, expected):
    from animation_studio.providers.comfy_http import ComfyExecutionError

    server, executor = setup
    cancel = Event()

    def hook(request):
        if request.url.path == '/prompt':
            cancel.set()
        if request.url.path.endswith('/cancel'):
            if failure == 'timeout':
                raise httpx.ReadTimeout('secret', request=request)
            if failure == 'disconnect':
                raise httpx.ConnectError('secret', request=request)
            if failure == 'http':
                return httpx.Response(503)
            if failure == 'malformed':
                return httpx.Response(
                    200, content=b'{', headers={'content-type': 'application/json'}
                )
            return httpx.Response(200, json={'cancelled': 1} if failure == 'wrong_type' else {})

    server.override = hook
    with pytest.raises(ComfyExecutionError) as caught:
        executor.execute(graph, cancel=cancel)
    error = caught.value
    assert error.code == error.__cause__.code == 'cancelled'
    assert error.receipt.prompt_id == PROMPT_ID
    assert error.cancellation.dispatched is None
    assert error.cancellation.error_code == expected
    assert 'secret' not in str(error)
    assert len(server.calls) == 2


def test_expired_primary_deadline_gets_fresh_cleanup_budget(setup, graph, monkeypatch):
    from animation_studio.providers.comfy_http import ComfyExecutionError

    server, executor = setup
    now = [10.0]
    monkeypatch.setattr('animation_studio.providers.comfy_http.time.monotonic', lambda: now[0])

    def hook(request):
        if request.url.path.startswith('/history/'):
            now[0] += 61

    server.override = hook
    with pytest.raises(ComfyExecutionError) as caught:
        executor.execute(graph)
    assert caught.value.code == 'timeout'
    assert caught.value.cancellation.dispatched is True
    assert server.calls[-1].url.path == f'/api/jobs/{PROMPT_ID}/cancel'
    assert server.calls[-1].extensions['timeout']['read'] == 5


@pytest.mark.parametrize('case', ['before', 'lost_ack', 'invalid_ack'])
def test_unknown_receipt_never_cancels_arbitrary_job(setup, graph, case):
    from animation_studio.providers.comfy_http import ComfyExecutionError

    server, executor = setup
    cancel = Event()
    if case == 'before':
        cancel.set()
    elif case == 'invalid_ack':
        server.receipt = {'prompt_id': '../other', 'node_errors': {}}
    else:

        def lost(request):
            raise httpx.ReadTimeout('lost', request=request)

        server.override = lost
    with pytest.raises(ComfyExecutionError) as caught:
        executor.execute(graph, cancel=cancel)
    assert caught.value.receipt is None and caught.value.cancellation is None
    assert len(server.calls) == (0 if case == 'before' else 1)


def test_no_stale_receipt_on_reused_executor(setup, graph):
    from animation_studio.providers.comfy_http import ComfyExecutionError

    server, executor = setup
    cancel = Event()

    def hook(request):
        if request.url.path == '/prompt':
            cancel.set()

    server.override = hook
    with pytest.raises(ComfyExecutionError) as first:
        executor.execute(graph, cancel=cancel)
    assert first.value.receipt.prompt_id == PROMPT_ID
    server.override = None
    server.receipt = {}
    start = len(server.calls)
    with pytest.raises(ComfyExecutionError) as second:
        executor.execute(graph)
    assert second.value.receipt is None and second.value.cancellation is None
    assert len(server.calls) == start + 1


def test_non_cancel_failure_retains_receipt_without_cleanup(setup, graph):
    from dataclasses import FrozenInstanceError

    from animation_studio.providers.comfy_http import ComfyExecutionError

    server, executor = setup
    server.history[PROMPT_ID]['status']['status_str'] = 'error'
    with pytest.raises(ComfyExecutionError) as caught:
        executor.execute(graph)
    assert caught.value.code == 'execution_failed'
    assert caught.value.receipt.prompt_id == PROMPT_ID
    assert caught.value.cancellation is None
    with pytest.raises(FrozenInstanceError):
        caught.value.receipt.prompt_id = 'different'
    assert len(server.calls) == 2
