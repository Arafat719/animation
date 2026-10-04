import json
import os
import stat
import subprocess
import sys

import pytest

from animation_studio.providers import comfy_storage
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_storage import ComfyJournalStore

UUID = '12345678-1234-5678-9abc-123456789abc'


@pytest.fixture
def context():
    return ComfyExecutionContext(
        mode='mock',
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
    return ComfyJournalStore(tmp_path, context)


def test_deterministic_roundtrip_and_permissions(store, context):
    assert store.path.name == f'{UUID}.json'
    with store.locked():
        assert store.create_intent().state == 'intent'
        assert store.accept(UUID).prompt_id == UUID
    saved = store.path.read_bytes()
    with ComfyJournalStore(store.path.parent, context).locked() as restarted:
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
    other = ComfyJournalStore(store.path.parent, context)
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
    other = ComfyJournalStore(
        store.path.parent, context.model_copy(update={'graph_sha256': 'd' * 64})
    )
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
    tmp_path.chmod(0o755)
    with pytest.raises(ValueError), ComfyJournalStore(tmp_path, context).locked():
        pass


def test_process_exit_releases_lock_and_preserves_intent(store, context):
    script = """
import json, os, sys
from pathlib import Path
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_storage import ComfyJournalStore
store = ComfyJournalStore(Path(sys.argv[1]), ComfyExecutionContext(**json.loads(sys.argv[2])))
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
