import json
import os
import subprocess
import sys
from pathlib import Path
from threading import Event

import httpx
import pytest
from test_comfy_http import PROMPT_ID, Server

from animation_studio.providers.comfy_http import ComfyExecutionError, ComfyHTTPExecutor
from animation_studio.providers.comfy_journal import ComfyJobRecord, DurableComfyExecutor
from animation_studio.providers.comfy_workflow import (
    MODEL_NAME,
    MODEL_VERSION,
    build_image_workflow,
)
from animation_studio.providers.image import ImageProviderError, ImageRequest


@pytest.fixture
def graph():
    return build_image_workflow(
        ImageRequest(
            prompt='নদীর পাশে বাড়ি', model_name=MODEL_NAME, model_version=MODEL_VERSION, seed=42
        )
    )


@pytest.fixture
def setup(tmp_path, graph):
    server = Server(graph)
    client = ComfyHTTPExecutor(
        transport=httpx.MockTransport(server), max_polls=2, poll_interval=0.001
    )
    journal = DurableComfyExecutor(client, tmp_path / 'job.json')
    yield server, client, journal
    client.close()


def test_persist_before_submit_and_before_poll(setup, graph):
    server, client, journal = setup
    seen = []

    def inspect(request):
        if request.url.path.startswith('/object_info/'):
            assert not journal.path.exists()
            return
        data = json.loads(journal.path.read_text())
        seen.append(data['state'])
        if request.url.path == '/prompt':
            assert data['state'] == 'intent' and data['prompt_id'] is None
        else:
            assert data['state'] == 'accepted' and data['prompt_id'] == PROMPT_ID

    server.override = inspect
    assert journal.execute(graph) == server.png
    assert seen == ['intent', 'accepted', 'accepted']
    saved = journal.path.read_bytes()
    assert graph['2']['inputs']['text'].encode() not in saved
    assert os.stat(journal.path).st_mode & 0o777 == 0o600
    with pytest.raises(ImageProviderError, match='Journal exists'):
        DurableComfyExecutor(client, journal.path).execute(graph)
    assert journal.path.read_bytes() == saved
    server.calls.clear()
    assert DurableComfyExecutor(client, journal.path).recover(graph) == server.png
    assert all(r.method == 'GET' for r in server.calls)
    assert journal.path.read_bytes() == saved


def test_lost_ack_stays_unknown_across_instances(setup, graph):
    server, client, journal = setup

    def lost(request):
        if request.url.path == '/prompt':
            raise httpx.ReadTimeout('lost acknowledgement', request=request)

    server.override = lost
    with pytest.raises(ComfyExecutionError):
        journal.execute(graph)
    assert json.loads(journal.path.read_text())['state'] == 'intent'
    restarted = DurableComfyExecutor(client, journal.path)
    for operation in (restarted.execute, restarted.recover):
        with pytest.raises(ImageProviderError):
            operation(graph)
    assert len(server.calls) == 7


def test_crash_before_http_still_blocks_submit(setup, graph, monkeypatch):
    server, client, journal = setup

    def crash(*args, **kwargs):
        raise SystemExit('crash after durable intent')

    monkeypatch.setattr(client, 'execute', crash)
    with pytest.raises(SystemExit):
        journal.execute(graph)
    with pytest.raises(ImageProviderError, match='Journal exists'):
        DurableComfyExecutor(client, journal.path).execute(graph)
    assert len(server.calls) == 6 and all(r.method == 'GET' for r in server.calls)


@pytest.mark.parametrize('stage', ['intent', 'accepted'])
def test_write_failure_blocks_progress(setup, graph, monkeypatch, stage):
    server, client, journal = setup
    write = journal._write

    def fail(record):
        if record.state == stage:
            raise OSError('disk failure')
        write(record)

    monkeypatch.setattr(journal, '_write', fail)
    with pytest.raises(ImageProviderError) as caught:
        journal.execute(graph)
    assert caught.value.code == 'io_error'
    assert len(server.calls) == (6 if stage == 'intent' else 7)
    if stage == 'accepted':
        assert caught.value.receipt.prompt_id == PROMPT_ID
        assert json.loads(journal.path.read_text())['state'] == 'intent'
        with pytest.raises(ImageProviderError):
            DurableComfyExecutor(client, journal.path).recover(graph)
        assert len(server.calls) == 7


