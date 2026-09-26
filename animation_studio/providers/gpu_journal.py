"""Linux-local, single-writer journal for explicitly invoked mock recovery."""

import fcntl
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from animation_studio.providers.gpu import ErrorCode
from animation_studio.providers.gpu_lifecycle import (
    MockLifecycle,
    MockRESTLifecycle,
    MockSessionController,
)


class SessionRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True, allow_inf_nan=False)

    schema_version: Literal[1] = 1
    session_id: str = Field(pattern=r'^[a-z0-9-]{1,64}$')
    provider: Literal['runpod'] = 'runpod'
    mode: Literal['mock'] = 'mock'
    pod_id: str = Field(pattern=r'^[a-z0-9]{1,64}$')
    created_at_utc: float = Field(ge=0)
    deadline_at_utc: float = Field(gt=0)
    cleanup_requested: bool = False
    attempt_count: int = Field(default=0, ge=0, le=3)
    last_compute: Literal['running', 'stopped', 'absent', 'unknown'] = 'unknown'
    last_storage: Literal['none', 'retained', 'unknown'] = 'unknown'
    last_error_codes: tuple[Literal['inspect_failed', 'stop_failed', 'terminate_failed'], ...] = ()

    last_provider_codes: tuple[ErrorCode, ...] = ()

    @field_validator('schema_version', mode='before')
    @classmethod
    def strict_version(cls, data):
        if type(data) is not int:
            raise ValueError('Invalid schema version type')
        return data

    @model_validator(mode='after')
    def coherent(self):
        if type(self.schema_version) is not int or self.deadline_at_utc <= self.created_at_utc:
            raise ValueError('Invalid version or deadline')
        if not self.cleanup_requested and (
            self.attempt_count
            or self.last_compute != 'unknown'
            or self.last_storage != 'unknown'
            or self.last_error_codes
            or self.last_provider_codes
        ):
            raise ValueError('Unarmed recovery state')
        return self

    @property
    def outcome(self) -> str:
        if 'unauthorized' in self.last_provider_codes:
            return 'needs_manual_cleanup'
        if self.last_compute == 'absent':
            return 'complete' if self.last_storage == 'none' else 'needs_manual_cleanup'
        if self.attempt_count >= 3:
            return 'needs_manual_cleanup'
        return 'pending'


class MockSessionJournal:
    """Caller owns a private existing directory. No automatic process or live I/O.

    Lock file is persistent: never unlink it, which could split lock ownership.
    Successful arm is a persistence checkpoint, not production job admission.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def _locked(self):
        fd = os.open(str(self.path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def _read(self) -> SessionRecord:
        return SessionRecord.model_validate_json(self.path.read_bytes())

    def _write(self, record: SessionRecord):
        fd, name = tempfile.mkstemp(prefix='.gpu-session-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(record.model_dump_json())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def arm(self, record: SessionRecord):
        record = SessionRecord.model_validate_json(record.model_dump_json())
        if record.cleanup_requested or record.attempt_count:
            raise ValueError('Expected a fresh session')
        with self._locked():
            if self.path.exists():
                raise FileExistsError('Session already exists')
            self._write(record)

    def recover(self, backend: MockLifecycle | MockRESTLifecycle) -> SessionRecord:
        # Controller enforces exact mock backend types before any journal mutation.
        controller = MockSessionController(backend, started_at=0, duration_seconds=1)
        with self._locked():
            record = self._read()
            if backend.state.pod_id != record.pod_id:
                raise ValueError('Resource ID mismatch')
            if record.outcome != 'pending':
                return record
            # Persist intent before HTTP, even if the previous deadline is in the future.
            pending = record.model_copy(
                update={
                    'cleanup_requested': True,
                    'attempt_count': record.attempt_count + 1,
                }
            )
            self._write(pending)
            result = controller.cleanup()
            final = pending.model_copy(
                update={
                    'last_compute': result.state.compute,
                    'last_storage': result.state.storage,
                    'last_error_codes': result.errors,
                    'last_provider_codes': result.provider_codes,
                }
            )
            self._write(final)
            return final
