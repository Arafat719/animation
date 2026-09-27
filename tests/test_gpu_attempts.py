import json
import multiprocessing
import os
from decimal import Decimal

import pytest
from pydantic import ValidationError

from animation_studio.providers.gpu import GPUJobRequest
from animation_studio.providers.gpu_attempts import (
    AttemptLimitExceeded,
    LedgerConflict,
    LocalAttemptLedger,
)
from animation_studio.providers.gpu_budget import (
    BudgetConfig,
    BudgetExceeded,
    PlannedGPUShot,
    RenderWorkload,
)


def inputs(attempts=2):
    request = GPUJobRequest(
        operation='mock.noop',
        prompt='private-prompt-নদী',
        model_name='mock-worker',
        model_version='1',
    )
    workload = RenderWorkload(
        gpu_hourly_price='1',
        startup_gpu_minutes='0',
        shots=tuple(
            PlannedGPUShot(
                shot_id=shot,
                request=request,
                gpu_minutes_per_attempt='1',
                attempts=attempts,
            )
            for shot in ('first', 'second')
        ),
    )
    config = BudgetConfig(
        max_gpu_hourly_price='1',
        max_gpu_minutes_per_job='10',
        max_attempts_per_shot=2,
        max_estimated_cost_per_render='1',
    )
    return workload, config


def reserve(ledger, key='key', **kwargs):
    workload, config = inputs()
    return ledger.reserve(
        workload, config, render_id='render', shot_id='first', attempt_key=key, **kwargs
    )


@pytest.fixture
def ledger(tmp_path):
    result = LocalAttemptLedger(tmp_path / 'attempts.json')
    result.initialize()
    return result


def test_replay_reopen_and_limit(ledger):
    first = reserve(ledger)
    reopened = LocalAttemptLedger(ledger.path)
    assert reserve(reopened) == first
    assert reserve(reopened, 'key2').ordinal == 2
    assert reserve(reopened) == first  # Replay remains valid at the cap.
    with pytest.raises(AttemptLimitExceeded):
        reserve(reopened, 'key3')
    with pytest.raises(FileExistsError):
        reopened.initialize()


@pytest.mark.parametrize('change', ['render', 'shot', 'workload', 'config'])
def test_conflicting_identity_never_mutates(ledger, change):
    reserve(ledger)
    before = ledger.path.read_bytes()
    work, config = inputs()
    render_id, shot_id = 'render', 'first'
    if change == 'render':
        render_id = 'different'
    elif change == 'shot':
        shot_id = 'second'
    elif change == 'workload':
        work = work.model_copy(update={'startup_gpu_minutes': Decimal(1)})
    else:
        config = config.model_copy(update={'max_gpu_minutes_per_job': Decimal(9)})
    with pytest.raises(LedgerConflict):
        ledger.reserve(work, config, render_id=render_id, shot_id=shot_id, attempt_key='key')
    assert ledger.path.read_bytes() == before


def test_changed_render_with_new_key_and_shot_limits(ledger):
    reserve(ledger)
    work, config = inputs(1)
    with pytest.raises(LedgerConflict):
        ledger.reserve(work, config, render_id='render', shot_id='first', attempt_key='new')
    other = ledger.reserve(work, config, render_id='other', shot_id='first', attempt_key='other')
    assert other.ordinal == 1
    with pytest.raises(AttemptLimitExceeded):
        ledger.reserve(work, config, render_id='other', shot_id='first', attempt_key='over')
    assert (
        ledger.reserve(
            work, config, render_id='other', shot_id='second', attempt_key='second'
        ).ordinal
        == 1
    )


def test_invalid_and_over_budget_leave_no_admission(ledger):
    work, config = inputs()
    before = ledger.path.read_bytes()
    with pytest.raises(BudgetExceeded):
        ledger.reserve(
            work,
            config.model_copy(update={'max_estimated_cost_per_render': Decimal(0)}),
            render_id='render',
            shot_id='first',
            attempt_key='key',
        )
    with pytest.raises(ValueError, match='not part'):
        ledger.reserve(work, config, render_id='render', shot_id='absent', attempt_key='key')
    for key in ('', ' ', 'x' * 4001, 2):
        with pytest.raises(ValueError):
            reserve(ledger, key)
    with pytest.raises(ValidationError):
        ledger.reserve(
            work.model_copy(update={'gpu_hourly_price': Decimal(-1)}),
            config,
            render_id='render',
            shot_id='first',
            attempt_key='key',
        )
    assert ledger.path.read_bytes() == before


