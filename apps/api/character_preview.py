"""Explicit saved-character selection for a read-only offline plan preview."""

import sqlite3
from contextlib import closing
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from animation_studio.domain.v1.story_plan import StoryPlan
from animation_studio.persistence.character_profiles import (
    InvalidStoredProfile,
)
from animation_studio.persistence.db import init_db
from animation_studio.persistence.reviewed_character_profiles import (
    ReviewedCharacterProfileStore,
    SavedReviewedCharacterProfile,
)
from animation_studio.providers.character_profile_adapter import to_planner_character
from animation_studio.providers.planner import PlannerRequest
from animation_studio.providers.planner_repair import RepairExhausted
from animation_studio.providers.planner_service import MockDraftProvider, PlannerService

router = APIRouter()
SelectedId = Annotated[int, Field(strict=True, gt=0, le=2**63 - 1)]


class CharacterPreviewRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    character_ids: list[SelectedId] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique_ids(self):
        if len(self.character_ids) != len(set(self.character_ids)):
            raise ValueError('Character IDs must be unique')
        return self


class ManualProfileOrigin(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra='forbid')
    character_id: SelectedId
    schema_version: Literal[1] = 1
    source: Literal['user_provided'] = 'user_provided'
    is_mock: None = None


class ReviewedProfileOrigin(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra='forbid')
    character_id: SelectedId
    schema_version: Literal[2] = 2
    source: Literal['reviewed_extraction'] = 'reviewed_extraction'
    is_mock: bool


ProfileOrigin = Annotated[
    ManualProfileOrigin | ReviewedProfileOrigin, Field(discriminator='source')
]


class CharacterPreview(BaseModel):
    plan: StoryPlan
    profile_origins: list[ProfileOrigin]
    is_mock: Literal[True] = True
    status: Literal['REVIEW_REQUIRED'] = 'REVIEW_REQUIRED'


@router.post('/projects/{project_id}/mock-plan', response_model=CharacterPreview)
def preview_characters(
    project_id: Annotated[int, Path(gt=0, le=2**63 - 1)], payload: CharacterPreviewRequest
):
    path = init_db()
    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        project = connection.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
    if project is None:
        raise HTTPException(404, detail='Project not found')
    store = ReviewedCharacterProfileStore(path)
    profiles = []
    origins = []
    for character_id in payload.character_ids:
        try:
            saved = store.read(character_id)
        except LookupError:
            raise HTTPException(404, detail='Selected character not found') from None
        except InvalidStoredProfile:
            raise HTTPException(500, detail='Stored character profile invalid') from None
        if saved is None:
            raise HTTPException(409, detail='Selected character has no saved profile')
        profiles.append(to_planner_character(saved, expected_character_id=character_id))
        if isinstance(saved, SavedReviewedCharacterProfile):
            origins.append(
                ReviewedProfileOrigin(
                    character_id=character_id,
                    is_mock=saved.profile.provenance.report.provider.is_mock,
                )
            )
        else:
            origins.append(ManualProfileOrigin(character_id=character_id))
    try:
        request = PlannerRequest(
            prompt=project['master_prompt'],
            duration_seconds=project['target_duration_seconds']
            if project['target_duration_seconds'] is not None
            else 30,
            characters=profiles,
        )
    except ValidationError:
        raise HTTPException(
            422, detail='Mock planning requires a prompt of 1–4000 characters and 30–60 seconds.'
        ) from None
    try:
        plan = PlannerService(MockDraftProvider(), max_retries=0).plan(request)
    except RepairExhausted as error:
        raise HTTPException(
            422,
            detail={
                'code': 'PLANNER_OUTPUT_INVALID',
                'attempts': error.attempts,
                'issues': [
                    {'code': issue.code, 'path': list(issue.path)} for issue in error.issues
                ],
            },
        ) from None
    return CharacterPreview(plan=plan, profile_origins=origins)
