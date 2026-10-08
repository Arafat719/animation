"""Pure mock resource decisions, not measurement, enforcement or stop proof."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy


def _time(value: float) -> float:
    if type(value) not in (int, float):
        raise ValueError('Expected finite nonnegative time')
    try:
        result = float(value)
    except OverflowError:
        raise ValueError('Expected finite nonnegative time') from None
    if not isfinite(result) or result < 0:
        raise ValueError('Expected finite nonnegative time')
    return result


class ComfyResourceSample(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)
    context: ComfyExecutionContext
    worker_id: str = Field(min_length=1, max_length=128, pattern=r'^[a-zA-Z0-9_-]+$')
    device_index: int = Field(ge=0)
    sampled_at: float
    rss_bytes: int = Field(ge=0)
    available_ram_bytes: int = Field(ge=0)
    used_vram_bytes: int = Field(ge=0)

    @field_validator('sampled_at', mode='before')
    @classmethod
    def valid_time(cls, value):
        return _time(value)


@dataclass(frozen=True)
class ResourceDecision:
    action: Literal['allow', 'deny', 'abort']
    reasons: tuple[str, ...]
    run_deadline: float
    cleanup_deadline: float
    final_deadline: float
    remaining_seconds: float


def evaluate_resources(
    *,
    policy: ComfySupervisionPolicy,
    context: ComfyExecutionContext,
    worker_id: str,
    stage: Literal['admission', 'running'],
    start: float,
    now: float,
    sample: ComfyResourceSample | dict | None,
) -> ResourceDecision:
    """Evaluate caller-supplied mock telemetry in a single monotonic clock domain.

    Invalid arguments raise ValueError; untrusted/missing samples deny or abort.
    Callers own clock continuity, telemetry trust and all resulting actions.
    """
    if type(policy) is not ComfySupervisionPolicy or type(context) is not ComfyExecutionContext:
        raise ValueError('Expected supervision policy and context')
    policy = ComfySupervisionPolicy.model_validate(policy.model_dump())
    context = ComfyExecutionContext.model_validate(context.model_dump())
    if context.mode != 'mock' or type(stage) is not str or stage not in ('admission', 'running'):
        raise ValueError('Expected mock context and valid stage')
    # Reuse sample identity validation without trusting any telemetry.
    ComfyResourceSample(
        context=context,
        worker_id=worker_id,
        device_index=policy.device_index,
        sampled_at=0,
        rss_bytes=0,
        available_ram_bytes=0,
        used_vram_bytes=0,
    )
    start, now = _time(start), _time(now)
    final = start + policy.overall_timeout_seconds
    cleanup = final - policy.reap_allowance_seconds
    run = cleanup - policy.cleanup_reserve_seconds
    if not isfinite(final) or not start < run < cleanup < final or now < start:
        raise ValueError('Invalid or unrepresentable deadlines')
    reasons = []
    if sample is None:
        reasons.append('telemetry_missing')
    else:
        try:
            if type(sample) is ComfyResourceSample:
                sample = sample.model_dump()
            if type(sample) is not dict:
                raise ValueError('Expected sample')
            measured = ComfyResourceSample.model_validate(sample)
            measured_context = ComfyExecutionContext.model_validate(measured.context.model_dump())
            if (
                measured_context != context
                or measured.worker_id != worker_id
                or measured.device_index != policy.device_index
                or not start <= measured.sampled_at <= now
            ):
                raise ValueError('Sample identity or time mismatch')
        except (ValueError, TypeError):
            reasons.append('telemetry_invalid')
        else:
            if now - measured.sampled_at > policy.stale_after_seconds:
                reasons.append('telemetry_stale')
            if measured.rss_bytes >= policy.ram_limit_bytes:
                reasons.append('ram_limit')
            if measured.available_ram_bytes <= policy.host_reserve_bytes:
                reasons.append('host_reserve')
            if measured.used_vram_bytes >= policy.vram_limit_bytes:
                reasons.append('vram_limit')
    if now >= run:
        reasons.append('run_deadline')
    action = ('deny' if stage == 'admission' else 'abort') if reasons else 'allow'
    return ResourceDecision(action, tuple(reasons), run, cleanup, final, max(0.0, run - now))
