import json
from threading import Event

import httpx
import pytest
from test_comfy_http import PROMPT_ID, Server
from test_comfy_http import graph as graph_fixture

from animation_studio.providers.comfy_http import ComfyExecutionError, ComfyHTTPExecutor
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_journal import _fingerprint
from animation_studio.providers.comfy_v2_executor import DurableComfyExecutorV2
from animation_studio.providers.image import ImageProviderError

graph = graph_fixture


@pytest.fixture
def setup(tmp_path, graph):
    tmp_path.chmod(0o700)
    server = Server(graph)
    client = ComfyHTTPExecutor(transport=httpx.MockTransport(server), max_polls=1)
    context = ComfyExecutionContext(
        mode='mock',
        job_id=PROMPT_ID,
        graph_sha256=_fingerprint(graph),
        origin='https://comfy.invalid:443/',
        deployment_id=PROMPT_ID,
        runtime_manifest_sha256='a' * 64,
        model_manifest_sha256='b' * 64,
    )
    executor = DurableComfyExecutorV2(client, tmp_path, context)
    yield server, executor, context
    client.close()


def test_order_restart_get_only(setup, graph, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('No live sockets')

    monkeypatch.setattr(socket, 'socket', forbidden)
    server, executor, context = setup

    def inspect(request):
        if request.url.path.startswith('/object_info/'):
            assert not executor.store.path.exists()
        else:
            state = json.loads(executor.store.path.read_bytes())['state']
            assert state == ('intent' if request.url.path == '/prompt' else 'accepted')

    server.override = inspect
    assert executor.execute(graph) == server.png
    saved = executor.store.path.read_bytes()
    restarted = DurableComfyExecutorV2(executor.executor, executor.store.path.parent, context)
    with pytest.raises(ImageProviderError):
        restarted.execute(graph)
    server.calls.clear()
    assert restarted.recover(graph) == server.png
    assert [r.url.path for r in server.calls] == [f'/history/{PROMPT_ID}', '/view']
    assert all(r.method == 'GET' for r in server.calls)
    assert executor.store.path.read_bytes() == saved


@pytest.mark.parametrize('failure', ['preflight', 'cancel_after_preflight', 'intent_write'])
def test_before_submit_no_intent_explicit_retry(setup, graph, monkeypatch, failure):
    server, executor, _ = setup
    cancel = Event()
    with monkeypatch.context() as patch:
        if failure == 'preflight':
            server.override = lambda request: httpx.Response(500)
        elif failure == 'cancel_after_preflight':
            original = executor.executor.preflight

            def preflight(*args, **kwargs):
                original(*args, **kwargs)
                cancel.set()

            patch.setattr(executor.executor, 'preflight', preflight)
        else:

            def fail():
                raise OSError('write failed')

            patch.setattr(executor.store, 'create_intent', fail)
        with pytest.raises(ImageProviderError):
            executor.execute(graph, cancel=cancel)
    assert not executor.store.path.exists()
    assert not any(r.method == 'POST' for r in server.calls)
    server.override = None
    cancel.clear()
    assert executor.execute(graph, cancel=cancel) == server.png


@pytest.mark.parametrize('failure', ['lost_receipt', 'malformed_receipt', 'persist_receipt'])
def test_ambiguous_no_resubmit(setup, graph, monkeypatch, failure):
    server, executor, _ = setup
    if failure == 'persist_receipt':

        def fail(receipt):
            raise ValueError('bad storage')

        monkeypatch.setattr(executor.store, 'accept', fail)
    elif failure == 'malformed_receipt':
        server.receipt = {'prompt_id': 'bad'}
    else:

        def lost(request):
            if request.url.path == '/prompt':
                raise httpx.ReadError('lost')

        server.override = lost
    with pytest.raises(ComfyExecutionError) as error:
        executor.execute(graph)
    if failure == 'persist_receipt':
        assert error.value.receipt.prompt_id == PROMPT_ID
        assert error.value.code == 'io_error'
    assert json.loads(executor.store.path.read_bytes())['state'] == 'intent'
    server.calls.clear()
    for method in (executor.execute, executor.recover):
        with pytest.raises(ImageProviderError):
            method(graph)
    assert server.calls == []


@pytest.mark.parametrize(
    'field,value',
    [
        ('deployment_id', '87654321-1234-5678-9abc-123456789abc'),
        ('runtime_manifest_sha256', 'c' * 64),
        ('model_manifest_sha256', 'c' * 64),
        ('origin', 'https://other.invalid:443/'),
        ('mode', 'live'),
        ('job_id', '87654321-1234-5678-9abc-123456789abc'),
        ('graph_sha256', 'c' * 64),
        ('schema_version', 1),
    ],
)
def test_recovery_identity_mismatch_no_io(setup, graph, field, value):
    server, executor, _ = setup
    executor.execute(graph)
    data = json.loads(executor.store.path.read_bytes())
    data[field] = value
    executor.store.path.write_text(json.dumps(data))
    saved = executor.store.path.read_bytes()
    server.calls.clear()
    with pytest.raises(ImageProviderError):
        executor.recover(graph)
    assert not server.calls
    assert executor.store.path.read_bytes() == saved


def test_lock_held_during_preflight(setup, graph):
    server, executor, context = setup
    other = DurableComfyExecutorV2(executor.executor, executor.store.path.parent, context)

    def inspect(request):
        if request.url.path.startswith('/object_info/'):
            with pytest.raises(ImageProviderError):
                other.execute(graph)

    server.override = inspect
    assert executor.execute(graph) == server.png
    assert sum(r.url.path == '/prompt' for r in server.calls) == 1


@pytest.mark.parametrize('operation', ['execute', 'recover'])
def test_precancel_and_wrong_graph_no_io(setup, graph, operation):
    server, executor, _ = setup
    event = Event()
    event.set()
    with pytest.raises(ImageProviderError):
        getattr(executor, operation)(graph, cancel=event)
    graph['2']['inputs']['text'] = 'different'
    with pytest.raises(ImageProviderError):
        getattr(executor, operation)(graph)
    assert not server.calls and not executor.store.path.exists()


def test_recovery_timeout_get_only(setup, graph):
    server, executor, _ = setup
    executor.execute(graph)
    server.calls.clear()
    server.pending = 10
    with pytest.raises(ComfyExecutionError):
        executor.recover(graph)
    assert all(r.method == 'GET' and r.url.path.startswith('/history/') for r in server.calls)


@pytest.mark.parametrize('crash_path', ['/prompt', '/view'])
def test_real_process_crash_recovery(setup, graph, crash_path):
    import subprocess
    import sys

    server, executor, context = setup
    trace = executor.store.path.parent / 'trace.txt'
    script = r"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, 'tests')
import httpx
from test_comfy_http import Server
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_http import ComfyHTTPExecutor
from animation_studio.providers.comfy_v2_executor import DurableComfyExecutorV2
root, context, graph, crash_path = Path(sys.argv[1]), json.loads(sys.argv[2]), json.loads(sys.argv[3]), sys.argv[4]
server = Server(graph)
def transport(request):
    with (root / 'trace.txt').open('a') as stream:
        stream.write(request.method + ' ' + request.url.path + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    if request.url.path == crash_path:
        os._exit(23)
    return server(request)
client = ComfyHTTPExecutor(transport=httpx.MockTransport(transport), max_polls=1)
DurableComfyExecutorV2(client, root, ComfyExecutionContext(**context)).execute(graph)
"""
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            script,
            str(executor.store.path.parent),
            context.model_dump_json(),
            json.dumps(graph),
            crash_path,
        ],
        check=False,
        timeout=20,
        capture_output=True,
    )
    assert result.returncode == 23, result.stderr
    assert trace.read_text().count('POST /prompt') == 1
    with pytest.raises(ImageProviderError):
        executor.execute(graph)
    if crash_path == '/view':
        assert executor.recover(graph) == server.png
        assert all(r.method == 'GET' for r in server.calls)
    else:
        with pytest.raises(ImageProviderError):
            executor.recover(graph)
        assert server.calls == []
