"""RenderJob baseline v1, preserving current API defaults and stored values."""

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    current_step: str | None = Field(default='queued')


class FixtureJobCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')


class RenderJob(BaseModel):
    id: int
    project_id: int
    current_step: str | None = 'queued'
    current_shot: int | None = None
    state: str | None = 'running'
    progress: int | None = 0


class RenderJobRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)

    id: int
    project_id: int
    current_step: str | None
    current_shot: int | None
    state: str | None
    progress: int | None
    created_at: str
    updated_at: str
