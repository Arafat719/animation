import os

import pytest

from animation_studio.providers.gpu_journal import MockSessionJournal, SessionRecord
from animation_studio.providers.gpu_supervisor import supervise_mock_recovery


def armed(tmp_path):
    journal = MockSessionJournal(tmp_path / 'session.json')
    journal.arm(
        SessionRecord(session_id='fixture', pod_id='owned', created_at_utc=1.0, deadline_at_utc=2.0)
    )
    return journal


def test_hung_child_reaped_and_attempts_bound_explicit_restarts(tmp_path):
    journal = armed(tmp_path)
    for attempt in range(1, 4):
        result = supervise_mock_recovery(journal.path, scenario='hang', timeout_seconds=1.0)
        assert result.timed_out and result.outcome == 'needs_manual_cleanup'
        assert result.returncode == -9
        with pytest.raises(ChildProcessError):
            os.waitpid(result.child_pid, os.WNOHANG)
        record = journal._read()
        assert record.attempt_count == attempt and record.cleanup_requested
        assert record.last_compute == 'unknown' and record.deadline_at_utc == 2.0
    # Durable cap prevents even spawning another hung child.
    final = supervise_mock_recovery(journal.path, scenario='hang', timeout_seconds=1.0)
    assert final.child_pid is None and final.outcome == 'needs_manual_cleanup'


def test_later_explicit_observation_can_resolve_unknown_compute(tmp_path):
    journal = armed(tmp_path)
    first = supervise_mock_recovery(journal.path, scenario='hang', timeout_seconds=1.0)
    assert first.timed_out
    second = supervise_mock_recovery(journal.path, scenario='absent', timeout_seconds=5.0)
    assert not second.timed_out and second.outcome == 'needs_manual_cleanup'
    record = journal._read()
    assert record.last_compute == 'absent' and record.last_storage == 'unknown'
    assert record.attempt_count == 2


@pytest.mark.parametrize('scenario', ['success', 'unauthorized'])
def test_normal_exit_and_auth_terminal_no_restart(tmp_path, scenario):
    journal = armed(tmp_path)
    result = supervise_mock_recovery(journal.path, scenario=scenario, timeout_seconds=5.0)
    assert not result.timed_out and result.returncode == 2
    assert journal._read().attempt_count == 1
    assert (
        supervise_mock_recovery(journal.path, scenario='hang', timeout_seconds=1.0).child_pid
        is None
    )


@pytest.mark.parametrize('timeout', [True, 0, -1, float('inf'), float('nan')])
def test_invalid_timeout_never_changes_journal(tmp_path, timeout):
    journal = armed(tmp_path)
    with pytest.raises(ValueError):
        supervise_mock_recovery(journal.path, scenario='success', timeout_seconds=timeout)
    assert journal._read().attempt_count == 0
