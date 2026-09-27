from decimal import Decimal

import pytest
from test_gpu_attempts import inputs

from animation_studio.providers.gpu import GPUProviderError, MockGPUProvider
from animation_studio.providers.gpu_attempts import AttemptLimitExceeded, LocalAttemptLedger
from animation_studio.providers.gpu_budget import BudgetExceeded
from animation_studio.providers.gpu_lifecycle import MockLifecycle
from animation_studio.providers.gpu_mock_dispatch import AttemptAlreadyReserved
from animation_studio.providers.gpu_mock_session import MockRenderSession, MockSessionClosed


@pytest.fixture
def setup(tmp_path):
    ledger = LocalAttemptLedger(tmp_path / 'ledger.json')
    ledger.initialize()
    provider, backend = MockGPUProvider(), MockLifecycle('owned')
    now = [100.0]
    session = MockRenderSession(
        provider, backend, ledger, *inputs(), render_id='render', clock=lambda: now[0]
    )
    return session, now, ledger, provider, backend


def submit(session, key='key'):
    return session.submit(shot_id='first', attempt_key=key)


def test_boundary_cleanup_and_lookup(setup):
    session, now, ledger, provider, backend = setup
    assert session.deadline == 700
    now[0] = 699.9
    submit(session)
    assert not session.closed and not backend.calls
    before = ledger.path.read_bytes()
    now[0] = 700
    with pytest.raises(MockSessionClosed):
        submit(session, 'new')
    assert session.cleanup_result.complete
    assert ledger.path.read_bytes() == before
    assert len(provider._jobs) == 1
    assert ledger.lookup(render_id='render', shot_id='first', attempt_key='key').receipt
    now[0] = 701
    with pytest.raises(MockSessionClosed):
        submit(session, 'new')
    assert backend.calls.count('terminate') == 1
    assert session.deadline == 700


@pytest.mark.parametrize('method', ['finish', 'fail'])
@pytest.mark.parametrize('storage', ['none', 'retained', 'unknown'])
def test_early_close_storage(setup, method, storage):
    session, _, _, _, backend = setup
    from animation_studio.providers.gpu_lifecycle import ResourceState

    backend.state = ResourceState('owned', 'running', storage)
    result = getattr(session, method)()
    assert result.state.compute == 'absent'
    assert result.complete == (storage == 'none')
    with pytest.raises(MockSessionClosed):
        submit(session)


def test_cleanup_failure_never_reopens(setup):
    session, now, _, provider, backend = setup
    backend.failures.add('terminate')
    now[0] = session.deadline
    with pytest.raises(MockSessionClosed):
        submit(session)
    assert session.closed and not session.cleanup_result.complete
    backend.failures.clear()
    assert session.tick().complete
    assert provider._jobs == {}


def test_replay_cap_invalid_input_do_not_close(setup):
    session, _, _, provider, _ = setup
    with pytest.raises(ValueError):
        session.submit(shot_id='missing', attempt_key='x')
    with pytest.raises(GPUProviderError):
        session.submit(shot_id='first', attempt_key='x', timeout_seconds=0)
    submit(session)
    with pytest.raises(AttemptAlreadyReserved):
        submit(session)
    submit(session, 'second')
    with pytest.raises(AttemptLimitExceeded):
        submit(session, 'third')
    assert not session.closed and len(provider._jobs) == 2


def test_timeout_unknown_closes_and_preserves_error(setup, monkeypatch):
    session, _, ledger, provider, _ = setup
    original = MockGPUProvider.submit
    error = GPUProviderError('timeout', 'ambiguous')

    def timeout(self, request, **kwargs):
        original(self, request, **kwargs)
        raise error

    monkeypatch.setattr(MockGPUProvider, 'submit', timeout)
    with pytest.raises(GPUProviderError) as caught:
        submit(session)
    assert caught.value is error
    assert session.closed and session.cleanup_result.complete
    assert ledger.lookup(render_id='render', shot_id='first', attempt_key='key').receipt is None
    with pytest.raises(MockSessionClosed):
        submit(session)
    assert len(provider._jobs) == 1


def test_post_submit_overrun_cleanup(setup, monkeypatch):
    session, now, _, _, _ = setup
    original = MockGPUProvider.submit

    def slow(self, request, **kwargs):
        job = original(self, request, **kwargs)
        now[0] = 701
        return job

    monkeypatch.setattr(MockGPUProvider, 'submit', slow)
    assert submit(session).status == 'queued'
    assert session.closed and session.cleanup_result.complete


@pytest.mark.parametrize('clock', [99, True, float('nan'), float('inf')])
def test_invalid_clock_no_admission(setup, clock):
    session, now, ledger, provider, _ = setup
    before = ledger.path.read_bytes()
    now[0] = clock
    with pytest.raises(ValueError):
        submit(session)
    assert provider._jobs == {} and ledger.path.read_bytes() == before


def test_persistence_failure_cleanup(setup, monkeypatch):
    session, _, ledger, provider, _ = setup

    def fail(*args):
        raise OSError('disk failure')

    monkeypatch.setattr(ledger, '_write', fail)
    with pytest.raises(OSError, match='disk failure'):
        submit(session)
    assert session.closed and session.cleanup_result.complete and provider._jobs == {}


def test_constructor_guards_and_rounding(setup):
    _, _, ledger, provider, backend = setup
    work, config = inputs()
    for p, b in [(object(), backend), (provider, object())]:
        with pytest.raises(TypeError):
            MockRenderSession(p, b, ledger, work, config, render_id='r', clock=lambda: 0)
    with pytest.raises(BudgetExceeded):
        MockRenderSession(
            provider,
            backend,
            ledger,
            work,
            config.model_copy(update={'max_gpu_minutes_per_job': Decimal(0)}),
            render_id='r',
            clock=lambda: 0,
        )
    with pytest.raises(ValueError, match='Unrepresentable'):
        MockRenderSession(
            provider, backend, ledger, work, config, render_id='r', clock=lambda: 1e30
        )
    config = config.model_copy(update={'max_gpu_minutes_per_job': Decimal('4.000001')})
    session = MockRenderSession(
        provider, backend, ledger, work, config, render_id='r', clock=lambda: 100.0
    )
    assert Decimal(session.deadline) <= Decimal('340.000060')
    assert not backend.calls
