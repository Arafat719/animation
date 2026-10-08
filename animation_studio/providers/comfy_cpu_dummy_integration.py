"""CPU-only integration: fixed dummy child, real procfs RAM telemetry, RAM sampler.

Never launches Comfy, models or GPU work, and never an arbitrary command. This is
the C3 composition of the existing reader, sampler and pure CPU guard; the
synthetic dummy supervisor and the full mock resource evaluator stay unchanged.
"""

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Literal

from animation_studio.providers.comfy_cpu_guard import CpuDecision, evaluate_cpu_resources
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_ram_sampler import RamSampler
from animation_studio.providers.comfy_ram_telemetry import OwnedChildRamReader
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy

DummyMode = Literal['cooperate', 'ignore_stop', 'exit_after_ready', 'exit_before_ready']

_MODES = ('cooperate', 'ignore_stop', 'exit_after_ready', 'exit_before_ready')
_READY_BYTE = b'R'
_TICK_SECONDS = 0.02
_EXIT_AFTER_READY_SECONDS = 0.3

_CPU_DUMMY = """
import os, signal, sys, time

mode = sys.argv[1]
if mode == 'ignore_stop':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
else:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
if mode != 'exit_before_ready':
    os.write(1, b'R')
if mode == 'exit_after_ready':
    time.sleep(float(sys.argv[2]))
    sys.exit(0)
if mode == 'exit_before_ready':
    sys.exit(0)
while True:
    time.sleep(0.05)
"""


@dataclass(frozen=True)
class CpuDummyResult:
    """Explicit CPU-only outcome; VRAM, job, compute and storage stay unknown."""

    outcome: Literal['exited', 'aborted', 'needs_manual_cleanup']
    reasons: tuple[str, ...]
    admitted: bool
    observed_rss_bytes: int | None
    child_pid: int | None
    returncode: int | None
    ready: bool
    stop_requested: bool
    kill_requested: bool
    sample_sequence: int
    sampler_status: Literal['not_started', 'running', 'unknown', 'stopped', 'failed']
    worker_status: Literal['unknown', 'exited']
    decision: CpuDecision | None
    cleanup_child: subprocess.Popen | None = field(default=None, repr=False, compare=False)
    cleanup_sampler: RamSampler | None = field(default=None, repr=False, compare=False)
    telemetry_source: Literal['local_procfs'] = 'local_procfs'
    scope: Literal['local_cpu_dummy'] = 'local_cpu_dummy'
    vram_status: Literal['unknown'] = 'unknown'
    job_status: Literal['unknown'] = 'unknown'
    compute_status: Literal['unknown'] = 'unknown'
    storage_status: Literal['unknown'] = 'unknown'


@dataclass(frozen=True)
class CpuDummyCleanup:
    """Attached as cpu_dummy_cleanup to the original propagated exception.

    Keep this session until child reaping and sampler close are confirmed.
    Error codes are safe summaries; exception objects are private diagnostics.
    The deadline records the original budget, never a renewed supervision window.
    """

    child: subprocess.Popen = field(repr=False)
    sampler: RamSampler | None = field(repr=False)
    deadline: float
    worker_status: Literal['unknown', 'exited']
    sampler_status: str
    error_codes: tuple[str, ...]
    errors: tuple[BaseException, ...] = field(repr=False)
    outcome: Literal['needs_manual_cleanup', 'closed']


def _signal_owned(child: subprocess.Popen, sig: int) -> bool:
    """Signal only the owned direct child; a concurrent exit is not an error."""
    if child.poll() is not None:
        return False
    try:
        child.send_signal(sig)
    except ProcessLookupError:
        return False
    return True


def _read_ready(child: subprocess.Popen) -> bool:
    try:
        return os.read(child.stdout.fileno(), 1) == _READY_BYTE
    except BlockingIOError:
        return False


def _spawn(mode: DummyMode) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, '-I', '-S', '-c', _CPU_DUMMY, mode, str(_EXIT_AFTER_READY_SECONDS)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


