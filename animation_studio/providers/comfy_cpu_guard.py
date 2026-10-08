"""Pure CPU-only decisions for local dummy work, never full image admission."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_ram_telemetry import LocalRamReading
from animation_studio.providers.comfy_resource_guard import _time
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy

_FAILURES = {
    'unavailable': 'telemetry_unavailable',
    'invalid': 'telemetry_invalid',
    'identity_mismatch': 'telemetry_identity_mismatch',
    'exited': 'worker_exit_unconfirmed',
}


@dataclass(frozen=True)
class CpuDecision:
    action: Literal['allow', 'abort']
    reasons: tuple[str, ...]
    run_deadline: float
    cleanup_deadline: float
    final_deadline: float
    remaining_seconds: float
    scope: Literal['local_cpu_dummy'] = 'local_cpu_dummy'
    vram_status: Literal['unknown'] = 'unknown'


def _integer(value, minimum):
    return type(value) is int and value >= minimum


def _validate_reading(reading, pid, ticks, start, now):
    if type(reading) is not LocalRamReading:
        raise ValueError('Expected local reading')
    if (
        type(reading.status) is not str
        or reading.status not in ('ok', *_FAILURES)
        or not _integer(reading.pid, 1)
        or reading.pid != pid
        or type(reading.source) is not str
        or reading.source != 'local_procfs'
        or type(reading.coverage) is not str
        or reading.coverage != 'direct_child'
        or reading.vram_bytes is not None
        or not start <= _time(reading.sampled_at) <= now
    ):
        raise ValueError('Invalid reading identity/provenance')
    if reading.status == 'ok':
        if (
            not _integer(reading.start_ticks, 0)
            or reading.start_ticks != ticks
            or not _integer(reading.rss_bytes, 0)
            or not _integer(reading.available_ram_bytes, 0)
        ):
            raise ValueError('Invalid memory reading')
    elif any(
        value is not None
        for value in (reading.start_ticks, reading.rss_bytes, reading.available_ram_bytes)
    ):
        raise ValueError('Failure must retain unknown values')


def evaluate_cpu_resources(
    *,
    policy: ComfySupervisionPolicy,
    context: ComfyExecutionContext,
    expected_pid: int,
    expected_start_ticks: int,
    reading: LocalRamReading | None,
    start: float,
    now: float,
) -> CpuDecision:
    """Validate caller-pinned identity and explicit times; performs no I/O.

    Ownership and parent-confirmed exit remain the caller's responsibility.
    Malformed arguments raise ValueError; malformed telemetry produces abort.
    """
    if type(policy) is not ComfySupervisionPolicy or type(context) is not ComfyExecutionContext:
        raise ValueError('Expected policy and mock execution context')
    policy = ComfySupervisionPolicy.model_validate(policy.model_dump())
    context = ComfyExecutionContext.model_validate(context.model_dump())
    if context.mode != 'mock':
        raise ValueError('CPU guard is for mock execution only')
    if not _integer(expected_pid, 1) or not _integer(expected_start_ticks, 0):
        raise ValueError('Invalid expected child identity')
    start, now = _time(start), _time(now)
    final = start + policy.overall_timeout_seconds
    cleanup = final - policy.reap_allowance_seconds
    run = cleanup - policy.cleanup_reserve_seconds
    if not isfinite(final) or not start < run < cleanup < final or now < start:
        raise ValueError('Invalid or unrepresentable deadlines')
    reasons = []
    if reading is None:
        reasons.append('telemetry_missing')
    else:
        try:
            _validate_reading(reading, expected_pid, expected_start_ticks, start, now)
        except ValueError:
            reasons.append('telemetry_invalid')
        else:
            if reading.status != 'ok':
                reasons.append(_FAILURES[reading.status])
            else:
                if now - reading.sampled_at > policy.stale_after_seconds:
                    reasons.append('telemetry_stale')
                if reading.rss_bytes >= policy.ram_limit_bytes:
                    reasons.append('ram_limit')
                if reading.available_ram_bytes <= policy.host_reserve_bytes:
                    reasons.append('host_reserve')
    if now >= run:
        reasons.append('run_deadline')
    return CpuDecision(
        'abort' if reasons else 'allow', tuple(reasons), run, cleanup, final, max(0.0, run - now)
    )
