import json
import os

import pytest
from pydantic import ValidationError

from animation_studio.providers.gpu_journal import MockSessionJournal, SessionRecord
from animation_studio.providers.gpu_lifecycle import MockLifecycle


def record(**changes):
    return SessionRecord(
        session_id='session-1',
        pod_id='owned',
        created_at_utc=100.0,
        deadline_at_utc=200.0,
        **changes,
    )


def journal(tmp_path):
    store = MockSessionJournal(tmp_path / 'session.json')
    store.arm(record())
    return store


def test_roundtrip_restart_closes_even_future_deadline(tmp_path):
    store = journal(tmp_path)
    assert store._read() == record()
    assert os.stat(store.path).st_mode & 0o777 == 0o600
    backend = MockLifecycle('owned')
    result = MockSessionJournal(store.path).recover(backend)
    assert result.cleanup_requested and result.outcome == 'complete'
    assert result.deadline_at_utc == 200 and result.attempt_count == 1
    calls = backend.calls.copy()
    assert store.recover(backend) == result
    assert backend.calls == calls
    with pytest.raises(FileExistsError):
        store.arm(record())


@pytest.mark.parametrize(
    'field,value',
    [
        ('schema_version', 2),
        ('schema_version', True),
        ('mode', 'live'),
        ('api_key', 'secret'),
        ('deadline_at_utc', 99),
        ('deadline_at_utc', float('inf')),
        ('attempt_count', True),
        ('cleanup_requested', 'false'),
        ('pod_id', '../other'),
    ],
)
def test_invalid_record_rejected_before_backend(tmp_path, field, value):
    store = journal(tmp_path)
    data = record().model_dump(mode='json')
    data[field] = value
    store.path.write_text(json.dumps(data))
    backend = MockLifecycle('owned')
    with pytest.raises(ValidationError):
        store.recover(backend)
    assert not backend.calls


def test_corruption_and_identity_mismatch(tmp_path):
    store = journal(tmp_path)
    backend = MockLifecycle('other')
    with pytest.raises(ValueError, match='mismatch'):
        store.recover(backend)
    assert not backend.calls
    store.path.write_text('{')
    with pytest.raises(ValidationError):
        store.recover(backend)
    assert not backend.calls


def test_lock_contention_blocks_second_owner(tmp_path):
    store = journal(tmp_path)
    backend = MockLifecycle('owned')
    with store._locked(), pytest.raises(BlockingIOError):
        MockSessionJournal(store.path).recover(backend)
    assert not backend.calls


def test_failed_intent_write_prevents_mutation(tmp_path, monkeypatch):
    store = journal(tmp_path)

    def fail(*args):
        raise OSError('Disk failure')

    monkeypatch.setattr(os, 'replace', fail)
    backend = MockLifecycle('owned')
    with pytest.raises(OSError):
        store.recover(backend)
    assert not backend.calls and store._read() == record()
    assert not list(tmp_path.glob('.gpu-session-*'))


def test_crash_after_delete_before_result_save_reconciles(tmp_path, monkeypatch):
    store = journal(tmp_path)
    original = store._write
    writes = []

    def crash(record):
        writes.append(record)
        if len(writes) == 2:
            raise OSError('Simulated crash after delete')
        original(record)

    monkeypatch.setattr(store, '_write', crash)
    backend = MockLifecycle('owned', storage='unknown')
    with pytest.raises(OSError):
        store.recover(backend)
    assert store._read().attempt_count == 1
    backend.calls.clear()
    result = MockSessionJournal(store.path).recover(backend)
    assert backend.calls == ['inspect']
    assert result.attempt_count == 2 and result.outcome == 'needs_manual_cleanup'
    assert result.last_storage == 'unknown'


def test_attempt_limit_survives_restarts(tmp_path):
    store = journal(tmp_path)
    backend = MockLifecycle('owned')
    backend.failures.add('terminate')
    for attempt in range(1, 4):
        result = MockSessionJournal(store.path).recover(backend)
        assert result.attempt_count == attempt
    assert result.outcome == 'needs_manual_cleanup'
    before = backend.calls.copy()
    assert store.recover(backend) == result
    assert backend.calls == before


def test_failed_arm_fsync_does_not_report_armed(tmp_path, monkeypatch):
    store = MockSessionJournal(tmp_path / 'session.json')

    def fail(_):
        raise OSError('Sync failed')

    monkeypatch.setattr(os, 'fsync', fail)
    with pytest.raises(OSError):
        store.arm(record())
    assert not store.path.exists()
    assert not list(tmp_path.glob('.gpu-session-*'))