def supervise_cpu_dummy(
    *, policy: ComfySupervisionPolicy, context: ComfyExecutionContext, mode: DummyMode
) -> CpuDummyResult:
    """Observe one fixed dummy child with real procfs telemetry and CPU-only decisions.

    The child writes one ready byte and then waits: it allocates nothing large and
    creates no descendants. Bootstrap shares the run window, so the first-sample
    deadline is min(run deadline, start + staleness bound). Telemetry admission is
    claimed only after the guard returns an explicit allow, and that allow is a
    CPU-only decision, never image admission. Parent deadlines never reset and
    drive the stop/kill/reap ladder, so a child cannot extend them. A child that
    outlives the final deadline, or a sampler that cannot be joined inside it,
    yields needs_manual_cleanup for the caller to keep the session and follow up.
    Exceptions retain their type/identity and carry cpu_dummy_cleanup ownership;
    callers must retain that session and complete any unconfirmed cleanup.
    """
    if not sys.platform.startswith('linux'):
        raise ValueError('Linux CPU dummy supervision required')
    if type(mode) is not str or mode not in _MODES:
        raise ValueError('Invalid CPU dummy mode')
    if type(policy) is not ComfySupervisionPolicy:
        raise ValueError('Expected supervision policy')
    if type(context) is not ComfyExecutionContext or context.mode != 'mock':
        raise ValueError('CPU dummy supervision accepts mock context only')
    policy = ComfySupervisionPolicy.model_validate(policy.model_dump())
    context = ComfyExecutionContext.model_validate(context.model_dump())

    start = time.monotonic()
    # The guard owns this deadline arithmetic; no reading exists yet at bootstrap,
    # so a placeholder identity validates deadlines before spawn; reasons are discarded.
    probe = evaluate_cpu_resources(
        policy=policy,
        context=context,
        expected_pid=1,
        expected_start_ticks=0,
        reading=None,
        start=start,
        now=time.monotonic(),
    )
    final_deadline = probe.final_deadline
    cleanup_deadline = probe.cleanup_deadline
    first_sample_deadline = min(probe.run_deadline, start + policy.stale_after_seconds)

    child = _spawn(mode)
    sampler = None
    close_snapshot = None
    decision = None
    reasons = ()
    expected_ticks = None
    observed_rss = None
    ready = stop = killed = admitted = False
    parent_error = None
    cleanup_errors = []

    def attempt(code, action):
        try:
            return action()
        except BaseException as error:  # noqa: BLE001 — retained and re-raised after cleanup.
            # Continue independent cleanup, then propagate with retained ownership.
            cleanup_errors.append((code, error))
            return None

    try:
        reader = OwnedChildRamReader(child)
        os.set_blocking(child.stdout.fileno(), False)
        while True:
            if not ready:
                ready = _read_ready(child)
            if ready and sampler is None:
                # Identity is pinned from the first identity-checked reading, which
                # is why sampling starts only after the child has signalled readiness.
                sampler = RamSampler(reader, interval_seconds=policy.sample_interval_seconds)
                sampler.start()
            snapshot = sampler.snapshot() if sampler is not None else None
            reading = snapshot.latest if snapshot is not None else None
            now = time.monotonic()

            # Parent-confirmed exit wins a race with an exited telemetry record.
            if child.poll() is not None:
                break
            if not reasons:
                bootstrap = expected_ticks is None
                if reading is not None and reading.status == 'ok' and bootstrap:
                    ticks = reading.start_ticks
                    # Invalid telemetry must abort, never become a caller identity.
                    expected_ticks = ticks if type(ticks) is int and ticks >= 0 else 0
                if (
                    reading is not None
                    or (snapshot is not None and snapshot.error_code is not None)
                    or not bootstrap
                    or now >= first_sample_deadline
                ):
                    decision = evaluate_cpu_resources(
                        policy=policy,
                        context=context,
                        expected_pid=child.pid,
                        expected_start_ticks=expected_ticks or 0,
                        reading=reading,
                        start=start,
                        now=now,
                    )
                    if bootstrap and now >= first_sample_deadline:
                        reasons = ('telemetry_missing',)
                        if now >= probe.run_deadline:
                            reasons += ('run_deadline',)
                    elif decision.action == 'allow':
                        admitted = True
                    else:
                        reasons = decision.reasons
                    if reading is not None and decision.action == 'allow':
                        observed_rss = reading.rss_bytes
                    if reasons:
                        stop = _signal_owned(child, signal.SIGTERM)

            if reasons and now >= cleanup_deadline and not killed:
                killed = _signal_owned(child, signal.SIGKILL)
            if now >= final_deadline:
                break
            time.sleep(min(_TICK_SECONDS, policy.sample_interval_seconds))
    except BaseException as error:  # noqa: BLE001 — retained and re-raised after cleanup.
        parent_error = error
    finally:
        # Each independent action runs even when another fails. Never renew budget.
        if sampler is not None:
            attempt('sampler_stop_failed', sampler.stop)
        returncode = attempt('worker_poll_failed', child.poll)
        if returncode is None:
            if not killed:
                killed = bool(
                    attempt('worker_kill_failed', lambda: _signal_owned(child, signal.SIGKILL))
                )

            def reap():
                try:
                    return child.wait(timeout=max(0.0, final_deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    return None  # Unknown retained below, not successful cleanup.

            attempt('worker_reap_failed', reap)
        if sampler is not None:
            close_snapshot = attempt(
                'sampler_close_failed', lambda: sampler.close(deadline=final_deadline)
            )
        attempt('stdout_close_failed', child.stdout.close)
        returncode = attempt('worker_poll_failed', child.poll)

    sampler_status = (
        close_snapshot.status
        if close_snapshot is not None
        else ('unknown' if sampler is not None else 'not_started')
    )
    sequence = close_snapshot.sequence if close_snapshot is not None else 0
    if parent_error is not None or cleanup_errors:
        error = parent_error if parent_error is not None else cleanup_errors[0][1]
        error.cpu_dummy_cleanup = CpuDummyCleanup(
            child=child,
            sampler=sampler,
            deadline=final_deadline,
            worker_status='unknown' if returncode is None else 'exited',
            sampler_status=sampler_status,
            error_codes=tuple(code for code, _ in cleanup_errors),
            errors=tuple(failure for _, failure in cleanup_errors),
            outcome=(
                'needs_manual_cleanup'
                if returncode is None or sampler_status == 'unknown' or cleanup_errors
                else 'closed'
            ),
        )
        raise error.with_traceback(error.__traceback__)

    worker_status = 'unknown' if returncode is None else 'exited'
    if returncode is None or sampler_status == 'unknown':
        outcome = 'needs_manual_cleanup'
    elif reasons:
        outcome = 'aborted'
    else:
        outcome = 'exited'
    return CpuDummyResult(
        outcome=outcome,
        reasons=reasons,
        admitted=admitted,
        observed_rss_bytes=observed_rss,
        child_pid=child.pid,
        returncode=returncode,
        ready=ready,
        stop_requested=stop,
        kill_requested=killed,
        sample_sequence=sequence,
        sampler_status=sampler_status,
        worker_status=worker_status,
        decision=decision,
        cleanup_child=child if returncode is None else None,
        cleanup_sampler=sampler if sampler_status == 'unknown' else None,
    )
