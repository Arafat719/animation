"""Separate-process fixture watchdog. Never constructs a live provider."""

import argparse
import fcntl
import os
import select
import sys
import time
from contextlib import ExitStack
from pathlib import Path

import httpx
from pydantic import SecretStr

from animation_studio.providers.gpu_journal import MockSessionJournal, SessionRecord
from animation_studio.providers.gpu_lifecycle import MockLifecycle, MockRESTLifecycle
from animation_studio.providers.runpod_lifecycle import RunPodLifecycle

REST_SCENARIOS = ('success', 'unauthorized', 'unavailable', 'ambiguous-delete', 'absent', 'hang')


def mock_rest_adapter(pod_id: str, scenario: str) -> RunPodLifecycle:
    """Built-in process-local fixtures; no endpoint, token or live transport input."""
    if scenario not in REST_SCENARIOS:
        raise ValueError('Unknown mock scenario')
    absent = scenario == 'absent'

    def respond(request):
        nonlocal absent
        base = f'https://rest.runpod.io/v1/pods/{pod_id}'
        if scenario == 'hang':
            # Intent is already durable before this deliberately unbounded fixture.
            while True:
                time.sleep(1)
        if scenario == 'unauthorized':
            return httpx.Response(401)
        if scenario == 'unavailable':
            return httpx.Response(503)
        if request.method == 'GET' and str(request.url) == base:
            return (
                httpx.Response(404)
                if absent
                else httpx.Response(200, json={'id': pod_id, 'desiredStatus': 'RUNNING'})
            )
        if request.method == 'POST' and str(request.url) == base + '/stop':
            return httpx.Response(200)
        if request.method == 'DELETE' and str(request.url) == base:
            absent = True
            if scenario == 'ambiguous-delete':
                raise httpx.ReadTimeout('Simulated lost acknowledgement', request=request)
            return httpx.Response(204)
        raise ValueError('Unexpected mock request')

    return RunPodLifecycle(
        pod_id=pod_id,
        api_key=SecretStr('mock-fixture-only'),
        transport=httpx.MockTransport(respond),
    )


def run(
    journal_path: Path, arm_record: Path | None = None, mock_rest_scenario: str | None = None
) -> int:
    """stdin byte/EOF requests cleanup; stdout READY follows durable arming.

    Parent must exclusively own the pipe writer. An inherited writer delays EOF.
    Existing journals recover immediately; their deadlines are never renewed.
    This fixture uses unknown storage, so successful compute cleanup returns 2.
    """
    if mock_rest_scenario is not None and mock_rest_scenario not in REST_SCENARIOS:
        raise ValueError('Unknown mock scenario')
    lease = os.open(
        str(journal_path) + '.runner.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        journal = MockSessionJournal(journal_path)
        if arm_record is not None:
            record = SessionRecord.model_validate_json(arm_record.read_bytes())
            journal.arm(record)
            remaining = max(0.0, record.deadline_at_utc - time.time())
            deadline = time.monotonic() + remaining
            print('READY', flush=True)
            # select wakes on parent death (EOF), explicit signal or deadline.
            while True:
                remaining = max(0.0, deadline - time.monotonic())
                readable, _, _ = select.select([sys.stdin.fileno()], [], [], min(remaining, 1.0))
                if readable or time.monotonic() >= deadline:
                    break
        else:
            record = journal._read()
        with ExitStack() as resources:
            if mock_rest_scenario is None:
                backend = MockLifecycle(record.pod_id, storage='unknown')
            else:
                adapter = mock_rest_adapter(record.pod_id, mock_rest_scenario)
                resources.callback(adapter.close)
                backend = MockRESTLifecycle(adapter)
            while True:
                result = journal.recover(backend)
                if result.outcome != 'pending':
                    print(result.outcome, flush=True)
                    return 0 if result.outcome == 'complete' else 2
                time.sleep(result.attempt_count)  # delays 1s, 2s; journal caps at 3
    finally:
        os.close(lease)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    parser.add_argument('--arm-record', type=Path)
    parser.add_argument('--mock-rest-scenario', choices=REST_SCENARIOS)
    args = parser.parse_args()
    try:
        return run(args.journal, args.arm_record, args.mock_rest_scenario)
    except (OSError, ValueError):
        # Do not echo malformed record contents or filesystem details.
        print('watchdog_failed', file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
