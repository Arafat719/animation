"""Linux fixed-fixture session child supervision; never launch a live worker."""

import json
import os
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, field_validator

from animation_studio.providers.comfy_cpu_guard import evaluate_cpu_resources
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_journal import _fingerprint
from animation_studio.providers.comfy_ram_sampler import RamSampler
from animation_studio.providers.comfy_ram_telemetry import OwnedChildRamReader
from animation_studio.providers.comfy_resource_guard import evaluate_resources
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy
from animation_studio.providers.comfy_workflow import validate_image_workflow
from animation_studio.providers.image import ImageErrorCode, ImageProviderError

MAX_IPC_BYTES = 65536
Scenario = Literal[
    'normal',
    'startup_hang',
    'inventory_hang',
    'history_hang',
    'cooperate',
    'intent_hang',
    'cancel_hang',
]


class FixtureLaunch(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)
    root: str
    context: ComfyExecutionContext
    graph: dict[str, dict]
    policy: ComfySupervisionPolicy
    start: float
    session_id: str
    scenario: Scenario

    @field_validator('session_id')
    @classmethod
    def canonical_session(cls, value):
        if str(UUID(value)) != value:
            raise ValueError('Expected canonical session identity')
        return value


class FixtureTerminal(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)
    session_id: str
    job_id: str
    outcome: Literal['fixture_verified', 'failed']
    code: ImageErrorCode | None


def decode_message(data):
    if not data or len(data) > MAX_IPC_BYTES:
        raise ValueError('Invalid supervision message size')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate supervision field')
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError('Nonfinite supervision value')

    return json.loads(data, object_pairs_hook=unique, parse_constant=reject_constant)


@dataclass(frozen=True)
class SessionChildCleanup:
    child: subprocess.Popen = field(repr=False, compare=False)
    final_deadline: float
    error_codes: tuple[str, ...]
    errors: tuple[BaseException, ...] = field(repr=False, compare=False)
    sampler: RamSampler | None = field(default=None, repr=False, compare=False)
    sampler_status: str = 'not_started'


@dataclass(frozen=True)
class SessionSupervisionResult:
    outcome: Literal['fixture_verified', 'failed', 'aborted', 'needs_manual_cleanup']
    reason: str | None
    session_id: str
    child_pid: int
    returncode: int | None
    stop_requested: bool
    kill_requested: bool
    terminal: FixtureTerminal | None
    cleanup: SessionChildCleanup | None = field(default=None, repr=False, compare=False)
    is_mock: bool = True
    telemetry_source: str = 'synthetic'
    job_status: str = 'unknown'
    compute_status: str = 'unknown'
    storage_status: str = 'unknown'
    ram_source: str = 'local_procfs'
    ram_coverage: str = 'direct_child'
    # Last guard-allowed sample, not a peak or the rejected sample's measurement.
    rss_bytes: int | None = None
    available_ram_bytes: int | None = None
    sampler_status: str = 'not_started'
    sample_sequence: int = 0
    ram_reasons: tuple[str, ...] = ()
    ram_admitted: bool = False
    vram_status: str = 'unknown'


