"""Explicit profile save/read; no automatic extraction or generation."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from pydantic import Discriminator, Field, Tag

from animation_studio.domain.v1.character_profile import CharacterProfileDraft
from animation_studio.persistence.character_profiles import (
    CharacterProfileStore,
    InvalidStoredProfile,
    ProfileConflict,
    SavedCharacterProfile,
    UnsupportedProfileVersion,
)
from animation_studio.persistence.db import init_db
from animation_studio.persistence.reviewed_character_profiles import (
    ReviewedCharacterProfileStore,
    SavedReviewedCharacterProfile,
)

router = APIRouter()
CharacterId = Annotated[int, Path(gt=0, le=2**63 - 1)]


# A callable discriminator preserves the stored model's strict before-validator.
def _profile_version(value):
    version = (
        value.get('schema_version')
        if isinstance(value, dict)
        else getattr(value, 'schema_version', None)
    )
    return version if type(version) is int else None


VersionedProfile = Annotated[
    Annotated[SavedCharacterProfile, Tag(1)] | Annotated[SavedReviewedCharacterProfile, Tag(2)],
    Discriminator(_profile_version),
    Field(
        json_schema_extra={
            'discriminator': {
                'propertyName': 'schema_version',
                'mapping': {
                    '1': '#/components/schemas/SavedCharacterProfile',
                    '2': '#/components/schemas/SavedReviewedCharacterProfile',
                },
            },
        }
    ),
]


@router.post(
    '/characters/{character_id}/profile', response_model=SavedCharacterProfile, status_code=201
)
def save_profile(character_id: CharacterId, payload: CharacterProfileDraft):
    try:
        return CharacterProfileStore(init_db()).save(character_id, payload)
    except LookupError:
        raise HTTPException(404, detail='Character not found') from None
    except ProfileConflict:
        raise HTTPException(409, detail='Character profile already saved') from None


@router.get('/characters/{character_id}/profile', response_model=SavedCharacterProfile | None)
def read_profile(character_id: CharacterId):
    try:
        return CharacterProfileStore(init_db()).read(character_id)
    except LookupError:
        raise HTTPException(404, detail='Character not found') from None
    except UnsupportedProfileVersion:
        raise HTTPException(409, detail='Unsupported character profile version') from None
    except InvalidStoredProfile:
        raise HTTPException(500, detail='Stored character profile invalid') from None


@router.get('/v2/characters/{character_id}/profile', response_model=VersionedProfile | None)
def read_versioned_profile(character_id: CharacterId):
    """Read the authoritative saved version, retaining reviewed provenance and mock origin."""
    try:
        return ReviewedCharacterProfileStore(init_db()).read(character_id)
    except LookupError:
        raise HTTPException(404, detail='Character not found') from None
    except InvalidStoredProfile:
        raise HTTPException(500, detail='Stored character profile invalid') from None
