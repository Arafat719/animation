import json
import multiprocessing
import os
from decimal import Decimal

import pytest
from test_gpu_attempts import inputs

from animation_studio.providers.gpu import GPUProviderError, MockGPUProvider
from animation_studio.providers.gpu_attempts import LedgerConflict, LocalAttemptLedger
from animation_studio.providers.gpu_durable_session import DurableMockRenderSession
from animation_studio.providers.gpu_lifecycle import MockLifecycle
from animation_studio.providers.gpu_mock_session import MockSessionClosed


def open_session(path, *, recover=False, now=100.0, pod='owned', config=None):
    work, limits = inputs()
    provider, backend = MockGPUProvider(), MockLifecycle(pod)
    method = DurableMockRenderSession.recover if recover else DurableMockRenderSession.create
    session = method(
        provider,
        backend,
        LocalAttemptLedger(path),
        work,
        config or limits,
        render_id='render',
        clock=lambda: now,
    )
    return session, provider, backend


@pytest.fixture
def path(tmp_path):
    path = tmp_path / 'ledger.json'
    LocalAttemptLedger(path).initialize()
    return path


def record(path):
    return next(iter(json.loads(path.read_text())['sessions'].values()))


def test_owner_receipt_close_and_recover(path):
    session, provider, _ = open_session(path)
    try:
        with pytest.raises(BlockingIOError):
            open_session(path)
        job = session.submit(shot_id='first', attempt_key='key')
        assert job.status == 'queued'
        assert session.finish().complete
        assert record(path)['closed']
    finally:
        session.release()
    with pytest.raises(LedgerConflict):
        open_session(path)
    recovered, new_provider, _ = open_session(path, recover=True, now=0)
    with recovered:
        assert recovered.closed and recovered.deadline == 700
        with pytest.raises(MockSessionClosed):
            recovered.submit(shot_id='first', attempt_key='new')
        assert new_provider._jobs == {}
        assert (
            LocalAttemptLedger(path)
            .lookup(render_id='render', shot_id='first', attempt_key='key')
            .receipt
        )
    assert len(provider._jobs) == 1


def _crash(path):
    session, _, _ = open_session(path)
    session.submit(shot_id='first', attempt_key='key')
    os._exit(7)


@pytest.mark.parametrize('now', [0, 101, 900, float('nan')])
def test_process_crash_never_resumes_or_renews(path, now):
    child = multiprocessing.get_context('spawn').Process(target=_crash, args=(path,))
    child.start()
    child.join(10)
    assert child.exitcode == 7
    before = record(path)
    recovered, provider, _ = open_session(path, recover=True, now=now)
    with recovered:
        assert recovered.closed
        with pytest.raises(MockSessionClosed):
            recovered.submit(shot_id='first', attempt_key='new')
    after = record(path)
    assert after['deadline'] == before['deadline'] == 700
    assert after['started_at'] == before['started_at'] == 100
    assert after['closed'] and provider._jobs == {}


def test_legacy_used_render_not_enrolled(path):
    ledger = LocalAttemptLedger(path)
    ledger.reserve(*inputs(), render_id='render', shot_id='first', attempt_key='key')
    before = path.read_bytes()
    with pytest.raises(LedgerConflict):
        open_session(path)
    with pytest.raises(ValueError, match='No durable'):
        open_session(path, recover=True)
    assert path.read_bytes() == before
    assert ledger.lookup(render_id='render', shot_id='first', attempt_key='key').receipt is None


def test_identity_mismatch_and_missing_corrupt(path):
    session, _, _ = open_session(path)
    session.release()
    before = path.read_bytes()
    _, config = inputs()
    for kwargs in (
        {'pod': 'other'},
        {'config': config.model_copy(update={'max_gpu_minutes_per_job': Decimal(9)})},
    ):
        with pytest.raises(LedgerConflict):
            open_session(path, recover=True, **kwargs)
    assert path.read_bytes() == before
    path.write_text('{}')
    with pytest.raises(ValueError):
        open_session(path, recover=True)
    path.unlink()
    with pytest.raises(FileNotFoundError):
        open_session(path, recover=True)


@pytest.mark.parametrize('sync_number', [1, 2])
def test_fresh_fsync_failure_no_owner_returned(path, monkeypatch, sync_number):
    original = os.fsync
    calls = 0

    def fail(fd):
        nonlocal calls
        calls += 1
        if calls == sync_number:
            raise OSError('injected fsync')
        original(fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, 'fsync', fail)
        with pytest.raises(OSError):
            open_session(path)
    if sync_number == 2:
        session, provider, _ = open_session(path, recover=True)
        with session:
            assert session.closed and provider._jobs == {}
    else:
        session, _, _ = open_session(path)
        session.release()


