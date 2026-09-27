import json
import multiprocessing
import os
from decimal import Decimal

import pytest
from test_gpu_attempts import inputs

from animation_studio.providers.gpu import GPUProviderError, MockGPUProvider
from animation_studio.providers.gpu_attempts import (
    AttemptLimitExceeded,
    LedgerConflict,
    LocalAttemptLedger,
)
from animation_studio.providers.gpu_budget import BudgetExceeded
from animation_studio.providers.gpu_mock_dispatch import (
    AttemptAlreadyReserved,
    submit_mock_budgeted_shot,
)


@pytest.fixture
def setup(tmp_path):
    ledger = LocalAttemptLedger(tmp_path / 'ledger.json')
    ledger.initialize()
    return ledger, MockGPUProvider()


def dispatch(ledger, provider, key='key', **overrides):
    work, config = inputs()
    args = {'render_id': 'render', 'shot_id': 'first', 'attempt_key': key}
    args.update(overrides)
    return submit_mock_budgeted_shot(provider, ledger, work, config, **args)


def test_success_replay_reopen_and_cap(setup):
    ledger, provider = setup
    job = dispatch(ledger, provider)
    assert job.status == 'queued'
    assert provider.status(job.job_id) == job
    for current in (ledger, LocalAttemptLedger(ledger.path)):
        with pytest.raises(AttemptAlreadyReserved) as error:
            dispatch(current, provider)
        assert error.value.reservation.ordinal == 1
    assert dispatch(ledger, provider, 'second').job_id == 'mock-gpu-2'
    with pytest.raises(AttemptLimitExceeded):
        dispatch(ledger, provider, 'third')
    assert len(provider._jobs) == 2


def test_old_v1_reservation_is_never_dispatched(setup):
    ledger, provider = setup
    work, config = inputs()
    ledger.reserve(work, config, render_id='render', shot_id='first', attempt_key='key')
    # Original v1 shape has no dispatch fields; it remains readable without migration.
    assert set(json.loads(ledger.path.read_text())) == {'schema_version', 'renders', 'reservations'}
    with pytest.raises(AttemptAlreadyReserved):
        dispatch(ledger, provider)
    assert provider._jobs == {}


@pytest.mark.parametrize('accepted', [False, True])
def test_ambiguous_failure_never_retries(setup, monkeypatch, accepted):
    ledger, provider = setup
    original = MockGPUProvider.submit
    calls = []

    def ambiguous(self, request, *, timeout_seconds=10):
        calls.append(request)
        if accepted:
            original(self, request, timeout_seconds=timeout_seconds)
        raise GPUProviderError('timeout', 'Injected ambiguous submit')

    monkeypatch.setattr(MockGPUProvider, 'submit', ambiguous)
    with pytest.raises(GPUProviderError, match='Injected'):
        dispatch(ledger, provider)
    with pytest.raises(AttemptAlreadyReserved):
        dispatch(LocalAttemptLedger(ledger.path), MockGPUProvider())
    assert len(calls) == 1
    assert len(provider._jobs) == int(accepted)


@pytest.mark.parametrize('stage', ['file', 'directory'])
def test_fsync_failure_causes_zero_submits(setup, monkeypatch, stage):
    ledger, provider = setup
    original = os.fsync
    calls = 0

    def fail(fd):
        nonlocal calls
        calls += 1
        if calls == (1 if stage == 'file' else 2):
            raise OSError('Injected sync failure')
        original(fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, 'fsync', fail)
        with pytest.raises(OSError):
            dispatch(ledger, provider)
    assert provider._jobs == {}
    if stage == 'directory':
        with pytest.raises(AttemptAlreadyReserved):
            dispatch(ledger, provider)
        assert provider._jobs == {}
    else:
        assert dispatch(ledger, provider).status == 'queued'


def test_preflight_conflict_and_invalid_timeout_make_no_extra_calls(setup):
    ledger, provider = setup
    work, config = inputs()
    before = ledger.path.read_bytes()
    with pytest.raises(BudgetExceeded):
        submit_mock_budgeted_shot(
            provider,
            ledger,
            work,
            config.model_copy(update={'max_estimated_cost_per_render': Decimal(0)}),
            render_id='render',
            shot_id='first',
            attempt_key='key',
        )
    with pytest.raises(GPUProviderError):
        dispatch(ledger, provider, timeout_seconds=0)
    assert ledger.path.read_bytes() == before
    assert provider._jobs == {}
    dispatch(ledger, provider)
    with pytest.raises(LedgerConflict):
        dispatch(ledger, provider, shot_id='second')
    assert len(provider._jobs) == 1


def test_nonmock_and_subclass_rejected_before_admission(setup):
    ledger, _ = setup

    class PretendMock(MockGPUProvider):
        pass

    before = ledger.path.read_bytes()
    for provider in (object(), PretendMock()):
        with pytest.raises(TypeError):
            dispatch(ledger, provider)
    assert ledger.path.read_bytes() == before


def _crash_before_submit(path):
    def crash(self, request, *, timeout_seconds=10):
        os._exit(7)

    MockGPUProvider.submit = crash
    dispatch(LocalAttemptLedger(path), MockGPUProvider())


def test_crash_after_reservation_prevents_restart_submit(setup):
    ledger, provider = setup
    context = multiprocessing.get_context('spawn')
    child = context.Process(target=_crash_before_submit, args=(ledger.path,))
    child.start()
    child.join(10)
    assert child.exitcode == 7
    with pytest.raises(AttemptAlreadyReserved):
        dispatch(ledger, provider)
    assert provider._jobs == {}


def _race(path, barrier, results):
    provider = MockGPUProvider()
    barrier.wait(timeout=10)
    try:
        dispatch(LocalAttemptLedger(path), provider)
        status = 'submitted'
    except AttemptAlreadyReserved:
        status = 'reserved'
    except BlockingIOError:
        status = 'busy'
    results.put((status, len(provider._jobs)))


def test_same_key_concurrent_processes_submit_at_most_once(setup):
    ledger, provider = setup
    context = multiprocessing.get_context('spawn')
    barrier, results = context.Barrier(2), context.Queue()
    children = [
        context.Process(target=_race, args=(ledger.path, barrier, results)) for _ in range(2)
    ]
    for child in children:
        child.start()
    for child in children:
        child.join(10)
        assert child.exitcode == 0
    outcomes = [results.get(timeout=2) for _ in children]
    assert sum(count for _, count in outcomes) == 1
    assert sum(status == 'submitted' for status, _ in outcomes) == 1
    with pytest.raises(AttemptAlreadyReserved):
        dispatch(ledger, provider)
    assert provider._jobs == {}
