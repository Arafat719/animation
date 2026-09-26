"""Bound one explicitly requested mock recovery child; no automatic restart loop."""

import fcntl
import math
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from animation_studio.providers.gpu_journal import MockSessionJournal
from animation_studio.providers.gpu_watchdog import REST_SCENARIOS


@dataclass(frozen=True)
class SupervisionResult:
    outcome: str
    timed_out: bool
    child_pid: int | None
    returncode: int | None


def supervise_mock_recovery(
    journal_path: Path, *, scenario: str, timeout_seconds: float
) -> SupervisionResult:
    """Recover an already-armed journal; never launch or admit a new session.

    Bounds the child including startup. Timeout kills/reaps only this child and
    reports unknown cleanup. A later explicit invocation re-reads the journal;
    no reset of attempts, deadline or authentication failure is allowed.
    """
    if scenario not in REST_SCENARIOS:
        raise ValueError('Unknown mock scenario')
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ValueError('Invalid supervision timeout')
    journal_path = Path(journal_path).resolve()
    lease = os.open(
        str(journal_path) + '.supervisor.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        journal = MockSessionJournal(journal_path)
        with journal._locked():
            record = journal._read()
        if record.outcome != 'pending':
            return SupervisionResult(record.outcome, False, None, None)
        with subprocess.Popen(
            [
                sys.executable,
                '-m',
                'animation_studio.providers.gpu_watchdog',
                str(journal_path),
                '--mock-rest-scenario',
                scenario,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        ) as child:
            try:
                child.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
                return SupervisionResult('needs_manual_cleanup', True, child.pid, child.returncode)
            if child.returncode not in (0, 2):
                return SupervisionResult('needs_manual_cleanup', False, child.pid, child.returncode)
            with journal._locked():
                result = journal._read()
            return SupervisionResult(result.outcome, False, child.pid, child.returncode)
    finally:
        os.close(lease)
