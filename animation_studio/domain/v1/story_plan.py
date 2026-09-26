"""Strict planning contracts, distinct from the persisted Phase 1 ShotRecord."""

import math
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Text = Annotated[str, Field(min_length=1, max_length=4000)]
Identifier = Annotated[str, Field(min_length=1, max_length=120)]


class PlanningModel(BaseModel):
    model_config = ConfigDict(
        strict=True, extra='forbid', str_strip_whitespace=True, allow_inf_nan=False
    )


class PlanCharacter(PlanningModel):
    id: Identifier
    name: Annotated[str, Field(min_length=1, max_length=120)]


class DialogueLine(PlanningModel):
    speaker_id: Identifier
    text: Text


class ShotError(PlanningModel):
    code: Identifier
    message: Text


class ShotPlan(PlanningModel):
    id: Identifier
    order: int = Field(ge=1, le=10)
    duration_seconds: float = Field(ge=3, le=6)
    camera_framing: Text
    camera_movement: Text
    background: Text
    action: Text
    lighting: Text
    visible_character_ids: list[Identifier] = Field(max_length=100)
    dialogue: list[DialogueLine] = Field(max_length=100)
    image_prompt: Text
    negative_prompt: str = Field(max_length=4000)
    motion_prompt: Text
    seed: int = Field(ge=0, le=2**32 - 1)
    reference_inputs: list[Text] = Field(default_factory=list, max_length=100)
    keyframe_path: Text | None = None
    raw_clip_path: Text | None = None
    lip_synced_clip_path: Text | None = None
    status: Literal['pending', 'running', 'completed', 'failed', 'cancelled'] = 'pending'
    attempts: int = Field(default=0, ge=0)
    error: ShotError | None = None

    @model_validator(mode='after')
    def unique_visible_characters(self) -> Self:
        if len(self.visible_character_ids) != len(set(self.visible_character_ids)):
            raise ValueError('Visible character IDs must be unique')
        return self


class StoryPlan(PlanningModel):
    schema_version: Literal[1]
    logline: Text
    setting: Text
    mood: Text
    visual_style: Text
    characters: list[PlanCharacter] = Field(max_length=100)
    shots: list[ShotPlan] = Field(min_length=6, max_length=10)
    estimated_total_duration_seconds: float = Field(ge=30, le=60)

    @field_validator('schema_version', mode='before')
    @classmethod
    def strict_schema_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError('Schema version must be an integer')
        return value

    @model_validator(mode='after')
    def validate_timeline_and_references(self) -> Self:
        ids = [character.id for character in self.characters]
        if len(ids) != len(set(ids)):
            raise ValueError('Character IDs must be unique')
        if len({shot.id for shot in self.shots}) != len(self.shots):
            raise ValueError('Shot IDs must be unique')
        if [shot.order for shot in self.shots] != list(range(1, len(self.shots) + 1)):
            raise ValueError('Shots must be listed in contiguous one-based order')
        total = math.fsum(shot.duration_seconds for shot in self.shots)
        if not 30 <= total <= 60 or not math.isclose(
            total, self.estimated_total_duration_seconds, rel_tol=0, abs_tol=1e-6
        ):
            raise ValueError('Estimated duration must equal the 30–60 second shot timeline')
        known = set(ids)
        for shot in self.shots:
            if not set(shot.visible_character_ids) <= known:
                raise ValueError('Visible characters must reference the plan cast')
            if any(line.speaker_id not in known for line in shot.dialogue):
                raise ValueError('Dialogue speakers must reference the plan cast')
        return self
