"""Save/read final fixture-provider outcomes, independently of job execution."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from animation_studio.persistence.db import init_db
from animation_studio.providers.fake import ErrorCode, FakeResult


class UnknownJobError(LookupError):
    pass


class JobResultConflictError(RuntimeError):
    pass


class StoredError(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, str_strip_whitespace=True)
    code: ErrorCode
    message: str = Field(min_length=1, max_length=2000)


class Outcome(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    result: FakeResult | None = None
    error: StoredError | None = None

    @model_validator(mode='after')
    def validate_outcome(self) -> Self:
        if (self.result is None) == (self.error is None):
            raise ValueError('Exactly one result or error is required')
        if self.result is not None:
            for kind in ('image', 'audio', 'video'):
                artifact = getattr(self.result, kind)
                if artifact.kind != kind or not artifact.path.is_absolute():
                    raise ValueError('Artifact kind must match its field and its path must be absolute')
                if kind != 'image' and artifact.duration_seconds is None:
                    raise ValueError('Audio and video require a positive duration')
        return self


class SavedOutcome(Outcome):
    job_id: int = Field(gt=0, strict=True)
    schema_version: Literal[1]
    created_at: str


JOB_ID = TypeAdapter(int)


class JobResultRepository:
    """An explicit database path is required; constructor applies migrations.

    All outcomes are immutable. Identical retries return the stored record;
    conflicting writes raise JobResultConflictError, including error replacement.
    """

    def __init__(self, db_path: str):
        self.db_path = str(Path(init_db(db_path)).absolute())

    @staticmethod
    def _validate_id(job_id: int) -> int:
        value = JOB_ID.validate_python(job_id, strict=True)
        if value <= 0:
            raise ValueError('Job ID must be positive')
        return value

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        return connection

    @staticmethod
    def _require_job(connection: sqlite3.Connection, job_id: int):
        if connection.execute('SELECT id FROM render_jobs WHERE id = ?', (job_id,)).fetchone() is None:
            raise UnknownJobError(f'Job {job_id} does not exist')

    @staticmethod
    def _read(connection: sqlite3.Connection, job_id: int) -> SavedOutcome | None:
        row = connection.execute('SELECT * FROM job_results WHERE job_id = ?', (job_id,)).fetchone()
        if row is None:
            return None
        return SavedOutcome(
            job_id=row['job_id'], schema_version=row['schema_version'], created_at=row['created_at'],
            result=FakeResult.model_validate_json(row['result_json']) if row['result_json'] is not None else None,
            error=StoredError(code=row['error_code'], message=row['error_message'])
            if row['error_code'] is not None or row['error_message'] is not None else None,
        )

    def get(self, job_id: int) -> SavedOutcome | None:
        job_id = self._validate_id(job_id)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute('BEGIN')
                self._require_job(connection, job_id)
                return self._read(connection, job_id)

    def save_success(self, job_id: int, result: FakeResult | dict[str, object]) -> SavedOutcome:
        # Revalidate even model instances that may have been copied without validation.
        payload = result.model_dump() if isinstance(result, FakeResult) else result
        return self._save(job_id, Outcome(result=payload))

    def save_error(self, job_id: int, error: StoredError | dict[str, object]) -> SavedOutcome:
        payload = error.model_dump() if isinstance(error, StoredError) else error
        return self._save(job_id, Outcome(error=payload))

    def _save(self, job_id: int, outcome: Outcome) -> SavedOutcome:
        job_id = self._validate_id(job_id)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute('BEGIN IMMEDIATE')
                self._require_job(connection, job_id)
                existing = self._read(connection, job_id)
                if existing is not None:
                    if existing.result == outcome.result and existing.error == outcome.error:
                        return existing
                    raise JobResultConflictError(f'Job {job_id} already has a different final outcome')
                connection.execute('''
                    INSERT INTO job_results (job_id, result_json, error_code, error_message)
                    VALUES (?, ?, ?, ?)
                ''', (
                    job_id, outcome.result.model_dump_json() if outcome.result is not None else None,
                    outcome.error.code if outcome.error is not None else None,
                    outcome.error.message if outcome.error is not None else None,
                ))
                saved = self._read(connection, job_id)
                if saved is None:
                    raise RuntimeError('Inserted job outcome could not be read')
                return saved