def test_fsync_failure_before_submit(setup, graph, monkeypatch):
    server, _, journal = setup

    def fail(fd):
        raise OSError('fsync failed')

    monkeypatch.setattr('animation_studio.providers.comfy_journal.os.fsync', fail)
    with pytest.raises(ImageProviderError):
        journal.execute(graph)
    assert len(server.calls) == 6 and all(r.method == 'GET' for r in server.calls)
    assert not list(journal.path.parent.glob('.comfy-job-*'))


def test_second_owner_cannot_submit_or_recover_while_active(setup, graph):
    server, client, journal = setup
    competing = DurableComfyExecutor(client, journal.path)

    def compete(request):
        if request.url.path == '/prompt':
            for operation in (competing.execute, competing.recover):
                with pytest.raises(ImageProviderError) as caught:
                    operation(graph)
                assert caught.value.code == 'io_error'

    server.override = compete
    journal.execute(graph)
    assert [r.method for r in server.calls].count('POST') == 1


@pytest.mark.parametrize(
    'body',
    [b'', b'{', b'{}', b'{"schema_version":1,"schema_version":1}', b'x' * 4097],
    ids=['empty', 'truncated', 'missing', 'duplicate', 'large'],
)
def test_corrupt_record_blocks_all_dispatch(setup, graph, body):
    server, _, journal = setup
    journal.path.write_bytes(body)
    for operation in (journal.execute, journal.recover):
        with pytest.raises(ImageProviderError):
            operation(graph)
    assert journal.path.read_bytes() == body and not server.calls


@pytest.mark.parametrize(
    'field,value',
    [
        ('schema_version', 2),
        ('schema_version', True),
        ('mode', 'live'),
        ('prompt_id', '../other'),
        ('state', 'unknown'),
        ('extra', 1),
    ],
)
def test_invalid_schema_record(setup, graph, field, value):
    server, _, journal = setup
    journal.execute(graph)
    data = json.loads(journal.path.read_text())
    data[field] = value
    journal.path.write_text(json.dumps(data))
    server.calls.clear()
    with pytest.raises(ImageProviderError):
        journal.recover(graph)
    assert not server.calls


def test_request_mismatch_and_missing_journal(setup, graph):
    server, _, journal = setup
    with pytest.raises(ImageProviderError):
        journal.recover(graph)
    assert not server.calls
    journal.execute(graph)
    server.calls.clear()
    graph['5']['inputs']['seed'] += 1
    with pytest.raises(ImageProviderError, match='mismatch'):
        journal.recover(graph)
    assert not server.calls


@pytest.mark.parametrize('kind', ['journal', 'lock'])
def test_symlinks_rejected(setup, graph, tmp_path, kind):
    server, _, journal = setup
    target = tmp_path / 'target'
    target.write_text('preserve')
    path = journal.path if kind == 'journal' else Path(str(journal.path) + '.lock')
    path.symlink_to(target)
    for operation in (journal.execute, journal.recover):
        with pytest.raises(ImageProviderError):
            operation(graph)
    assert target.read_text() == 'preserve' and not server.calls


def test_recovery_timeout_and_cancel_are_get_only(setup, graph):
    server, _, journal = setup
    journal.execute(graph)
    original = journal.path.read_bytes()
    server.calls.clear()
    server.pending = 10
    with pytest.raises(ComfyExecutionError) as caught:
        journal.recover(graph)
    assert caught.value.code == 'timeout' and caught.value.cancellation is None
    assert all(r.method == 'GET' for r in server.calls)
    cancel = Event()
    cancel.set()
    count = len(server.calls)
    with pytest.raises(ComfyExecutionError) as caught:
        journal.recover(graph, cancel=cancel)
    assert caught.value.code == 'cancelled' and len(server.calls) == count
    assert journal.path.read_bytes() == original


def test_cancel_before_intent(setup, graph):
    server, _, journal = setup
    cancel = Event()
    cancel.set()
    with pytest.raises(ImageProviderError):
        journal.execute(graph, cancel=cancel)
    assert not journal.path.exists() and not server.calls


def test_initial_version_intent_backward_read():
    # Version-1 intent records may omit the optional receipt; never upgrade to accepted.
    record = ComfyJobRecord.model_validate_json(
        json.dumps(
            {'schema_version': 1, 'mode': 'mock', 'graph_sha256': 'a' * 64, 'state': 'intent'}
        )
    )
    assert record.prompt_id is None and record.state == 'intent'


