import pytest

from animation_studio.providers.gpu_journal import MockSessionJournal
from tests.test_gpu_watchdog import launch, paths, ready, stop


@pytest.mark.parametrize(
    'scenario,attempts,compute,codes',
    [
        ('success', 1, 'absent', ()),
        ('unauthorized', 1, 'unknown', ('unauthorized',)),
        ('unavailable', 3, 'unknown', ('unavailable',) * 4),
        ('ambiguous-delete', 1, 'absent', ('timeout',)),
        ('absent', 1, 'absent', ()),
    ],
)
def test_rest_subprocess_recovery_and_terminal_restart(
    tmp_path, scenario, attempts, compute, codes
):
    journal, fixture = paths(tmp_path)
    process = launch(journal, fixture, scenario)
    try:
        ready(process)
        out, err = process.communicate(b'finished', timeout=8)
        assert process.returncode == 2 and not err
        assert out == b'needs_manual_cleanup\n'
        result = MockSessionJournal(journal)._read()
        assert result.attempt_count == attempts and result.last_compute == compute
        assert result.last_storage == 'unknown' and result.last_provider_codes == codes
        before = journal.read_bytes()
        # Even a different scenario cannot rearm a terminal journal after restart.
        restarted = launch(journal, scenario='success')
        try:
            restarted.communicate(timeout=5)
            assert restarted.returncode == 2 and journal.read_bytes() == before
        finally:
            stop(restarted)
    finally:
        stop(process)


def test_rest_runner_crash_before_cleanup_recovers_on_restart(tmp_path):
    journal, fixture = paths(tmp_path)
    process = launch(journal, fixture, 'success')
    try:
        ready(process)
        process.kill()
        process.wait(timeout=5)
        restarted = launch(journal, scenario='absent')
        try:
            restarted.communicate(timeout=5)
            result = MockSessionJournal(journal)._read()
            assert restarted.returncode == 2
            assert result.last_compute == 'absent' and result.attempt_count == 1
        finally:
            stop(restarted)
    finally:
        stop(process)
