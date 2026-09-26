import json

import httpx
import pytest

from animation_studio.providers.gpu_journal import MockSessionJournal, SessionRecord
from tests.test_gpu_rest_cleanup import present, setup


@pytest.mark.parametrize('status', [401, 403])
@pytest.mark.parametrize('position', range(4))
def test_auth_denial_stops_current_cycle_and_restart_retries(tmp_path, status, position):
    replies = [present(), httpx.Response(200), httpx.Response(204), httpx.Response(404)]
    replies[position] = httpx.Response(status, text='private-secret')
    adapter, backend, _, calls = setup(replies)
    store = MockSessionJournal(tmp_path / 'session.json')
    store.arm(
        SessionRecord(session_id='fixture', pod_id='owned', created_at_utc=1.0, deadline_at_utc=2.0)
    )
    try:
        result = store.recover(backend)
        assert result.last_provider_codes == ('unauthorized',)
        assert result.outcome == 'needs_manual_cleanup' and result.attempt_count == 1
        assert len(calls) == position + 1
        assert MockSessionJournal(store.path).recover(backend) == result
        assert len(calls) == position + 1
        assert 'private-secret' not in store.path.read_text()
    finally:
        adapter.close()


def test_direct_controller_does_not_retry_auth_denial():
    adapter, _, controller, calls = setup([httpx.Response(401)])
    try:
        first = controller.cleanup()
        assert first.provider_codes == ('unauthorized',)
        assert controller.tick(11) == first and calls == ['GET']
    finally:
        adapter.close()


def test_transient_error_code_preserved_and_recovery_allowed(tmp_path):
    adapter, backend, _, calls = setup(
        [
            present(),
            httpx.ReadTimeout('private-secret'),
            httpx.Response(503),
            present(),
            httpx.Response(404),
        ]
    )
    store = MockSessionJournal(tmp_path / 'session.json')
    store.arm(
        SessionRecord(session_id='fixture', pod_id='owned', created_at_utc=1.0, deadline_at_utc=2.0)
    )
    try:
        first = store.recover(backend)
        assert first.last_provider_codes == ('timeout', 'unavailable')
        assert first.outcome == 'pending'
        assert store.recover(backend).last_compute == 'absent'
        assert calls == ['GET', 'POST', 'DELETE', 'GET', 'GET']
    finally:
        adapter.close()


def test_old_v1_record_without_provider_codes_still_recovers(tmp_path):
    store = MockSessionJournal(tmp_path / 'session.json')
    record = SessionRecord(
        session_id='fixture', pod_id='owned', created_at_utc=1.0, deadline_at_utc=2.0
    )
    data = record.model_dump(mode='json')
    del data['last_provider_codes']
    store.path.write_text(json.dumps(data))
    adapter, backend, _, _ = setup([httpx.Response(404)])
    try:
        assert store._read().last_provider_codes == ()
        assert store.recover(backend).last_compute == 'absent'
    finally:
        adapter.close()
