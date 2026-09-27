"""Integrated offline owner crash, recovery and durable outcome acceptance."""

import json
import multiprocessing
import os

import pytest
from test_gpu_attempts import inputs

from animation_studio.providers.gpu import MockGPUProvider
from animation_studio.providers.gpu_attempts import LedgerConflict, LocalAttemptLedger
from animation_studio.providers.gpu_durable_session import DurableMockRenderSession
from animation_studio.providers.gpu_lifecycle import MockLifecycle
from animation_studio.providers.gpu_mock_session import MockSessionClosed


def _owner(path, pipe):
    provider = MockGPUProvider()
    session = DurableMockRenderSession.create(
        provider,
        MockLifecycle('owned'),
        LocalAttemptLedger(path),
        *inputs(),
        render_id='acceptance',
        clock=lambda: 100.0,
    )
    first = session.submit(shot_id='first', attempt_key='accepted')
    pipe.send(first.job_id)
    if not pipe.poll(10) or pipe.recv() != 'crash-after-accept':
        os._exit(9)
    original = MockGPUProvider.submit

    def accept_then_exit(self, request, **kwargs):
        original(self, request, **kwargs)
        os._exit(7)  # The second job was accepted, but no response/receipt was saved.

    MockGPUProvider.submit = accept_then_exit
    session.submit(shot_id='second', attempt_key='unknown')


def test_durable_restart_integrated_acceptance(tmp_path):
    path = tmp_path / 'acceptance.json'
    ledger = LocalAttemptLedger(path)
    ledger.initialize()
    context = multiprocessing.get_context('spawn')
    parent, child_end = context.Pipe()
    child = context.Process(target=_owner, args=(path, child_end))
    child.start()
    child_end.close()
    provider = MockGPUProvider()
    backend = MockLifecycle('owned', storage='unknown')

    def open_session(method):
        return method(
            provider, backend, ledger, *inputs(), render_id='acceptance', clock=lambda: 0.0
        )

    def lookup(shot, key):
        return ledger.lookup(render_id='acceptance', shot_id=shot, attempt_key=key)

    try:
        assert parent.poll(10), 'Owner did not finish the first submission'
        job_id = parent.recv()
        assert lookup('first', 'accepted').receipt.job_id == job_id
        with pytest.raises(BlockingIOError):
            open_session(DurableMockRenderSession.recover)
        parent.send('crash-after-accept')
        child.join(10)
        assert child.exitcode == 7
    finally:
        if child.is_alive():
            child.kill()
            child.join(5)
        parent.close()

    before = json.loads(path.read_text())
    old_session = next(iter(before['sessions'].values()))
    assert not old_session['closed']
    assert lookup('second', 'unknown').receipt is None
    with pytest.raises(LedgerConflict):
        open_session(DurableMockRenderSession.create)
    with open_session(DurableMockRenderSession.recover) as recovered:
        assert recovered.closed and recovered.deadline == old_session['deadline'] == 700
        assert recovered.cleanup_result.state.compute == 'absent'
        assert recovered.cleanup_result.state.storage == 'unknown'
        assert not recovered.cleanup_result.complete
        snapshot = path.read_bytes()
        for shot, key in [('first', 'accepted'), ('second', 'unknown'), ('first', 'new')]:
            with pytest.raises(MockSessionClosed):
                recovered.submit(shot_id=shot, attempt_key=key)
        assert lookup('first', 'accepted').receipt.job_id == job_id
        assert lookup('second', 'unknown').receipt is None
        assert lookup('first', 'new') is None
        assert path.read_bytes() == snapshot
        assert provider._jobs == {}
    after = json.loads(path.read_text())
    new_session = next(iter(after['sessions'].values()))
    assert new_session['closed'] and new_session['cleanup_attempts'] == 1
    assert new_session['started_at'] == old_session['started_at']
    assert new_session['deadline'] == old_session['deadline']
    assert after['reservations'] == before['reservations']
    assert backend.calls == ['inspect', 'stop', 'terminate', 'inspect']