def _spawn():
    return subprocess.Popen(
        [sys.executable, '-m', 'animation_studio.providers.comfy_session_child'],
        cwd=Path(__file__).resolve().parents[2],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


def supervise_offline_session(
    *,
    root: Path,
    context: ComfyExecutionContext,
    graph: dict,
    policy: ComfySupervisionPolicy,
    scenario: Scenario = 'normal',
    cancel: Event | None = None,
) -> SessionSupervisionResult:
    """Own one fixed mock child; no HTTP, journal mutation or automatic recovery here.

    Caller retains cleanup handles on both returned unknown outcomes and exceptions.
    Same-host monotonic deadlines include startup; OS scheduling/spawn are not hard bounds.
    Local RAM admission gates the startup payload, not interpreter allocation. Child
    inference telemetry remains synthetic and does not establish target VRAM safety.
    """
    if not sys.platform.startswith('linux'):
        raise ValueError('Linux same-host supervision required')
    root = Path(root).absolute()
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Expected owned private root')
    validate_image_workflow(graph)
    context = ComfyExecutionContext.model_validate(context.model_dump())
    policy = ComfySupervisionPolicy.model_validate(policy.model_dump())
    if context.mode != 'mock' or context.graph_sha256 != _fingerprint(graph):
        raise ValueError('Expected matching mock context')
    start = time.monotonic()
    decision = evaluate_resources(
        policy=policy,
        context=context,
        worker_id='fixture-child',
        stage='admission',
        start=start,
        now=start,
        sample=None,
    )
    launch = FixtureLaunch(
        root=str(root),
        context=context,
        graph=graph,
        policy=policy,
        start=start,
        session_id=str(uuid4()),
        scenario=scenario,
    )
    payload = launch.model_dump_json().encode() + b'\n'
    if len(payload) > MAX_IPC_BYTES:
        raise ValueError('Supervision startup message too large')
    if cancel is not None and cancel.is_set():
        raise ImageProviderError('cancelled', 'Cancelled before child launch')
    child = _spawn()
    terminal = None
    reason = None
    stop = killed = eof = False
    incoming = bytearray()
    outgoing = payload
    payload_sent = 0
    admitted = False
    ticks = None
    sampler = close_snapshot = snapshot = None
    measured = None
    ram_reasons = ()
    first_sample_deadline = min(decision.run_deadline, start + policy.stale_after_seconds)
    primary = None
    errors = []
    code = None

    def attempt(label, action):
        try:
            return action()
        except BaseException as error:  # noqa: BLE001 — independent cleanup, preserve ownership.
            errors.append((label, error))
            return None

    try:
        os.set_blocking(child.stdin.fileno(), False)
        os.set_blocking(child.stdout.fileno(), False)
        child.poll()  # Observe immediate launch failure before starting telemetry.
        sampler = RamSampler(
            OwnedChildRamReader(child), interval_seconds=policy.sample_interval_seconds
        )
        sampler.start()
        while True:
            now = time.monotonic()
            code = child.poll()
            if reason is None and (
                now >= decision.run_deadline or (cancel is not None and cancel.is_set())
            ):
                reason = 'timeout' if now >= decision.run_deadline else 'cancelled'
            if code is None and reason is None:
                snapshot = sampler.snapshot()
                reading = snapshot.latest
                # Reading may have observed/reaped exit while taking the snapshot.
                code = child.poll()
                if code is None:
                    if snapshot.error_code is not None or snapshot.status != 'running':
                        ram_reasons = ('sampler_failed',)
                    elif not admitted and now >= first_sample_deadline:
                        ram_reasons = ('telemetry_missing',)
                    elif reading is not None or admitted:
                        candidate_ticks = ticks
                        if candidate_ticks is None:
                            candidate_ticks = (
                                reading.start_ticks
                                if reading is not None
                                and type(reading.start_ticks) is int
                                and reading.start_ticks >= 0
                                else 0
                            )
                        guard = evaluate_cpu_resources(
                            policy=policy,
                            context=context,
                            expected_pid=child.pid,
                            expected_start_ticks=candidate_ticks,
                            reading=reading,
                            start=start,
                            now=time.monotonic(),
                        )
                        if guard.action == 'allow':
                            ticks = candidate_ticks
                            admitted = True
                            measured = reading
                        else:
                            ram_reasons = guard.reasons
                    if ram_reasons:
                        reason = ram_reasons[0]
            if reason is not None and not stop:
                if payload_sent < len(payload):
                    outgoing = b''
                    child.stdin.close()  # Incomplete startup never becomes executable.
                else:
                    outgoing += b'S'
                stop = True
            if outgoing and code is None and admitted:
                try:
                    count = os.write(child.stdin.fileno(), outgoing)
                    outgoing = outgoing[count:]
                    payload_sent = min(len(payload), payload_sent + count)
                except BlockingIOError:
                    pass
                except BrokenPipeError:
                    outgoing = b''
                    reason = reason or 'control_closed'
            if not eof:
                try:
                    chunk = os.read(child.stdout.fileno(), MAX_IPC_BYTES + 1)
                except BlockingIOError:
                    chunk = None
                if chunk == b'':
                    eof = True
                elif chunk:
                    incoming.extend(chunk)
                    if len(incoming) > MAX_IPC_BYTES:
                        reason = reason or 'invalid_terminal'
                        incoming.clear()
                        eof = True
                    elif b'\n' in incoming:
                        try:
                            if (
                                terminal is not None
                                or incoming.count(b'\n') != 1
                                or not incoming.endswith(b'\n')
                            ):
                                raise ValueError
                            parsed = FixtureTerminal.model_validate(decode_message(bytes(incoming)))
                            if (
                                parsed.session_id != launch.session_id
                                or parsed.job_id != context.job_id
                                or (parsed.outcome == 'fixture_verified') != (parsed.code is None)
                            ):
                                raise ValueError
                            terminal = parsed
                            if time.monotonic() >= decision.run_deadline:
                                reason = reason or 'timeout'
                        except (ValueError, TypeError, RecursionError):
                            reason = reason or 'invalid_terminal'
                        incoming.clear()
            if code is not None and eof:
                if incoming or terminal is None:
                    reason = reason or 'invalid_terminal'
                break
            if now >= decision.cleanup_deadline and code is None and not killed:
                child.send_signal(signal.SIGKILL)
                killed = True
            if now >= decision.final_deadline:
                break
            time.sleep(max(0, min(0.01, decision.final_deadline - time.monotonic())))
    except BaseException as error:  # noqa: BLE001 — rethrow original after bounded cleanup.
        primary = error
    finally:
        if sampler is not None:
            attempt('sampler_stop_failed', sampler.stop)
        code = attempt('poll_failed', child.poll)
        if code is None:
            if not killed:

                def kill():
                    child.send_signal(signal.SIGKILL)
                    return True

                killed = bool(attempt('kill_failed', kill))

            def reap():
                try:
                    return child.wait(timeout=max(0, decision.final_deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    return None  # Unknown child stays caller-owned; no renewed allowance.

            attempt('reap_failed', reap)
        if sampler is not None:
            close_snapshot = attempt(
                'sampler_close_failed', lambda: sampler.close(deadline=decision.final_deadline)
            )
        attempt('stdin_close_failed', child.stdin.close)
        attempt('stdout_close_failed', child.stdout.close)
        code = attempt('poll_failed', child.poll)
    sampler_status = (
        close_snapshot.status
        if close_snapshot is not None
        else ('unknown' if sampler is not None else 'not_started')
    )
    cleanup = SessionChildCleanup(
        child,
        decision.final_deadline,
        tuple(x[0] for x in errors),
        tuple(x[1] for x in errors),
        sampler,
        sampler_status,
    )
    if primary is not None or errors:
        error = primary if primary is not None else errors[0][1]
        error.session_child_cleanup = cleanup
        error.session_child_terminal = terminal
        raise error.with_traceback(error.__traceback__)
    outcome = (
        'needs_manual_cleanup'
        if code is None or sampler_status == 'unknown'
        else 'aborted'
        if reason
        else 'fixture_verified'
        if code == 0 and terminal and terminal.outcome == 'fixture_verified'
        else 'failed'
    )
    return SessionSupervisionResult(
        outcome,
        reason or (terminal.code if terminal else None),
        launch.session_id,
        child.pid,
        code,
        stop,
        killed,
        terminal,
        cleanup if code is None or sampler_status == 'unknown' else None,
        rss_bytes=measured.rss_bytes if measured is not None else None,
        available_ram_bytes=measured.available_ram_bytes if measured is not None else None,
        sampler_status=sampler_status,
        sample_sequence=close_snapshot.sequence if close_snapshot is not None else 0,
        ram_reasons=ram_reasons,
        ram_admitted=admitted,
    )
