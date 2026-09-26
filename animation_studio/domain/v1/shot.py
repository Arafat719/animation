"""Complete persisted Shot baseline v1; planning contracts belong to Phase 3."""

from pydantic import BaseModel, ConfigDict


class ShotRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True, allow_inf_nan=False)

    id: int
    project_id: int
    order_index: int
    duration_seconds: float
    prompt: str
    status: str | None
