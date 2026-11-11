"""One immutable user-authored snapshot per existing character."""

import sqlite3
from contextlib import closing
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from animation_studio.domain.v1.character_profile import CharacterProfileDraft


class SavedCharacterProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)
    character_id: int
    schema_version: Literal[1] = 1
    profile: CharacterProfileDraft
    created_at: str


class ProfileConflict(ValueError):
    pass


class InvalidStoredProfile(ValueError):
    pass


class UnsupportedProfileVersion(InvalidStoredProfile):
    """A v1-only reader must not report an existing reviewed profile as absent."""


def _profile_exists(connection, character_id: int) -> bool:
    return (
        connection.execute(
            'SELECT 1 FROM character_profiles WHERE character_id=? '
            'UNION ALL SELECT 1 FROM reviewed_character_profiles WHERE character_id=? LIMIT 1',
            (character_id, character_id),
        ).fetchone()
        is not None
    )


def _identity(character_id: int):
    if type(character_id) is not int or not 1 <= character_id <= 2**63 - 1:
        raise ValueError('Invalid character identity')


class CharacterProfileStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @staticmethod
    def _view(row):
        try:
            return SavedCharacterProfile(
                character_id=row['character_id'],
                schema_version=row['schema_version'],
                profile=CharacterProfileDraft.model_validate_json(row['profile_json']),
                created_at=row['created_at'],
            )
        except (ValidationError, ValueError, TypeError):
            raise InvalidStoredProfile('Stored character profile invalid') from None

    def read(self, character_id: int) -> SavedCharacterProfile | None:
        _identity(character_id)
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute('BEGIN')
            if not connection.execute(
                'SELECT 1 FROM characters WHERE id=?', (character_id,)
            ).fetchone():
                raise LookupError('Character not found')
            if connection.execute(
                'SELECT 1 FROM reviewed_character_profiles WHERE character_id=?', (character_id,)
            ).fetchone():
                raise UnsupportedProfileVersion('Unsupported character profile version')
            row = connection.execute(
                'SELECT * FROM character_profiles WHERE character_id=?', (character_id,)
            ).fetchone()
            return self._view(row) if row else None

    def save(self, character_id: int, profile: CharacterProfileDraft) -> SavedCharacterProfile:
        _identity(character_id)
        profile = CharacterProfileDraft.model_validate(profile)
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
            connection.execute(
                'INSERT INTO character_profiles(character_id,schema_version,profile_json) VALUES(?,1,?)',
                (character_id, profile.model_dump_json()),
            )
            return self._view(
                connection.execute(
                    'SELECT * FROM character_profiles WHERE character_id=?', (character_id,)
                ).fetchone()
            )
