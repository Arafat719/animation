"""Pure offline supervision contracts; no persistence, clocks, processes or I/O.

Observation flags and evidence hashes are claims, never verified stop proof.
Mock v1 and live v2 records use separate parsers; neither enables execution.
"""

import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.image import ImageErrorCode

PositiveBytes = Annotated[int, Field(gt=0)]
Seconds = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Timestamp = Annotated[int, Field(ge=0, le=253402300799)]
Digest = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]
MAX_OBSERVATION_BYTES = 4096


class _Contract(BaseModel):
    model_config = ConfigDict(
        strict=True, extra='forbid', frozen=True, revalidate_instances='always'
    )


class ComfySupervisionPolicy(_Contract):
    """Explicit budgets only; validation does not enforce resource limits.

    Overall time includes cleanup and reap reserves; remaining time is for run.
    Byte counts describe the target host/device, not the HTTP client process.
    """

    ram_limit_bytes: PositiveBytes
    host_reserve_bytes: PositiveBytes
    device_index: int = Field(ge=0)
    vram_limit_bytes: PositiveBytes
    sample_interval_seconds: Seconds
    stale_after_seconds: Seconds
    overall_timeout_seconds: Seconds
    cleanup_reserve_seconds: Seconds
    reap_allowance_seconds: Seconds

    @model_validator(mode='after')
    def coherent(self):
        if self.stale_after_seconds < self.sample_interval_seconds:
            raise ValueError('Staleness bound must cover sample interval')
        if (
            self.cleanup_reserve_seconds + self.reap_allowance_seconds
            >= self.overall_timeout_seconds
        ):
            raise ValueError('No execution time remains after reserves')
        return self


class ComfySupervisionObservation(_Contract):
    """Mock sidecar schema v1, independent of generation journal versions.

    Context and evidence references require external trusted matching. No attempt
    guard, evidence lookup, timestamp freshness or transition enforcement here.
    """

    schema_version: Literal[1]
    context: ComfyExecutionContext
    prompt_id: str | None = None
    primary_outcome: Literal['success', 'unknown'] | ImageErrorCode
    cleanup_phase: Literal['not_requested', 'intent', 'observed', 'unknown']
    attempt_count: int = Field(ge=0, le=1)
    created_at: Timestamp
    updated_at: Timestamp
    source: Literal['none', 'mock']
    cancel_dispatched: bool | None = None
    job_status: Literal['unknown', 'terminal'] = 'unknown'
    worker_status: Literal['unknown', 'exited'] = 'unknown'
    compute_status: Literal['unknown', 'stopped', 'absent'] = 'unknown'
    storage_status: Literal['unknown', 'present', 'absent'] = 'unknown'
    evidence_sha256: Digest | None = None

    @field_validator('schema_version', mode='before')
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int:
            raise ValueError('Expected integer schema version')
        return value

    @field_validator('context')
    @classmethod
    def valid_context(cls, value):
        value = ComfyExecutionContext.model_validate(value.model_dump())
        if value.mode != 'mock':
            raise ValueError('Only mock observations supported')
        return value

    @field_validator('prompt_id')
    @classmethod
    def canonical_receipt(cls, value):
        if value is not None and str(UUID(value)) != value:
            raise ValueError('Expected canonical prompt ID')
        return value

    @model_validator(mode='after')
    def coherent(self):
        if self.updated_at < self.created_at:
            raise ValueError('Observation timestamps reversed')
        known_status = any(
            value != 'unknown'
            for value in (
                self.job_status,
                self.worker_status,
                self.compute_status,
                self.storage_status,
            )
        )
        if self.cleanup_phase == 'not_requested' and self.attempt_count != 0:
            raise ValueError('Unrequested cleanup cannot have an attempt')
        if self.cleanup_phase in ('intent', 'observed') and self.attempt_count != 1:
            raise ValueError('Cleanup phase requires an attempt')
        if self.cleanup_phase != 'observed' and (
            known_status
            or self.cancel_dispatched is not None
            or self.source != 'none'
            or self.evidence_sha256 is not None
        ):
            raise ValueError('Unobserved cleanup must remain unknown')
        if self.cleanup_phase == 'observed' and (
            self.source != self.context.mode or self.evidence_sha256 is None
        ):
            raise ValueError('Observation requires matching evidence source and reference')
        if (
            self.cancel_dispatched is not None or self.job_status == 'terminal'
        ) and self.prompt_id is None:
            raise ValueError('Prompt observation requires receipt identity')
        return self


class LiveComfySupervisionObservation(ComfySupervisionObservation):
    """Live-mode sidecar v2, never an upgrade of a mock observation.

    Source and status are caller claims; parsing does not verify evidence, stop a
    worker, or authorize dispatch. Synthetic test instances are not live evidence.
    """

    schema_version: Literal[2]
    source: Literal['none', 'live']

    @field_validator('context')
    @classmethod
    def valid_context(cls, value):
        # Override the v1 context validator, retaining all other field checks.
        value = ComfyExecutionContext.model_validate(value.model_dump())
        if value.mode != 'live':
            raise ValueError('Expected live observation context')
        return value


def parse_supervision_observation(
    content: bytes, context: ComfyExecutionContext
) -> ComfySupervisionObservation:
    """Bounded strict parsing and context matching; no file read or stop verification."""
    return _parse_observation(content, context, ComfySupervisionObservation)


def parse_live_supervision_observation(
    content: bytes, context: ComfyExecutionContext
) -> LiveComfySupervisionObservation:
    """Read live v2 only; reject v1/mock bytes without migration or relabeling."""
    return _parse_observation(content, context, LiveComfySupervisionObservation)


def _parse_observation(content, context, observation_type):
    try:
        if type(content) is not bytes or len(content) > MAX_OBSERVATION_BYTES:
            raise ValueError
        if type(context) is not ComfyExecutionContext:
            raise ValueError
        expected = ComfyExecutionContext.model_validate(context.model_dump())

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError
                result[key] = value
            return result

        def reject_constant(value):
            raise ValueError

        data = json.loads(content, object_pairs_hook=unique, parse_constant=reject_constant)
        result = observation_type.model_validate(data)
        if result.context != expected:
            raise ValueError
        return result
    except (ValueError, TypeError, RecursionError):
        raise ValueError('Invalid or incompatible Comfy supervision observation') from None
