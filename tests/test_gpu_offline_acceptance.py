"""Bounded offline acceptance of admission, mock submission and durable lookup."""

from decimal import Decimal

import pytest
from test_gpu_attempts import inputs

from animation_studio.providers.gpu import GPUProviderError, MockGPUProvider
from animation_studio.providers.gpu_attempts import AttemptLimitExceeded, LocalAttemptLedger
from animation_studio.providers.gpu_budget import BudgetExceeded, estimate_render
from animation_studio.providers.gpu_mock_dispatch import (
    AttemptAlreadyReserved,
    submit_mock_budgeted_shot,
)


def test_budget_dispatch_receipt_recovery_scenario(tmp_path, monkeypatch):
    work, config = inputs()
    ledger = LocalAttemptLedger(tmp_path / 'acceptance.json')
    ledger.initialize()
    provider = MockGPUProvider()
    original_submit = MockGPUProvider.submit
    calls = []
    lose_response = False

    def observed_submit(self, request, **kwargs):
        calls.append(request)
        job = original_submit(self, request, **kwargs)
        if lose_response:
            raise GPUProviderError('timeout', 'Offline fixture: accepted response lost')
        return job

    monkeypatch.setattr(MockGPUProvider, 'submit', observed_submit)

    def submit(shot, key, limits=config):
        return submit_mock_budgeted_shot(
            provider,
            ledger,
            work,
            limits,
            render_id='acceptance',
            shot_id=shot,
            attempt_key=key,
        )

    def lookup(shot, key):
        return ledger.lookup(render_id='acceptance', shot_id=shot, attempt_key=key)

    estimate = estimate_render(work, config)
    assert estimate.allowed
    assert estimate.reserved_gpu_minutes == Decimal(4)
    assert estimate.estimated_compute_cost == Decimal('0.066667')
    before = ledger.path.read_bytes()
    with pytest.raises(BudgetExceeded):
        submit(
            'first',
            'blocked',
            config.model_copy(update={'max_estimated_cost_per_render': Decimal(0)}),
        )
    assert ledger.path.read_bytes() == before
    assert lookup('first', 'blocked') is None
    assert calls == []

    job = submit('first', 'accepted')
    assert lookup('first', 'accepted').receipt.job_id == job.job_id
    lose_response = True
    with pytest.raises(GPUProviderError, match='response lost'):
        submit('second', 'ambiguous')
    assert lookup('second', 'ambiguous').receipt is None
    assert len(calls) == len(provider._jobs) == 2

    # Reopen durable state and replace the process-local provider to simulate recovery.
    ledger = LocalAttemptLedger(ledger.path)
    provider = MockGPUProvider()
    before = ledger.path.read_bytes()
    assert lookup('first', 'accepted').receipt.outcome == 'submitted'
    assert lookup('second', 'ambiguous').receipt is None
    for shot, key in [('first', 'accepted'), ('second', 'ambiguous')]:
        with pytest.raises(AttemptAlreadyReserved):
            submit(shot, key)
    assert len(calls) == 2
    assert provider._jobs == {}
    assert ledger.path.read_bytes() == before

    # Explicit separate attempt for the known submitted shot; never retry the unknown one.
    lose_response = False
    submit('first', 'explicit-second-attempt')
    assert lookup('first', 'explicit-second-attempt').ordinal == 2
    with pytest.raises(AttemptLimitExceeded):
        submit('first', 'over-cap')
    assert lookup('first', 'over-cap') is None
    assert len(calls) == 3
    assert lookup('second', 'ambiguous').receipt is None
    assert 'private-prompt' not in ledger.path.read_text()
