import httpx
import pytest
from pydantic import SecretStr

from animation_studio.providers.gpu_lifecycle import MockRESTLifecycle, MockSessionController
from animation_studio.providers.runpod_lifecycle import RunPodLifecycle


def setup(responses):
    calls = []
    replies = iter(responses)

    def handle(request):
        calls.append(request.method)
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return reply

    adapter = RunPodLifecycle(
        pod_id='owned', api_key=SecretStr('fixture'), transport=httpx.MockTransport(handle)
    )
    backend = MockRESTLifecycle(adapter)
    controller = MockSessionController(backend, started_at=0, duration_seconds=10)
    return adapter, backend, controller, calls


def present(status='RUNNING'):
    return httpx.Response(200, json={'id': 'owned', 'desiredStatus': status})


def test_deadline_cleanup_and_reconcile_without_repeat_delete():
    adapter, _, controller, calls = setup(
        [
            present(),
            httpx.Response(200),
            httpx.Response(204),
            httpx.Response(404),
            httpx.Response(404),
        ]
    )
    try:
        assert controller.tick(9) is None and calls == []
        result = controller.tick(10)
        assert result.state.compute == 'absent'
        assert result.state.storage == 'unknown'
        assert not result.complete and not result.errors and controller.closed
        assert not controller.tick(11).complete
        assert calls == ['GET', 'POST', 'DELETE', 'GET', 'GET']
    finally:
        adapter.close()


@pytest.mark.parametrize('status', ['EXITED', 'TERMINATED', 'FUTURE'])
def test_desired_state_and_ack_do_not_prove_cleanup(status):
    adapter, _, controller, calls = setup(
        [
            present(status),
            httpx.Response(200),
            httpx.Response(204),
            present(status),
        ]
    )
    try:
        result = controller.tick(1, finished=True)
        assert result.state.compute == 'unknown' and not result.complete
        assert calls == ['GET', 'POST', 'DELETE', 'GET']
    finally:
        adapter.close()


def test_ambiguous_delete_recovery_inspects_before_any_new_mutation():
    adapter, _, controller, calls = setup(
        [
            present(),
            httpx.ReadTimeout('private'),
            httpx.ReadTimeout('private'),
            httpx.Response(503),
            httpx.Response(404),
        ]
    )
    try:
        first = controller.tick(1, failed=True)
        assert first.errors == ('stop_failed', 'terminate_failed', 'inspect_failed')
        assert first.state.compute == 'unknown' and controller.closed
        second = controller.tick(2)
        assert second.state.compute == 'absent' and not second.complete
        assert calls == ['GET', 'POST', 'DELETE', 'GET', 'GET']
    finally:
        adapter.close()


def test_failed_delete_can_be_reconciled_on_later_tick():
    adapter, _, controller, calls = setup(
        [
            present(),
            httpx.Response(200),
            httpx.Response(503),
            present(),
            present(),
            httpx.Response(200),
            httpx.Response(204),
            httpx.Response(404),
        ]
    )
    try:
        assert controller.tick(10).errors == ('terminate_failed',)
        result = controller.tick(11)
        assert result.state.compute == 'absent' and not result.complete
        assert calls == ['GET', 'POST', 'DELETE', 'GET'] * 2
    finally:
        adapter.close()


@pytest.mark.parametrize('operation', ['inspect', 'stop', 'terminate'])
def test_wrong_pod_rejected_without_http(operation):
    adapter, backend, _, calls = setup([])
    try:
        with pytest.raises(ValueError, match='mismatch'):
            getattr(backend, operation)('other')
        assert not calls
    finally:
        adapter.close()


def test_unverified_adapter_rejected():
    with pytest.raises(TypeError):
        MockRESTLifecycle(object())
