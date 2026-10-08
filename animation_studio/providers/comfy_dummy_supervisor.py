"""Bound one fixed dummy child with synthetic telemetry; never run Comfy or models."""

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Literal

from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_resource_guard import evaluate_resources
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy

_DUMMY = """
import os, signal, sys, time
mode = sys.argv[1]
if mode == 'ignore_stop':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
else:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
os.write(1, b'R')
if mode == 'normal':
    sys.exit(0)
while True:
    time.sleep(0.05)
"""


@dataclass(frozen=True)
class DummySupervisionResult:
    outcome: Literal['denied', 'exited', 'aborted', 'needs_manual_cleanup']
    reasons: tuple[str, ...]
    child_pid: int | None
    returncode: int | None
    ready: bool
    stop_requested: bool
    kill_requested: bool
    worker_status: Literal['unknown', 'exited']
    job_status: Literal['unknown'] = 'unknown'
    compute_status: Literal['unknown'] = 'unknown'
    storage_status: Literal['unknown'] = 'unknown'
    telemetry_source: Literal['synthetic'] = 'synthetic'


def _signal_owned(child: subprocess.Popen, sig: int) -> bool:
    if child.poll() is not None:
        return False
    try:
        child.send_signal(sig)
    except ProcessLookupError:
        # The owned child exited between poll and signal; next poll reaps it.
        return False
    return True


def supervise_dummy(
    *,
    policy: ComfySupervisionPolicy,
    context: ComfyExecutionContext,
    mode: Literal['normal', 'cooperate', 'ignore_stop'],
    telemetry: Literal['healthy', 'missing_at_admission', 'missing_when_ready'] = 'healthy',
) -> DummySupervisionResult:
    """Use fixed synthetic samples to exercise the guard and owned-child lifecycle.

    No arbitrary commands/PIDs or callbacks; the fixed child creates no descendants.
    Startup consumes the run window. SIGTERM is the dummy cooperative request;
    SIGKILL at cleanup deadline leaves the final reserve for bounded reaping.
    Signals/exit prove nothing about remote jobs. No Popen context manager: its
    implicit unbounded wait would violate the final deadline on failed cleanup.
    """
    if os.name != 'posix':
        raise ValueError('POSIX dummy supervision required')
    if type(mode) is not str or mode not in ('normal', 'cooperate', 'ignore_stop'):
        raise ValueError('Invalid dummy mode')
    if type(telemetry) is not str or telemetry not in (
        'healthy',
        'missing_at_admission',
        'missing_when_ready',
    ):
        raise ValueError('Invalid synthetic telemetry scenario')
    if type(policy) is not ComfySupervisionPolicy:
        raise ValueError('Expected supervision policy')
    policy = ComfySupervisionPolicy.model_validate(policy.model_dump())
    start = time.monotonic()
    worker_id = 'owned-dummy'

    def decide(now, stage, missing):
        sample = (
            None
            if missing
            else {
                'context': context,
                'worker_id': worker_id,
                'device_index': policy.device_index,
                'sampled_at': now,
                'rss_bytes': 0,
                'available_ram_bytes': policy.host_reserve_bytes + 1,
                'used_vram_bytes': 0,
            }
        )
        return evaluate_resources(
            policy=policy,
            context=context,
            worker_id=worker_id,
            stage=stage,
            start=start,
            now=now,
            sample=sample,
        )

    admission = decide(start, 'admission', telemetry == 'missing_at_admission')
    if admission.action != 'allow':
        return DummySupervisionResult(
            'denied', admission.reasons, None, None, False, False, False, 'unknown'
        )
    child = subprocess.Popen(
        [sys.executable, '-I', '-S', '-c', _DUMMY, mode],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    ready = stop = killed = False
    reasons = ()
    try:
        os.set_blocking(child.stdout.fileno(), False)
        while True:
            code = child.poll()
            if not ready:
                try:
                    ready = os.read(child.stdout.fileno(), 1) == b'R'
                except BlockingIOError:
                    pass  # No ready byte yet; deadline remains unchanged.
            if code is not None:
                return DummySupervisionResult(
                    'aborted' if reasons else 'exited',
                    reasons,
                    child.pid,
                    code,
                    ready,
                    stop,
                    killed,
                    'exited',
                )
            now = time.monotonic()
            if not reasons:
                decision = decide(now, 'running', telemetry == 'missing_when_ready' and ready)
                if decision.action == 'abort':
                    reasons = decision.reasons
                    stop = _signal_owned(child, signal.SIGTERM)
            if reasons and now >= admission.cleanup_deadline and not killed:
                killed = _signal_owned(child, signal.SIGKILL)
            if now >= admission.final_deadline:
                code = child.poll()
                return DummySupervisionResult(
                    'needs_manual_cleanup' if code is None else 'aborted',
                    reasons,
                    child.pid,
                    code,
                    ready,
                    stop,
                    killed,
                    'unknown' if code is None else 'exited',
                )
            next_boundary = admission.cleanup_deadline if reasons else admission.run_deadline
            if now >= admission.cleanup_deadline:
                next_boundary = admission.final_deadline
            time.sleep(
                max(
                    0,
                    min(
                        policy.sample_interval_seconds,
                        0.05,
                        next_boundary - time.monotonic(),
                        admission.final_deadline - time.monotonic(),
                    ),
                )
            )
    finally:
        # Also clean up on unexpected parent-side errors, preserving the exception.
        try:
            if child.poll() is None:
                if not killed:
                    _signal_owned(child, signal.SIGKILL)
                remaining = max(0, admission.final_deadline - time.monotonic())
                try:
                    child.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    pass  # Result remains unknown; never wait without a bound.
        finally:
            child.stdout.close()
