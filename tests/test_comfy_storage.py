import json
import os
import stat
import subprocess
import sys

import pytest

from animation_studio.providers import comfy_storage
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_storage import ComfyJournalStore, LiveComfyJournalStore

UUID = '12345678-1234-5678-9abc-123456789abc'


@pytest.fixture(params=['mock', 'live'])
def context(request):
    return ComfyExecutionContext(
        mode=request.param,
        job_id=UUID,
        graph_sha256='a' * 64,
        origin='https://comfy.invalid:443/',
        deployment_id=UUID,
        runtime_manifest_sha256='b' * 64,
        model_manifest_sha256='c' * 64,
    )


@pytest.fixture
def store(tmp_path, context):
    tmp_path.chmod(0o700)
    return (ComfyJournalStore if context.mode == 'mock' else LiveComfyJournalStore)(
        tmp_path, context
    )


def test_deterministic_roundtrip_and_permissions(store, context):
    assert store.path.name == f'{UUID}.json'
    with store.locked():
        assert store.create_intent().state == 'intent'
        assert store.accept(UUID).prompt_id == UUID
    saved = store.path.read_bytes()
    with type(store)(store.path.parent, context).locked() as restarted:
        assert restarted.read().prompt_id == UUID
        with pytest.raises(ValueError):
            restarted.create_intent()
        with pytest.raises(ValueError):
            restarted.accept(UUID)
    assert store.path.read_bytes() == saved
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store.path.with_suffix('.json.lock').stat().st_mode) == 0o600


@pytest.mark.parametrize('operation', ['read', 'create_intent', 'accept'])
def test_requires_lock(store, operation):
    with pytest.raises(RuntimeError):
        getattr(store, operation)(*([UUID] if operation == 'accept' else []))


def test_competing_owner_and_release(store, context):
    other = type(store)(store.path.parent, context)
    with store.locked():
        with pytest.raises(RuntimeError), store.locked():
            pass
        with pytest.raises(BlockingIOError), other.locked():
            pass
    with other.locked():
        other.create_intent()


@pytest.mark.parametrize(
    'body',
    [
        b'bad',
        b'x' * 4097,
        json.dumps(
            {
                'schema_version': 1,
                'mode': 'mock',
                'state': 'intent',
                'graph_sha256': 'a' * 64,
            }
        ).encode(),
    ],
)
def test_existing_corrupt_or_legacy_never_overwritten(store, body):
    store.path.write_bytes(body)
    with store.locked():
        for operation, args in [('read', []), ('create_intent', []), ('accept', [UUID])]:
            with pytest.raises(ValueError):
                getattr(store, operation)(*args)
    assert store.path.read_bytes() == body


@pytest.mark.parametrize('kind', ['journal', 'lock'])
def test_symlink_rejected(store, tmp_path, kind):
    target = tmp_path / 'untouched'
    target.write_bytes(b'original')
    path = store.path if kind == 'journal' else store.path.with_suffix('.json.lock')
    path.symlink_to(target)
    if kind == 'lock':
        with pytest.raises(OSError), store.locked():
            pass
    else:
        with store.locked():
            with pytest.raises(OSError):
                store.read()
            with pytest.raises(ValueError):
                store.create_intent()
    assert target.read_bytes() == b'original'


def test_invalid_receipt_and_context_preserve_intent(store, context):
    with store.locked():
        store.create_intent()
        saved = store.path.read_bytes()
        with pytest.raises(ValueError):
            store.accept('not-a-uuid')
    other = type(store)(store.path.parent, context.model_copy(update={'graph_sha256': 'd' * 64}))
    with other.locked(), pytest.raises(ValueError):
        other.accept(UUID)
    assert store.path.read_bytes() == saved


