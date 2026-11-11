"""Internal v2 storage and authoritative reads; no HTTP writer or draft trust layer.

The save caller must own the report and expected context. This repository does not
attest client-supplied provenance; a server-owned draft lookup is required before
an eventual reviewed-save API may call it.
"""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from animation_studio.domain.v1.character_extraction import (
    ExtractionModel,
    ExtractionRequest,
    ProviderIdentity,
    validate_extraction_report,
)
from animation_studio.domain.v1.character_review import ReviewedExtractionProfile
from animation_studio.persistence.character_profiles import (
    CharacterProfileStore,
    InvalidStoredProfile,
    ProfileConflict,
    SavedCharacterProfile,
    _identity,
    _profile_exists,
)


class SavedReviewedCharacterProfile(ExtractionModel):
    character_id: int = Field(gt=0, le=2**63 - 1)
    schema_version: Literal[2] = 2
    profile: ReviewedExtractionProfile
    created_at: str
    reviewed_at: str

    @field_validator('schema_version', mode='before')
    @classmethod
    def version(cls, value):
        if type(value) is not int or value != 2:
            raise ValueError('Unsupported stored profile version')
        return value

    @field_validator('created_at', 'reviewed_at')
    @classmethod
    def timestamp(cls, value):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
            raise ValueError('Stored timestamps must be UTC')
        return value

    @model_validator(mode='after')
    def binding(self):
        if self.character_id != self.profile.character_id:
            raise ValueError('Stored profile identity mismatch')
        return self


class ReviewedCharacterProfileStore:
    """Requires a migrated database. Saves only internally trusted v2 snapshots."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    @staticmethod
    def _view(row) -> SavedReviewedCharacterProfile:
        try:
            return SavedReviewedCharacterProfile(
                character_id=row['character_id'],
                schema_version=row['schema_version'],
                profile=ReviewedExtractionProfile.model_validate_json(row['reviewed_json']),
                created_at=row['created_at'],
                reviewed_at=row['reviewed_at'],
            )
        except (ValidationError, ValueError, TypeError):
            raise InvalidStoredProfile('Stored character profile invalid') from None

    def read(
        self, character_id: int
    ) -> SavedCharacterProfile | SavedReviewedCharacterProfile | None:
        """Read the one authoritative version; corruption never falls back to null/v1."""
        _identity(character_id)
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute('BEGIN')
            if not connection.execute(
                'SELECT 1 FROM characters WHERE id=?', (character_id,)
            ).fetchone():
                raise LookupError('Character not found')
            manual = connection.execute(
                'SELECT * FROM character_profiles WHERE character_id=?', (character_id,)
            ).fetchone()
            reviewed = connection.execute(
                'SELECT * FROM reviewed_character_profiles WHERE character_id=?', (character_id,)
            ).fetchone()
            if manual and reviewed:
                raise InvalidStoredProfile('Stored character profile invalid')
            if reviewed:
                return self._view(reviewed)
            return CharacterProfileStore._view(manual) if manual else None

    def save(
        self,
        profile: ReviewedExtractionProfile,
        *,
        expected_request: ExtractionRequest,
        expected_provider: ProviderIdentity,
    ) -> SavedReviewedCharacterProfile:
        # Validate before opening a database; no unchecked copy can bypass the contract.
        profile = ReviewedExtractionProfile.model_validate(profile)
        validate_extraction_report(
            profile.provenance.report,
            expected_request=expected_request,
            expected_provider=expected_provider,
        )
        character_id = profile.character_id
        with closing(sqlite3.connect(self.db_path, timeout=30)) as connection, connection:
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('BEGIN IMMEDIATE')
            if not connection.execute(
                'SELECT 1 FROM characters WHERE id=?', (character_id,)
            ).fetchone():
                raise LookupError('Character not found')
            if _profile_exists(connection, character_id):
                raise ProfileConflict('Character profile already saved')
            # Other SQL errors propagate; only a proven existing profile means conflict.
            connection.execute(
                'INSERT INTO reviewed_character_profiles '
                '(character_id,schema_version,reviewed_json) VALUES (?,2,?)',
                (character_id, profile.model_dump_json()),
            )
            return self._view(
                connection.execute(
                    'SELECT * FROM reviewed_character_profiles WHERE character_id=?',
                    (character_id,),
                ).fetchone()
            )
