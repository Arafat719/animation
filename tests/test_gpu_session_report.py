import json
import os

import pytest
from pydantic import ValidationError
from test_gpu_attempts import inputs
from test_gpu_durable_session import open_session

from animation_studio.providers.gpu import GPUProviderError
from animation_studio.providers.gpu_attempts import LocalAttemptLedger
from animation_studio.providers.gpu_lifecycle import MockLifecycle, ResourceState


@pytest.fixture
def path(tmp_path):
    path = tmp_path / 'ledger.json'
    LocalAttemptLedger(path).initialize()
    return path


def report(path):
    return LocalAttemptLedger(path).session_report(render_id='render')


def test_active_and_released_owner_read_has_no_side_effects(path, monkeypatch):
    session, provider, backend = open_session(path)
    before = path.read_bytes(), set(path.parent.iterdir())

    def forbidden(*args, **kwargs):
        pytest.fail('Read attempted mutation, locking or cleanup')

    try:
        with monkeypatch.context() as patch:
            patch.setattr(LocalAttemptLedger, '_locked', forbidden)
            patch.setattr(LocalAttemptLedger, '_write', forbidden)
            patch.setattr(MockLifecycle, 'inspect', forbidden)
            current = report(path)
            assert not current.closed and current.cleanup_attempts == 0
            assert current.started_at == 100 and current.deadline == 700
            assert current.source == current.compute == current.storage == 'unknown'
            assert not current.complete and not current.live_state_verified
            session.release()
            assert report(path) == current
        assert (path.read_bytes(), set(path.parent.iterdir())) == before
        assert not backend.calls and not provider._jobs
        with pytest.raises(ValidationError):
            current.closed = True
        assert report(path) == current
    finally:
        session.release()


@pytest.mark.parametrize('storage', ['none', 'retained', 'unknown'])
def test_saved_report_and_recovery(path, storage):
    session, _, backend = open_session(path)
    backend.state = ResourceState('owned', 'running', storage)
    session.finish()
    session.release()
    saved = report(path)
    assert saved.closed and saved.cleanup_attempts == 1
    assert saved.source == 'saved' and not saved.live_state_verified
    assert saved.compute == 'absent' and saved.storage == storage
    assert saved.complete == (storage == 'none')
    assert saved.observation.attempt == 1
    with pytest.raises(ValidationError):
        saved.observation.storage = 'unknown'
    recovered, _, _ = open_session(path, recover=True, now=0)
    try:
        assert report(path) == saved
    finally:
        recovered.release()


@pytest.mark.parametrize('unauthorized', [False, True])
def test_failure_observation_read_does_not_retry(path, monkeypatch, unauthorized):
    session, _, backend = open_session(path)
    if unauthorized:

        def denied(*args):
            raise GPUProviderError('unauthorized', 'private error')

        monkeypatch.setattr(MockLifecycle, 'inspect', denied)
    else:
        backend.failures.add('terminate')
    session.finish()
    session.release()
    before = path.read_bytes(), list(backend.calls)
    saved = report(path)
    assert saved.source == 'saved' and not saved.complete
    assert saved.compute == ('unknown' if unauthorized else 'stopped')
    assert saved.observation.provider_codes == ('unauthorized' if unauthorized else 'unavailable',)
    assert (path.read_bytes(), backend.calls) == before


def test_missing_observation_is_unknown_at_cap(path):
    session, _, _ = open_session(path)
    session.finish()
    session.release()
    data = json.loads(path.read_text())
    record = next(iter(data['sessions'].values()))
    del record['observation']
    record['cleanup_attempts'] = 3
    path.write_text(json.dumps(data))
    saved = report(path)
    assert saved.closed and saved.cleanup_attempts == 3
    assert saved.source == saved.compute == saved.storage == 'unknown'
    assert saved.observation is None and not saved.complete


def test_no_session_and_legacy_render_without_creating_locks(path, tmp_path):
    assert report(path) is None
    ledger = LocalAttemptLedger(path)
    ledger.reserve(*inputs(), render_id='render', shot_id='first', attempt_key='key')
    # A standalone snapshot without sidecars must remain standalone.
    snapshot = tmp_path / 'snapshot.json'
    snapshot.write_bytes(path.read_bytes())
    before = set(tmp_path.iterdir())
    assert report(snapshot) is None
    assert set(tmp_path.iterdir()) == before


@pytest.mark.parametrize('value', ['', ' ', 'a' * 4001, None, 12])
def test_invalid_identifier_rejected_before_open(tmp_path, value):
    with pytest.raises(ValueError):
        LocalAttemptLedger(tmp_path / 'missing').session_report(render_id=value)
    assert not list(tmp_path.iterdir())


def test_missing_file_and_symlink_rejected(path, tmp_path):
    with pytest.raises(FileNotFoundError):
        report(tmp_path / 'missing')
    link = tmp_path / 'link'
    link.symlink_to(path)
    with pytest.raises(OSError):
        report(link)


@pytest.mark.parametrize('kind', ['json', 'schema', 'association'])
def test_corruption_never_becomes_empty_report(path, kind):
    session, _, _ = open_session(path)
    session.finish()
    session.release()
    data = json.loads(path.read_text())
    if kind == 'schema':
        data['schema_version'] = 2
    elif kind == 'association':
        next(iter(data['sessions'].values()))['observation']['attempt'] = 2
    path.write_text('{' if kind == 'json' else json.dumps(data))
    before = path.read_bytes()
    with pytest.raises(ValidationError):
        report(path)
    assert path.read_bytes() == before


def test_atomic_replacement_after_open_keeps_whole_old_snapshot(path, monkeypatch):
    session, _, _ = open_session(path)
    old = report(path)
    old_bytes = path.read_bytes()
    session.finish()
    session.release()
    new = report(path)
    replacement = path.with_suffix('.replacement')
    replacement.write_bytes(path.read_bytes())
    path.write_bytes(old_bytes)
    real_open = os.open
    calls = []

    def replace_after_open(target, flags, *args, **kwargs):
        calls.append((target, flags))
        fd = real_open(target, flags, *args, **kwargs)
        os.replace(replacement, path)
        return fd

    with monkeypatch.context() as patch:
        patch.setattr(os, 'open', replace_after_open)
        assert report(path) == old
    assert calls == [(path, os.O_RDONLY | os.O_NOFOLLOW)]
    assert report(path) == new