@pytest.mark.parametrize('stage', ['file_fsync', 'replace', 'directory_fsync'])
def test_atomic_failure_preserves_valid_state(store, monkeypatch, stage):
    with store.locked():
        store.create_intent()
        original = os.fsync

        def fail_sync(fd):
            is_dir = stat.S_ISDIR(os.fstat(fd).st_mode)
            if (stage == 'file_fsync' and not is_dir) or (stage == 'directory_fsync' and is_dir):
                raise OSError('injected fsync error')
            original(fd)

        def fail_replace(*args):
            raise OSError('injected replace error')

        monkeypatch.setattr(os, 'fsync', fail_sync)
        if stage == 'replace':
            monkeypatch.setattr(os, 'replace', fail_replace)
        with pytest.raises(OSError):
            store.accept(UUID)
        assert store.read().state == ('accepted' if stage == 'directory_fsync' else 'intent')
        with pytest.raises(ValueError):
            store.create_intent()
    assert not list(store.path.parent.glob('.comfy-v2-*'))


def test_fsync_order_and_size_guard(store, monkeypatch):
    events = []
    sync, replace = os.fsync, os.replace

    def traced_sync(fd):
        events.append('directory' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file')
        sync(fd)

    def traced_replace(*args):
        events.append('replace')
        replace(*args)

    monkeypatch.setattr(os, 'fsync', traced_sync)
    monkeypatch.setattr(os, 'replace', traced_replace)
    with store.locked():
        store.create_intent()
        assert events == ['file', 'replace', 'directory']
        saved = store.path.read_bytes()
        monkeypatch.setattr(comfy_storage, 'MAX_RECORD_BYTES', 1)
        with pytest.raises(ValueError):
            store._write(store_record(context=store._context))
        assert store.path.read_bytes() == saved
        assert events == ['file', 'replace', 'directory']


def store_record(context):
    from animation_studio.providers.comfy_identity import ComfyJobRecordV2

    return ComfyJobRecordV2(**context.model_dump(), schema_version=2, state='intent')


def test_live_and_unsafe_root_rejected(tmp_path, context):
    with pytest.raises(ValueError):
        ComfyJournalStore(tmp_path, context.model_copy(update={'mode': 'live'}))
    with pytest.raises(ValueError):
        LiveComfyJournalStore(tmp_path, context.model_copy(update={'mode': 'mock'}))
    tmp_path.chmod(0o755)
    factory = ComfyJournalStore if context.mode == 'mock' else LiveComfyJournalStore
    with pytest.raises(ValueError), factory(tmp_path, context).locked():
        pass


def test_process_exit_releases_lock_and_preserves_intent(store, context):
    script = """
import json, os, sys
from pathlib import Path
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_storage import ComfyJournalStore, LiveComfyJournalStore
context = ComfyExecutionContext(**json.loads(sys.argv[2]))
factory = ComfyJournalStore if context.mode == 'mock' else LiveComfyJournalStore
store = factory(Path(sys.argv[1]), context)
with store.locked():
    store.create_intent()
    os._exit(23)
"""
    run = subprocess.run(
        [sys.executable, '-c', script, str(store.path.parent), context.model_dump_json()],
        check=False,
        timeout=20,
        capture_output=True,
    )
    assert run.returncode == 23, run.stderr
    with store.locked():
        assert store.read().state == 'intent'
        with pytest.raises(ValueError):
            store.create_intent()


def test_other_thread_cannot_use_held_lock(store):
    from concurrent.futures import ThreadPoolExecutor

    with store.locked(), ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(store.create_intent)
        with pytest.raises(RuntimeError):
            future.result(timeout=5)
        assert not store.path.exists()


def test_fifo_read_rejected_without_blocking(store):
    os.mkfifo(store.path)
    with store.locked(), pytest.raises(ValueError):
        store.read()


def test_failure_before_initial_replace_allows_retry(store, monkeypatch):
    with store.locked():
        with monkeypatch.context() as patch:

            def fail(fd):
                raise OSError('injected')

            patch.setattr(os, 'fsync', fail)
            with pytest.raises(OSError):
                store.create_intent()
        assert not store.path.exists()
        store.create_intent()
        assert store.read().state == 'intent'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        pytest.fail('Journal storage must not use network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


@pytest.mark.parametrize('state', ['intent', 'accepted'])
def test_cross_mode_records_and_lock_never_bypass_existing_job(store, context, state):
    opposite_mode = 'live' if context.mode == 'mock' else 'mock'
    factory = LiveComfyJournalStore if opposite_mode == 'live' else ComfyJournalStore
    other = factory(store.path.parent, context.model_copy(update={'mode': opposite_mode}))
    assert other.path == store.path
    with store.locked():
        store.create_intent()
        if state == 'accepted':
            store.accept(UUID)
        with pytest.raises(BlockingIOError), other.locked():
            pass
    saved = store.path.read_bytes()
    with other.locked():
        for operation, args in [('read', []), ('create_intent', []), ('accept', [UUID])]:
            with pytest.raises(ValueError):
                getattr(other, operation)(*args)
    assert store.path.read_bytes() == saved


@pytest.mark.parametrize('state', ['intent', 'accepted'])
def test_existing_v2_backward_read_does_not_rewrite(store, context, state):
    # Old v2 bytes need no migration: mode was already part of this schema.
    old = dict(context.model_dump(), schema_version=2, state=state)
    if state == 'accepted':
        old['prompt_id'] = UUID
    saved = json.dumps(old, indent=2).encode()
    store.path.write_bytes(saved)
    with store.locked():
        record = store.read()
        assert record.schema_version == 2 and record.mode == context.mode
        assert record.state == state
        with pytest.raises(ValueError):
            store.create_intent()
    assert store.path.read_bytes() == saved


@pytest.mark.parametrize('state', ['intent', 'accepted'])
def test_v1_remains_readable_as_mock_and_cannot_migrate_into_v2(store, state):
    from animation_studio.providers.comfy_identity import parse_job_record
    from animation_studio.providers.comfy_journal import ComfyJobRecord

    old = {'schema_version': 1, 'mode': 'mock', 'graph_sha256': 'a' * 64, 'state': state}
    if state == 'accepted':
        old['prompt_id'] = UUID
    saved = json.dumps(old).encode()
    store.path.write_bytes(saved)
    assert type(parse_job_record(saved, expected_mode='mock')) is ComfyJobRecord
    with pytest.raises(ValueError):
        parse_job_record(saved, expected_mode='live')
    with store.locked():
        for operation, args in [('read', []), ('create_intent', []), ('accept', [UUID])]:
            with pytest.raises(ValueError):
                getattr(store, operation)(*args)
    assert store.path.read_bytes() == saved


@pytest.mark.parametrize(
    'field,value',
    [
        ('job_id', '87654321-1234-5678-9abc-123456789abc'),
        ('graph_sha256', 'd' * 64),
        ('origin', 'https://other.invalid:443/'),
        ('deployment_id', '87654321-1234-5678-9abc-123456789abc'),
        ('runtime_manifest_sha256', 'd' * 64),
        ('model_manifest_sha256', 'd' * 64),
    ],
)
def test_each_persisted_identity_mismatch_blocks_receipt_write(store, field, value):
    with store.locked():
        store.create_intent()
    # Simulate a valid record belonging to another execution at this path.
    body = json.loads(store.path.read_bytes())
    body[field] = value
    saved = json.dumps(body).encode()
    store.path.write_bytes(saved)
    with store.locked():
        with pytest.raises(ValueError):
            store.read()
        with pytest.raises(ValueError):
            store.accept(UUID)
    assert store.path.read_bytes() == saved


def test_live_storage_does_not_enable_existing_execution_or_supervision(tmp_path, context):
    import httpx

    from animation_studio.providers.comfy_http import ComfyHTTPExecutor
    from animation_studio.providers.comfy_supervision_storage import ComfySupervisionStore
    from animation_studio.providers.comfy_v2_executor import DurableComfyExecutorV2

    live_context = context.model_copy(update={'mode': 'live'})
    live = LiveComfyJournalStore(tmp_path, live_context)
    with pytest.raises(TypeError):
        ComfySupervisionStore(live)
    calls = []
    executor = ComfyHTTPExecutor(transport=httpx.MockTransport(lambda r: calls.append(r)))
    try:
        with pytest.raises(ValueError):
            DurableComfyExecutorV2(executor, tmp_path, live_context)
    finally:
        executor.close()
    assert not calls and not list(tmp_path.iterdir())


def test_store_revalidates_forged_context_without_writing(tmp_path, context):
    factory = ComfyJournalStore if context.mode == 'mock' else LiveComfyJournalStore
    with pytest.raises(ValueError):
        factory(tmp_path, context.model_copy(update={'origin': 'http://unsafe.invalid'}))
    assert not list(tmp_path.iterdir())
