import json
import multiprocessing
import os

import pytest
from pydantic import ValidationError
from test_gpu_attempts import inputs
from test_gpu_mock_dispatch import dispatch

from animation_studio.providers.gpu import GPUProviderError, MockGPUProvider
from animation_studio.providers.gpu_attempts import LedgerConflict, LocalAttemptLedger
from animation_studio.providers.gpu_mock_dispatch import AttemptAlreadyReserved


@pytest.fixture
def setup(tmp_path):
    ledger = LocalAttemptLedger(tmp_path / 'ledger.json')
    ledger.initialize()
    return ledger, MockGPUProvider()


def lookup(ledger, **overrides):
    args = {'render_id': 'render', 'shot_id': 'first', 'attempt_key': 'key'}
    args.update(overrides)
    return ledger.lookup(**args)


def test_receipt_reopen_and_lookup_is_read_only(setup, monkeypatch):
    ledger, provider = setup
    assert lookup(ledger) is None
    job = dispatch(ledger, provider)
    before = ledger.path.read_bytes()
    files = set(ledger.path.parent.iterdir())

    def forbidden(*args, **kwargs):
        raise AssertionError('Lookup must not write or contact provider')

    monkeypatch.setattr(MockGPUProvider, 'submit', forbidden)
    monkeypatch.setattr(MockGPUProvider, 'status', forbidden)
    monkeypatch.setattr(LocalAttemptLedger, '_write', forbidden)
    result = lookup(LocalAttemptLedger(ledger.path))
    assert result.receipt.job_id == job.job_id
    assert result.receipt.outcome == 'submitted'
    assert ledger.path.read_bytes() == before
    assert set(ledger.path.parent.iterdir()) == files
    with pytest.raises(AttemptAlreadyReserved) as error:
        dispatch(ledger, provider)
    assert error.value.reservation.receipt == result.receipt
    assert 'private-prompt' not in ledger.path.read_text()


def test_old_v1_unknown_and_identity_conflict(setup):
    ledger, _ = setup
    work, config = inputs()
    ledger.reserve(work, config, render_id='render', shot_id='first', attempt_key='key')
    assert 'receipt' not in ledger.path.read_text()
    assert lookup(ledger).receipt is None
    for override in ({'shot_id': 'second'}, {'render_id': 'other'}):
        with pytest.raises(LedgerConflict):
            lookup(ledger, **override)


def test_accept_then_timeout_remains_unknown(setup, monkeypatch):
    ledger, provider = setup
    original = MockGPUProvider.submit

    def ambiguous(self, request, **kwargs):
        original(self, request, **kwargs)
        raise GPUProviderError('timeout', 'Ambiguous')

    monkeypatch.setattr(MockGPUProvider, 'submit', ambiguous)
    with pytest.raises(GPUProviderError):
        dispatch(ledger, provider)
    assert lookup(ledger).receipt is None
    with pytest.raises(AttemptAlreadyReserved):
        dispatch(ledger, provider)
    assert len(provider._jobs) == 1


@pytest.mark.parametrize('sync_number', [3, 4])
def test_receipt_sync_failure_never_resubmits(setup, monkeypatch, sync_number):
    ledger, provider = setup
    original = os.fsync
    calls = 0

    def failure(fd):
        nonlocal calls
        calls += 1
        if calls == sync_number:
            raise OSError('receipt sync failed')
        original(fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, 'fsync', failure)
        with pytest.raises(OSError, match='receipt sync'):
            dispatch(ledger, provider)
    result = lookup(ledger)
    assert (result.receipt is None) == (sync_number == 3)
    with pytest.raises(AttemptAlreadyReserved):
        dispatch(ledger, provider)
    assert len(provider._jobs) == 1


def _child_submit(path):
    dispatch(LocalAttemptLedger(path), MockGPUProvider())
    os._exit(0)


def test_receipt_survives_provider_process_exit(setup):
    ledger, _ = setup
    child = multiprocessing.get_context('spawn').Process(target=_child_submit, args=(ledger.path,))
    child.start()
    child.join(10)
    assert child.exitcode == 0
    result = lookup(ledger)
    assert result.receipt.job_id == 'mock-gpu-1'
    assert result.receipt.outcome == 'submitted'  # No claim that the job still exists.


@pytest.mark.parametrize('corrupt', [False, True])
def test_lookup_missing_or_corrupt_never_returns_unknown(setup, corrupt):
    ledger, _ = setup
    if corrupt:
        ledger.path.write_text('{}')
        error = ValidationError
    else:
        ledger.path.unlink()
        error = FileNotFoundError
    with pytest.raises(error):
        lookup(ledger)


def test_invalid_receipt_fails_closed(setup):
    ledger, provider = setup
    dispatch(ledger, provider)
    state = json.loads(ledger.path.read_text())
    next(iter(state['reservations'].values()))['receipt']['outcome'] = 'succeeded'
    ledger.path.write_text(json.dumps(state))
    with pytest.raises(ValidationError):
        lookup(ledger)
    with pytest.raises(ValidationError):
        dispatch(ledger, provider)
    assert len(provider._jobs) == 1
