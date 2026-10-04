"""Linux-local single-job journal: explicit creation versus read-only recovery.

Caller supplies a private existing directory and retains the same journal path
for the same logical job. Never delete an ambiguous journal to retry submission.
No backend database migration, live transport, or automatic recovery is enabled.
"""

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from threading import Event
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from animation_studio.providers.comfy_http import ComfyHTTPExecutor, ComfyReceipt
from animation_studio.providers.comfy_workflow import validate_image_workflow
from animation_studio.providers.image import ImageProviderError


class ComfyJobRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)
    schema_version: Literal[1] = 1
    mode: Literal['mock'] = 'mock'
    graph_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    state: Literal['intent', 'accepted']
    prompt_id: str | None = None

    @field_validator('schema_version', mode='before')
    @classmethod
    def version_type(cls, value):
        if type(value) is not int:
            raise ValueError('Invalid journal version')
        return value

    @model_validator(mode='after')
    def coherent(self):
        if self.state == 'intent':
            if self.prompt_id is not None:
                raise ValueError('Intent cannot contain a receipt')
        elif self.prompt_id is None or str(UUID(self.prompt_id)) != self.prompt_id:
            raise ValueError('Accepted record requires a canonical prompt UUID')
        return self


def _fingerprint(graph):
    validate_image_workflow(graph)
    return hashlib.sha256(json.dumps(graph, sort_keys=True, allow_nan=False).encode()).hexdigest()


class DurableComfyExecutor:
    """One journal per logical job; process lock held across the whole operation.

    Existing intent always blocks submit, even after crash before HTTP. Accepted
    records permit explicit GET-only recovery. Journal records contain a graph
    digest and receipt, never the prompt, media, credentials or server response.
    """

    is_mock = True

    def __init__(self, executor: ComfyHTTPExecutor, journal_path: Path):
        if type(executor) is not ComfyHTTPExecutor:
            raise TypeError('Durable executor requires the mock-only Comfy HTTP executor')
        self.executor = executor
        self.path = Path(journal_path).absolute()

    @contextmanager
    def _locked(self):
        # Permanent lock inode: unlinking it could allow two simultaneous owners.
        fd = os.open(str(self.path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def _write(self, record: ComfyJobRecord):
        fd, name = tempfile.mkstemp(prefix='.comfy-job-', dir=self.path.parent)
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

    def _read(self):
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate journal field')
                result[key] = value
            return result

        fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            content = stream.read(4097)
        if len(content) > 4096:
            raise ValueError('Journal too large')
        return ComfyJobRecord.model_validate(json.loads(content, object_pairs_hook=unique))

    def execute(self, graph: dict[str, dict], *, cancel: Event | None = None) -> bytes:
        digest = _fingerprint(graph)
        if cancel is not None and cancel.is_set():
            raise ImageProviderError('cancelled', 'Cancelled before durable submission')
        try:
            with self._locked():
                if os.path.lexists(self.path):
                    raise ImageProviderError(
                        'execution_failed', 'Journal exists; use explicit recovery'
                    )
                self.executor.preflight(graph, cancel=cancel)
                if cancel is not None and cancel.is_set():
                    raise ImageProviderError('cancelled', 'Cancelled before durable intent')
                self._write(ComfyJobRecord(graph_sha256=digest, state='intent'))

                def persist(receipt):
                    self._write(
                        ComfyJobRecord(
                            graph_sha256=digest, state='accepted', prompt_id=receipt.prompt_id
                        )
                    )

                return self.executor.execute(graph, cancel=cancel, on_receipt=persist)
        except OSError:
            raise ImageProviderError(
                'io_error', 'Journal unavailable; submission not retried'
            ) from None

    def recover(self, graph: dict[str, dict], *, cancel: Event | None = None) -> bytes:
        digest = _fingerprint(graph)
        try:
            with self._locked():
                record = self._read()
                if record.graph_sha256 != digest:
                    raise ImageProviderError('execution_failed', 'Journal workflow mismatch')
                if record.state != 'accepted':
                    raise ImageProviderError(
                        'execution_failed', 'Submission outcome unknown; receipt missing'
                    )
                return self.executor.recover(graph, ComfyReceipt(record.prompt_id), cancel=cancel)
        except OSError:
            raise ImageProviderError('io_error', 'Recovery journal unavailable') from None
        except (ValueError, RecursionError):
            raise ImageProviderError('io_error', 'Recovery journal invalid') from None