def test_close_intent_failure_blocks_admission_before_cleanup(path, monkeypatch):
    session, provider, backend = open_session(path)

    def fail(*args):
        raise OSError('intent write')

    with monkeypatch.context() as patch:
        patch.setattr(session._ledger, '_write', fail)
        with pytest.raises(OSError, match='intent'):
            session.finish()
        with pytest.raises(MockSessionClosed):
            session.submit(shot_id='first', attempt_key='key')
    assert not backend.calls and provider._jobs == {}
    session.release()
    recovered, _, _ = open_session(path, recover=True)
    with recovered:
        assert recovered.closed


def test_bounded_recovery_and_cleanup_failure(path, monkeypatch):
    def failed_termination(*args):
        raise RuntimeError('fixture termination failed')

    monkeypatch.setattr(MockLifecycle, 'terminate', failed_termination)
    session, _, backend = open_session(path)
    backend.failures.add('terminate')
    assert not session.finish().complete
    session.release()
    for _ in range(2):
        recovered, _, _ = open_session(path, recover=True)
        recovered.release()
    recovered, provider, backend = open_session(path, recover=True)
    with recovered:
        assert recovered.closed and not backend.calls
        assert not recovered.cleanup_result.complete
        assert provider._jobs == {}
    assert record(path)['cleanup_attempts'] == 3


def test_deadline_and_failure_persist_close(path, monkeypatch):
    session, provider, backend = open_session(path)
    session._clock = lambda: 700
    with pytest.raises(MockSessionClosed):
        session.submit(shot_id='first', attempt_key='key')
    assert record(path)['closed'] and backend.calls and not provider._jobs
    session.release()


def test_provider_failure_persists_close(path, monkeypatch):
    session, _, _ = open_session(path)
    error = GPUProviderError('timeout', 'ambiguous')

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(MockGPUProvider, 'submit', fail)
    try:
        with pytest.raises(GPUProviderError) as result:
            session.submit(shot_id='first', attempt_key='key')
        assert result.value is error
        assert record(path)['closed']
    finally:
        session.release()


@pytest.mark.parametrize('dispatch_failure', ['provider', 'reservation', 'receipt'])
@pytest.mark.parametrize('cleanup_failure', ['intent', 'result'])
def test_dispatch_and_cleanup_failure_preserve_both_errors(
    path, monkeypatch, dispatch_failure, cleanup_failure
):
    session, provider, backend = open_session(path)
    primary = (
        GPUProviderError('timeout', 'ambiguous submit')
        if dispatch_failure == 'provider'
        else OSError('dispatch persistence failed')
    )
    secondary = OSError('cleanup persistence failed')
    original_write = LocalAttemptLedger._write
    original_submit = MockGPUProvider.submit
    submits = 0

    def submit(self, request, **kwargs):
        nonlocal submits
        submits += 1
        job = original_submit(self, request, **kwargs)
        if dispatch_failure == 'provider':
            raise primary
        return job

    def write(self, state):
        saved = next(iter(state.sessions.values()))
        if saved.closed:
            stage = 'result' if saved.observation is not None else 'intent'
            if stage == cleanup_failure:
                raise secondary
        elif dispatch_failure == 'reservation' or (
            dispatch_failure == 'receipt'
            and any(r.receipt is not None for r in state.reservations.values())
        ):
            raise primary
        return original_write(self, state)

    monkeypatch.setattr(MockGPUProvider, 'submit', submit)
    monkeypatch.setattr(LocalAttemptLedger, '_write', write)
    try:
        with pytest.raises(type(primary)) as caught:
            session.submit(shot_id='first', attempt_key='key')
        assert caught.value is primary
        assert caught.value.__cause__ is secondary
        if dispatch_failure == 'provider':
            assert caught.value.code == 'timeout'
        assert session.closed and session.cleanup_result is None
        assert submits == len(provider._jobs) == (dispatch_failure != 'reservation')
        assert bool(backend.calls) == (cleanup_failure == 'result')
        saved = LocalAttemptLedger(path).session_report(render_id='render')
        assert saved.cleanup_attempts == (cleanup_failure == 'result')
        assert saved.closed == (cleanup_failure == 'result')
        assert saved.observation is None and not saved.complete
        reservation = LocalAttemptLedger(path).lookup(
            render_id='render', shot_id='first', attempt_key='key'
        )
        if dispatch_failure == 'reservation':
            assert reservation is None
        else:
            assert reservation.ordinal == 1 and reservation.receipt is None
        before = path.read_bytes(), submits, list(backend.calls)
        with pytest.raises(MockSessionClosed):
            session.submit(shot_id='first', attempt_key='new')
        assert (path.read_bytes(), submits, backend.calls) == before
    finally:
        session.release()
