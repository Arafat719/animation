"""Offline compute estimates and preflight admission; never authorizes paid use."""

from decimal import ROUND_CEILING, Decimal, localcontext
from typing import Annotated, Literal

from pydantic import Field, model_validator

from animation_studio.providers.gpu import Contract, GPUJob, GPUJobRequest, GPUProvider, Text

# Bounded decimal inputs avoid binary float arithmetic and unbounded exponents.
Amount = Annotated[Decimal, Field(ge=0, le=1000000, max_digits=13, decimal_places=6)]
Minutes = Annotated[Decimal, Field(gt=0, le=1000000, max_digits=13, decimal_places=6)]
Attempts = Annotated[int, Field(ge=1, le=1000, strict=True)]
LimitCode = Literal['hourly_price', 'gpu_minutes', 'shot_attempts', 'render_cost']


class BudgetConfig(Contract):
    """Explicit limits in USD; no implicit spending allowance."""

    currency: Literal['USD'] = 'USD'
    max_gpu_hourly_price: Amount
    max_gpu_minutes_per_job: Amount
    max_attempts_per_shot: Attempts
    max_estimated_cost_per_render: Amount


class PlannedGPUShot(Contract):
    shot_id: Text
    request: GPUJobRequest
    gpu_minutes_per_attempt: Minutes
    attempts: Attempts


class RenderWorkload(Contract):
    """One render job; attempts include the first run, not HTTP transport retries.

    Caller must include all stages in its per-attempt estimate. Startup overhead
    is billed once per render. Storage/egress/tax are excluded, never assumed free.
    """

    gpu_hourly_price: Amount
    startup_gpu_minutes: Amount
    shots: tuple[PlannedGPUShot, ...] = Field(min_length=1, max_length=10000)

    @model_validator(mode='after')
    def unique_shots(self):
        if len({shot.shot_id for shot in self.shots}) != len(self.shots):
            raise ValueError('Each shot must occur once; reserve its attempts in that entry')
        return self


class BudgetEstimate(Contract):
    currency: Literal['USD'] = 'USD'
    reserved_gpu_minutes: Decimal = Field(ge=0, allow_inf_nan=False)
    estimated_compute_cost: Decimal = Field(ge=0, allow_inf_nan=False)
    violations: tuple[LimitCode, ...]

    @property
    def allowed(self) -> bool:
        return not self.violations


class BudgetExceeded(Exception):
    code = 'budget_exceeded'

    def __init__(self, estimate: BudgetEstimate):
        self.estimate = estimate
        super().__init__(
            'GPU workload exceeds configured limits: ' + ', '.join(estimate.violations)
        )


def estimate_render(workload: RenderWorkload, config: BudgetConfig) -> BudgetEstimate:
    """Pure dry-run; cost rounds upward to USD 0.000001 before limit comparison."""
    # Revalidate even model_copy/model_construct inputs at this admission boundary.
    workload = RenderWorkload.model_validate(workload.model_dump())
    config = BudgetConfig.model_validate(config.model_dump())
    with localcontext() as context:
        context.prec = 50
        minutes = workload.startup_gpu_minutes + sum(
            (shot.gpu_minutes_per_attempt * shot.attempts for shot in workload.shots), Decimal(0)
        )
        cost = (minutes * workload.gpu_hourly_price / 60).quantize(
            Decimal('0.000001'), rounding=ROUND_CEILING
        )
    violations: list[LimitCode] = []
    if workload.gpu_hourly_price > config.max_gpu_hourly_price:
        violations.append('hourly_price')
    if minutes > config.max_gpu_minutes_per_job:
        violations.append('gpu_minutes')
    if any(shot.attempts > config.max_attempts_per_shot for shot in workload.shots):
        violations.append('shot_attempts')
    if cost > config.max_estimated_cost_per_render:
        violations.append('render_cost')
    return BudgetEstimate(
        reserved_gpu_minutes=minutes, estimated_compute_cost=cost, violations=tuple(violations)
    )


def submit_budgeted_shot(
    provider: GPUProvider,
    workload: RenderWorkload,
    config: BudgetConfig,
    *,
    shot_id: str,
    timeout_seconds: float = 10,
) -> GPUJob:
    """Check the whole render before sending one selected shot's initial attempt.

    This is a preflight gate, not a durable attempt/spend ledger or retry runner.
    It submits once and never catches/retries ambiguous provider failures. It does
    not replace owner approval, real runtime caps or paid dispatch authorization.
    """
    workload = RenderWorkload.model_validate(workload.model_dump())
    estimate = estimate_render(workload, config)
    if not estimate.allowed:
        raise BudgetExceeded(estimate)
    shot = next((shot for shot in workload.shots if shot.shot_id == shot_id), None)
    if shot is None:
        raise ValueError('Shot is not part of the estimated render')
    return provider.submit(shot.request, timeout_seconds=timeout_seconds)
