"""Pure capability-claim admission evaluation; no evidence collection or dispatch.

An allow decision only describes supplied claims. Target labels/hashes are not
attestation; production collection, resource enforcement and wiring remain absent.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_resource_guard import _time
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy

Capability = Literal[
    'runtime_native',
    'model_identity',
    'endpoint_auth_routes',
    'worker_ownership',
    'resource_supervision',
]
REQUIRED_CAPABILITIES = (
    'runtime_native',
    'model_identity',
    'endpoint_auth_routes',
    'worker_ownership',
    'resource_supervision',
)
Source = Literal['fixture', 'target']
Reason = Literal[
    'input_invalid',
    'observation_invalid',
    'capability_missing',
    'capability_duplicate',
    'capability_failed',
    'capability_unknown',
    'context_mismatch',
    'worker_mismatch',
    'device_mismatch',
    'policy_mismatch',
    'source_mismatch',
    'clock_session_mismatch',
    'evidence_future',
    'evidence_stale',
]


class ComfyAdmissionObservation(BaseModel):
    """One immutable claim, not verified evidence or permission to execute."""

    model_config = ConfigDict(
        strict=True, extra='forbid', frozen=True, revalidate_instances='always'
    )
    capability: Capability
    status: Literal['passed', 'failed', 'unknown']
    context: ComfyExecutionContext
    worker_id: str = Field(min_length=1, max_length=128, pattern=r'^[a-zA-Z0-9_-]+$')
    device_index: int = Field(ge=0)
    policy_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    source: Source
    clock_session_id: str
    checked_at: float
    evidence_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

    @field_validator('context')
    @classmethod
    def valid_context(cls, value):
        return ComfyExecutionContext.model_validate(dict(value.__dict__))

    @field_validator('clock_session_id')
    @classmethod
    def valid_clock_session(cls, value):
        if str(UUID(value)) != value:
            raise ValueError('Expected canonical clock session UUID')
        return value

    @field_validator('checked_at', mode='before')
    @classmethod
    def valid_time(cls, value):
        return _time(value)


def admission_policy_sha256(policy: ComfySupervisionPolicy) -> str:
    """Bind all validated policy fields, not its repr or a caller-provided ID."""
    try:
        if type(policy) is not ComfySupervisionPolicy:
            raise ValueError
        validated = ComfySupervisionPolicy.model_validate(dict(policy.__dict__))
        content = json.dumps(
            validated.model_dump(), sort_keys=True, separators=(',', ':'), allow_nan=False
        )
        return hashlib.sha256(content.encode()).hexdigest()
    except (ValueError, TypeError, OverflowError):
        raise ValueError('Invalid admission policy') from None


@dataclass(frozen=True)
class ComfyAdmissionDecision:
    action: Literal['allow', 'deny']
    source: Literal['fixture', 'target', 'unknown']
    reasons: tuple[Reason, ...]


def evaluate_admission(
    *,
    context: ComfyExecutionContext,
    policy: ComfySupervisionPolicy,
    worker_id: str,
    clock_session_id: str,
    expected_source: Source,
    now: float,
    max_age_seconds: float,
    observations: tuple[ComfyAdmissionObservation, ...],
) -> ComfyAdmissionDecision:
    """Evaluate a bounded in-memory snapshot; invalid input denies without echoing it.

    The caller supplies a fresh clock-session UUID for each process lifetime and
    preserves its monotonic time domain. This function reads no clock or evidence.
    Fixture claims only allow mock-context evaluation; target claims require live
    context. Neither decision type is consumed by a production executor.
    """
    try:
        if type(context) is not ComfyExecutionContext or type(policy) is not ComfySupervisionPolicy:
            raise ValueError
        context = ComfyExecutionContext.model_validate(dict(context.__dict__))
        policy_digest = admission_policy_sha256(policy)
        # Shared observation validators also validate independent expected bindings.
        expected = ComfyAdmissionObservation(
            capability='runtime_native',
            status='unknown',
            context=context,
            worker_id=worker_id,
            device_index=policy.device_index,
            policy_sha256=policy_digest,
            source=expected_source,
            clock_session_id=clock_session_id,
            checked_at=now,
            evidence_sha256='0' * 64,
        )
        now, max_age = _time(now), _time(max_age_seconds)
        if (
            max_age <= 0
            or type(observations) is not tuple
            or len(observations) > len(REQUIRED_CAPABILITIES)
        ):
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        return ComfyAdmissionDecision('deny', 'unknown', ('input_invalid',))

    reasons: list[Reason] = []
    if (expected_source == 'fixture') != (context.mode == 'mock'):
        reasons.append('source_mismatch')
    seen = set()
    for observation in observations:
        try:
            if type(observation) is not ComfyAdmissionObservation:
                raise ValueError
            # model_copy can inject forbidden fields that model_dump would discard.
            observed = ComfyAdmissionObservation.model_validate(dict(observation.__dict__))
        except (ValueError, TypeError, OverflowError):
            reasons.append('observation_invalid')
            continue
        if observed.capability in seen:
            reasons.append('capability_duplicate')
        seen.add(observed.capability)
        if observed.status != 'passed':
            reasons.append(
                'capability_failed' if observed.status == 'failed' else 'capability_unknown'
            )
        for actual, wanted, reason in (
            (observed.context, context, 'context_mismatch'),
            (observed.worker_id, expected.worker_id, 'worker_mismatch'),
            (observed.device_index, expected.device_index, 'device_mismatch'),
            (observed.policy_sha256, policy_digest, 'policy_mismatch'),
            (observed.source, expected_source, 'source_mismatch'),
            (observed.clock_session_id, expected.clock_session_id, 'clock_session_mismatch'),
        ):
            if actual != wanted:
                reasons.append(reason)
        if observed.checked_at > now:
            reasons.append('evidence_future')
        elif now - observed.checked_at > max_age:
            reasons.append('evidence_stale')
    if seen != set(REQUIRED_CAPABILITIES):
        reasons.append('capability_missing')
    return ComfyAdmissionDecision(
        'deny' if reasons else 'allow', expected_source, tuple(sorted(set(reasons)))
    )