@pytest.mark.parametrize(
    'corruption', ['garbage', 'empty', 'version', 'gap', 'limit', 'extra', 'missing']
)
def test_corrupt_state_fails_closed(ledger, corruption):
    reserve(ledger)
    state = json.loads(ledger.path.read_text())
    if corruption in ('garbage', 'empty'):
        data = 'not json' if corruption == 'garbage' else ''
    else:
        if corruption == 'missing':
            del state['reservations']
        elif corruption == 'version':
            state['schema_version'] = 2
        elif corruption == 'gap':
            next(iter(state['reservations'].values()))['ordinal'] = 2
        elif corruption == 'limit':
            next(iter(state['renders'].values()))['limits'] = {}
        else:
            state['unexpected'] = True
        data = json.dumps(state)
    ledger.path.write_text(data)
    with pytest.raises(ValidationError):
        reserve(ledger, 'new')
    assert ledger.path.read_text() == data


def test_missing_state_is_not_recreated(ledger):
    ledger.path.unlink()
    with pytest.raises(FileNotFoundError):
        reserve(ledger)
    assert not ledger.path.exists()


@pytest.mark.parametrize('failure', ['replace', 'file_sync', 'directory_sync'])
def test_durable_write_failure_never_reports_success(ledger, monkeypatch, failure):
    original_sync = os.fsync
    calls = 0

    def fail_sync(fd):
        nonlocal calls
        calls += 1
        if calls == (1 if failure == 'file_sync' else 2):
            raise OSError('injected fsync failure')
        original_sync(fd)

    def fail_replace(*args):
        raise OSError('injected replace failure')

    with monkeypatch.context() as patch:
        if failure == 'replace':
            patch.setattr(os, 'replace', fail_replace)
        else:
            patch.setattr(os, 'fsync', fail_sync)
        with pytest.raises(OSError, match='injected'):
            reserve(ledger)
    # Ambiguous directory sync may leave the reservation consumed; same key is safe.
    assert reserve(ledger).ordinal == 1
    assert reserve(ledger, 'second').ordinal == 2
    with pytest.raises(AttemptLimitExceeded):
        reserve(ledger, 'third')
    assert not list(ledger.path.parent.glob('.gpu-attempts-*'))


def _crash_after_reserve(path):
    reserve(LocalAttemptLedger(path))
    os._exit(7)


def test_process_exit_keeps_reserved_slot(ledger):
    context = multiprocessing.get_context('spawn')
    child = context.Process(target=_crash_after_reserve, args=(ledger.path,))
    child.start()
    child.join(10)
    assert not child.is_alive()
    assert child.exitcode == 7
    assert reserve(ledger).ordinal == 1
    assert reserve(ledger, 'second').ordinal == 2
    with pytest.raises(AttemptLimitExceeded):
        reserve(ledger, 'third')


def _contend(path, key, barrier, results):
    barrier.wait(timeout=10)
    try:
        result = reserve(LocalAttemptLedger(path), key)
        results.put(('reserved', result.ordinal))
    except AttemptLimitExceeded:
        results.put(('full', None))
    except BlockingIOError:
        results.put(('busy', None))


def test_concurrent_processes_cannot_take_same_last_slot(ledger):
    reserve(ledger)
    context = multiprocessing.get_context('spawn')
    barrier, results = context.Barrier(2), context.Queue()
    children = [
        context.Process(target=_contend, args=(ledger.path, key, barrier, results))
        for key in ('second', 'third')
    ]
    for child in children:
        child.start()
    for child in children:
        child.join(10)
        assert not child.is_alive()
        assert child.exitcode == 0
    outcomes = [results.get(timeout=2) for _ in children]
    assert outcomes.count(('reserved', 2)) == 1
    assert sum(status in ('full', 'busy') for status, _ in outcomes) == 1
    with pytest.raises(AttemptLimitExceeded):
        reserve(ledger, 'fourth')


def test_private_file_and_no_raw_payload(ledger):
    reserve(ledger, 'sensitive-attempt-key')
    raw = ledger.path.read_text()
    for secret in ('private-prompt', 'নদী', 'sensitive-attempt-key', 'mock-worker', 'first'):
        assert secret not in raw
    assert ledger.path.stat().st_mode & 0o777 == 0o600
    assert ledger.path.with_name(ledger.path.name + '.lock').stat().st_mode & 0o777 == 0o600
