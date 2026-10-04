"""Linux-local v2 mock journal storage; no executor or network integration."""

import fcntl
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from threading import get_ident

from animation_studio.providers.comfy_identity import (
    MAX_RECORD_BYTES,
    ComfyExecutionContext,
    ComfyJobRecordV2,
    match_job_context,
)


class ComfyJournalStore:
    """One deterministic path per job in a caller-owned private existing root.

    Hold locked() across the future preflight/submit/receipt transaction. Cooperating
    callers must share this root and never unlink the permanent lock file. Root
    ancestors must be trusted; this is not protection against a malicious owner.
    """

    def __init__(self, root: Path, context: ComfyExecutionContext):
        if type(context) is not ComfyExecutionContext:
            raise ValueError('Expected execution context')
        self._context = ComfyExecutionContext.model_validate(context.model_dump())
        if self._context.mode != 'mock':
            raise ValueError('Only mock journal storage is enabled')
        self._root = Path(root).absolute()
        self._active = None

    @property
    def path(self):
        return self._root / f'{self._context.job_id}.json'

    @contextmanager
    def locked(self):
        if self._active:
            raise RuntimeError('Journal lock already held')
        root_stat = self._root.lstat()
        if not stat.S_ISDIR(root_stat.st_mode) or root_stat.st_uid != os.getuid():
            raise ValueError('Expected an owned journal directory')
        if root_stat.st_mode & 0o077:
            raise ValueError('Journal directory must be private')
        fd = os.open(str(self.path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError('Invalid journal lock')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._active = get_ident()
            try:
                yield self
            finally:
                self._active = None
        finally:
            os.close(fd)

    def _require_lock(self):
        if self._active != get_ident():
            raise RuntimeError('Journal operation requires locked()')

    def read(self) -> ComfyJobRecordV2:
        self._require_lock()
        fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('Invalid journal file')
            content = stream.read(MAX_RECORD_BYTES + 1)
        return match_job_context(content, self._context)

    def create_intent(self) -> ComfyJobRecordV2:
        self._require_lock()
        if os.path.lexists(self.path):
            raise ValueError('Journal exists; submission must not be retried')
        record = ComfyJobRecordV2(**self._context.model_dump(), schema_version=2, state='intent')
        self._write(record)
        return record

    def accept(self, prompt_id: str) -> ComfyJobRecordV2:
        self._require_lock()
        current = self.read()
        if current.state != 'intent':
            raise ValueError('Journal already accepted')
        record = ComfyJobRecordV2(
            **self._context.model_dump(), schema_version=2, state='accepted', prompt_id=prompt_id
        )
        self._write(record)
        return record

    def _write(self, record):
        self._require_lock()
        content = record.model_dump_json().encode('utf-8')
        if len(content) > MAX_RECORD_BYTES:
            raise ValueError('Journal too large')
        match_job_context(content, self._context)
        fd, name = tempfile.mkstemp(prefix='.comfy-v2-', dir=self._root)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
            directory = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.lexists(name):
                os.unlink(name)
