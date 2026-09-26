import pytest

from animation_studio.providers.gpu_lifecycle import MockLifecycle, MockSessionController


def session(storage='none'):
    backend = MockLifecycle('owned-pod', storage=storage)
    return backend, MockSessionController(backend, started_at=100, duration_seconds=15)


def test_exact_deadline_and_repeated_cleanup():
    backend, controller = session()
    assert controller.tick(114.999) is None and not backend.calls
    result = controller.tick(115)
    assert result.complete and controller.closed
    assert backend.calls == ['inspect', 'stop', 'terminate', 'inspect']
    assert controller.tick(116).complete
    assert backend.calls[-1] == 'inspect' and backend.calls.count('terminate') == 1


@pytest.mark.parametrize('reason', ['finished', 'failed'])
def test_early_exit_cleanup(reason):
    _, controller = session()
    assert controller.tick(101, **{reason: True}).complete


@pytest.mark.parametrize('storage', ['retained', 'unknown'])
def test_compute_absence_does_not_clear_storage(storage):
    _, controller = session(storage)
    result = controller.tick(115)
    assert result.state.compute == 'absent' and result.state.storage == storage
    assert not result.complete


def test_stop_failure_uses_termination_fallback():
    backend, controller = session()
    backend.failures.add('stop')
    result = controller.tick(115)
    assert result.complete and result.errors == ('stop_failed',)


def test_failed_termination_reconciles_on_next_tick():
    backend, controller = session()
    backend.failures.add('terminate')
    result = controller.tick(115)
    assert not result.complete and controller.closed
    assert result.state.compute == 'stopped'
    backend.failures.clear()
    assert controller.tick(116).complete
    assert backend.calls.count('stop') == 1


def test_inspection_failure_never_claims_success():
    backend, controller = session()
    backend.failures.add('inspect')
    result = controller.tick(115)
    assert result.state.compute == 'unknown' and not result.complete
    assert 'terminate' in backend.calls


def test_wrong_resource_untouched():
    backend, _ = session()
    with pytest.raises(ValueError):
        backend.terminate('someone-else')
    assert backend.state.compute == 'running' and not backend.calls


@pytest.mark.parametrize('now', [99, True, float('nan'), float('inf'), '115'])
def test_invalid_clock(now):
    backend, controller = session()
    with pytest.raises(ValueError):
        controller.tick(now)
    assert not backend.calls


@pytest.mark.parametrize('duration', [0, -1, True, float('inf'), float('nan')])
def test_invalid_window(duration):
    with pytest.raises(ValueError):
        MockSessionController(MockLifecycle('pod'), started_at=0, duration_seconds=duration)


def test_live_backend_rejected():
    with pytest.raises(TypeError):
        MockSessionController(object(), started_at=0, duration_seconds=15)
