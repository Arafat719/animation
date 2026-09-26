"""Project baseline v1: existing API shapes and a complete persisted record.

API coercion/defaults remain compatible. ProjectRecord describes supported SQLite
row values without coercion, trimming, timestamp parsing or new V1 feature limits.
See docs/contracts/project-v1.md for SQL/API differences and endpoint validation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    master_prompt: str | None = Field(default=None)
    target_duration_seconds: int | None = Field(default=None, ge=1, le=600)
    status: str = Field(default='draft')


class Project(BaseModel):
    id: int
    title: str
    master_prompt: str | None = None
    target_duration_seconds: int | None = None
    status: str | None = 'draft'


class ProjectRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)

    id: int
    title: str
    created_at: str
    updated_at: str
    master_prompt: str | None
    target_duration_seconds: int | None
    status: str | None
