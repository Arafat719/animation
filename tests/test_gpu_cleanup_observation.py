import json

import pytest
from pydantic import ValidationError
from test_gpu_durable_session import open_session, record

from animation_studio.providers.gpu import GPUProviderError
from animation_studio.providers.gpu_attempts import LocalAttemptLedger
from animation_studio.providers.gpu_lifecycle import MockLifecycle, ResourceState
from animation_studio.providers.gpu_mock_session import MockSessionClosed


@pytest.fixture
def path(tmp_path):
    path = tmp_path / 'ledger.json'
    LocalAttemptLedger(path).initialize()
    return path


@pytest.mark.parametrize('storage', ['none', 'retained', 'unknown'])
def test_saved_absent_does_not_repeat_cleanup(path, storage):
    session, _, backend = open_session(path)
    backend.state = ResourceState('owned', 'running', storage)
    result = session.finish()
    assert result.source == 'current_call' and result.observed_attempt == 1
    session.release()
    before = path.read_bytes()
    recovered, provider, backend = open_session(path, recover=True)
    with recovered:
        result = recovered.cleanup_result
        assert result.source == 'saved' and not result.live_state_verified
        assert result.complete == (storage == 'none')
        assert result.state.storage == storage
        assert not backend.calls and provider._jobs == {}
        with pytest.raises(MockSessionClosed):
            recovered.submit(shot_id='first', attempt_key='new')
    assert path.read_bytes() == before


def test_unauthorized_saved_terminal(path, monkeypatch):
    def unauthorized(*args):
        raise GPUProviderError('unauthorized', 'private error not persisted')

    monkeypatch.setattr(MockLifecycle, 'inspect', unauthorized)
    session, _, _ = open_session(path)
    assert session.finish().provider_codes == ('unauthorized',)
    session.release()
    recovered, _, backend = open_session(path, recover=True)
    with recovered:
        assert recovered.cleanup_result.source == 'saved'
        assert not recovered.cleanup_result.complete and not backend.calls
    assert record(path)['cleanup_attempts'] == 1
    assert 'private error' not in path.read_text()


def test_failed_result_write_clears_old_observation(path, monkeypatch):
    session, _, backend = open_session(path)
    backend.failures.add('terminate')
    assert not session.finish().complete
    session.release()
    original = LocalAttemptLedger._write
    calls = 0

    def fail_result(self, state):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError('result save failed')
        return original(self, state)

    with monkeypatch.context() as patch:
        patch.setattr(LocalAttemptLedger, '_write', fail_result)
        with pytest.raises(OSError):
            open_session(path, recover=True)
    data = record(path)
    assert data['closed'] and data['cleanup_attempts'] == 2
    assert 'observation' not in data
    recovered, _, _ = open_session(path, recover=True)
    with recovered:
        assert recovered.cleanup_result.source == 'current_call'
        assert recovered.cleanup_result.observed_attempt == 3
    again, _, backend = open_session(path, recover=True)
    with again:
        assert again.cleanup_result.source == 'saved' and not backend.calls


@pytest.mark.parametrize(
    'field,value', [('pod_id', 'wrong'), ('attempt', 2), ('compute', 'invalid')]
)
def test_malformed_observation_rejected(path, field, value):
    session, _, _ = open_session(path)
    session.finish()
    session.release()
    data = json.loads(path.read_text())
    next(iter(data['sessions'].values()))['observation'][field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        open_session(path, recover=True)


def test_legacy_without_observation_stays_unknown_until_cleanup(path):
    session, _, _ = open_session(path)
    session.finish()
    session.release()
    data = json.loads(path.read_text())
    saved = next(iter(data['sessions'].values()))
    del saved['observation']
    saved['cleanup_attempts'] = 3
    path.write_text(json.dumps(data))
    recovered, _, backend = open_session(path, recover=True)
    with recovered:
        assert recovered.cleanup_result.source == 'unknown'
        assert not recovered.cleanup_result.complete and not backend.calls


@pytest.mark.parametrize('failure_at', [3, 4])
def test_observation_fsync_failure_never_reports_success(path, monkeypatch, failure_at):
    import os

    session, _, _ = open_session(path)
    original = os.fsync
    count = 0

    def fail(fd):
        nonlocal count
        count += 1
        if count == failure_at:
            raise OSError('observation fsync failed')
        original(fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, 'fsync', fail)
        with pytest.raises(OSError):
            session.finish()
    assert session.closed and session.cleanup_result is None
    session.release()
    recovered, _, backend = open_session(path, recover=True)
    with recovered:
        assert recovered.closed
        assert recovered.cleanup_result.source == ('current_call' if failure_at == 3 else 'saved')
        if failure_at == 4:
            assert not backend.calls


def _crash_before_observation(path):
    import os

    session, _, _ = open_session(path)
    original = LocalAttemptLedger._write
    count = 0

    def write(self, state):
        nonlocal count
        count += 1
        if count == 2:
            os._exit(7)
        return original(self, state)

    LocalAttemptLedger._write = write
    session.finish()


def test_crash_after_cleanup_before_observation_is_unknown(path):
    import multiprocessing

    child = multiprocessing.get_context('spawn').Process(
        target=_crash_before_observation, args=(path,)
    )
    child.start()
    child.join(10)
    assert child.exitcode == 7
    saved = record(path)
    assert saved['closed'] and saved['cleanup_attempts'] == 1
    assert 'observation' not in saved
    recovered, _, _ = open_session(path, recover=True)
    with recovered:
        assert recovered.cleanup_result.source == 'current_call'
        assert recovered.cleanup_result.observed_attempt == 2