def test_real_process_exit_and_restart(tmp_path, graph):
    script = """
import json, os, sys
from pathlib import Path
sys.path.insert(0, 'tests')
import httpx
from test_comfy_http import Server
from animation_studio.providers.comfy_http import ComfyHTTPExecutor
from animation_studio.providers.comfy_journal import DurableComfyExecutor
root = Path(sys.argv[1])
graph = json.loads((root / 'graph.json').read_text())
server = Server(graph)
def handler(request):
    with (root / 'calls').open('a') as stream:
        stream.write(request.method + ' ' + request.url.path + '\\n')
    if sys.argv[2] == 'crash' and request.url.path.startswith('/history/'):
        os._exit(7)
    return server(request)
client = ComfyHTTPExecutor(transport=httpx.MockTransport(handler))
journal = DurableComfyExecutor(client, root / 'job.json')
result = journal.execute(graph) if sys.argv[2] == 'crash' else journal.recover(graph)
assert result == server.png
client.close()
"""
    (tmp_path / 'graph.json').write_text(json.dumps(graph))
    root = Path(__file__).resolve().parents[1]
    first = subprocess.run(
        [sys.executable, '-c', script, str(tmp_path), 'crash'],
        cwd=root,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert first.returncode == 7, first.stderr.decode()
    assert json.loads((tmp_path / 'job.json').read_text())['state'] == 'accepted'
    second = subprocess.run(
        [sys.executable, '-c', script, str(tmp_path), 'recover'],
        cwd=root,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert second.returncode == 0, second.stderr.decode()
    calls = (tmp_path / 'calls').read_text().splitlines()
    assert sum(line == 'POST /prompt' for line in calls) == 1
    assert calls[-1].startswith('GET /view')


@pytest.mark.parametrize('failure', ['missing', 'http', 'timeout', 'cancel'])
def test_preflight_failure_leaves_no_intent_and_allows_explicit_retry(setup, graph, failure):
    server, _, journal = setup
    cancel = Event()

    def fail(request):
        assert request.url.path.startswith('/object_info/')
        assert not journal.path.exists()
        if failure == 'timeout':
            raise httpx.ReadTimeout('timeout', request=request)
        if failure == 'cancel':
            cancel.set()
        return httpx.Response(503) if failure == 'http' else httpx.Response(200, json={})

    server.override = fail
    with pytest.raises(ImageProviderError):
        journal.execute(graph, cancel=cancel)
    assert not journal.path.exists()
    assert len(server.calls) == 1 and server.calls[0].method == 'GET'
    server.override = None
    cancel.clear()
    assert journal.execute(graph, cancel=cancel) == server.png
    assert sum(r.url.path == '/prompt' for r in server.calls) == 1


def test_lock_held_through_preflight(setup, graph):
    server, client, journal = setup
    second = DurableComfyExecutor(client, journal.path)

    def compete(request):
        if request.url.path.startswith('/object_info/'):
            assert not journal.path.exists()
            with pytest.raises(ImageProviderError) as caught:
                second.execute(graph)
            assert caught.value.code == 'io_error'

    server.override = compete
    journal.execute(graph)
    assert sum(r.url.path.startswith('/object_info/') for r in server.calls) == 6
    assert sum(r.url.path == '/prompt' for r in server.calls) == 1


def test_recovery_ignores_unavailable_inventory(setup, graph):
    server, _, journal = setup
    journal.execute(graph)
    previous = journal.path.read_bytes()
    server.calls.clear()

    def missing(request):
        if request.url.path.startswith('/object_info/'):
            raise AssertionError('Recovery must not require node/model availability')

    server.override = missing
    assert journal.recover(graph) == server.png
    assert [r.url.path for r in server.calls] == [f'/history/{PROMPT_ID}', '/view']
    assert journal.path.read_bytes() == previous


def test_cancel_after_preflight_before_intent(setup, graph, monkeypatch):
    server, client, journal = setup
    cancel = Event()
    preflight = client.preflight

    def finish(*args, **kwargs):
        preflight(*args, **kwargs)
        cancel.set()

    monkeypatch.setattr(client, 'preflight', finish)
    with pytest.raises(ImageProviderError) as caught:
        journal.execute(graph, cancel=cancel)
    assert caught.value.code == 'cancelled'
    assert not journal.path.exists()
    assert len(server.calls) == 6 and all(r.method == 'GET' for r in server.calls)
