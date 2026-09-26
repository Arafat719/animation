"""Deterministic shot timing, independent of providers."""

import math
from typing import Annotated

from pydantic import Field, TypeAdapter

PlanDuration = Annotated[float, Field(strict=True, ge=30, le=60, allow_inf_nan=False)]
_DURATION = TypeAdapter(PlanDuration)


def split_duration(total_seconds: float) -> list[float]:
    """Return 6–10 equal 3–6s shots; sum tolerance is StoryPlan's 1e-6s.

    Choose the fewest shots allowed by the six-second ceiling and six-shot floor.
    Reject invalid input with ValidationError; do not round or clamp the target.
    """
    total = _DURATION.validate_python(total_seconds)
    count = max(6, math.ceil(total / 6))
    return [total / count] * count
