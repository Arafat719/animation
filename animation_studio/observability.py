"""Allowlisted pipeline events and application-scoped JSON stderr logging."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import RLock
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


EventName = Literal[
    'job_queued', 'job_started', 'job_progress', 'job_completed', 'job_failed',
    'job_cancelled', 'job_cancel_requested', 'job_reused', 'job_transition_error', 'job_dispatch_error',
    'job_worker_error', 'unstructured_log',
]
Step = Literal[
    'queued', 'started', 'image', 'audio', 'video', 'completed', 'failed',
    'cancelled', 'claim', 'finish', 'dispatch', 'unknown',
]
State = Literal['queued', 'running', 'completed', 'failed', 'cancelled']
ErrorCode = Literal[
    'invalid_input', 'fixture_missing', 'fixture_invalid', 'dependency_missing',
    'io_error', 'cancelled', 'timeout', 'provider_error', 'storage_error',
    'state_error', 'data_error', 'internal_error',
]


class PipelineEvent(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    event: EventName
    job_id: int | None = Field(default=None, gt=0)
    project_id: int | None = Field(default=None, gt=0)
    shot_id: int | None = Field(default=None, ge=0)
    step: Step
    state: State | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    error_code: ErrorCode | None = None


logger = logging.getLogger('animation_studio.pipeline')


def failure_code(error: Exception) -> ErrorCode:
    if isinstance(error, sqlite3.Error):
        return 'storage_error'
    if isinstance(error, ValidationError):
        return 'data_error'
    if isinstance(error, LookupError):
        return 'state_error'
    return 'internal_error'


def emit_event(event: EventName, *, job_id: int | None, project_id: int | None,
               shot_id: int | None, step: Step, state: State | None = None,
               progress: int | None = None, error_code: ErrorCode | None = None):
    # Never stringify provider errors, prompts, paths or arbitrary context.
    # Logging is best-effort and must not turn a committed job into a failure.
    try:
        payload = PipelineEvent(
            event=event, job_id=job_id, project_id=project_id, shot_id=shot_id,
            step=step, state=state, progress=progress, error_code=error_code,
        )
        level = logging.ERROR if event in {
            'job_failed', 'job_transition_error', 'job_dispatch_error', 'job_worker_error',
        } else logging.INFO
        logger.log(level, event, extra=payload.model_dump())
    except Exception:
        # Includes malformed diagnostic fields and a broken custom log sink.
        # Do not recursively log an exception which may itself contain secrets.
        return


class PipelineJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
            event = PipelineEvent.model_validate({
                field: getattr(record, field, None) for field in PipelineEvent.model_fields
            })
        except ValidationError:
            # Accidental conventional logging in this namespace still cannot
            # print arbitrary messages, exception text, stack traces or extras.
            event = PipelineEvent(event='unstructured_log', step='unknown')
        payload = event.model_dump()
        payload.update(
            schema_version=1,
            timestamp=datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec='milliseconds'),
            level=logging.getLevelName(record.levelno),
        )
        return json.dumps(payload, ensure_ascii=False, separators=(',', ':'))


class PipelineStreamHandler(logging.StreamHandler):
    def handleError(self, record):
        # The standard handler prints raw exception text to stderr on sink
        # failure. Keep our best-effort sink quiet without changing global policy.
        pass


_configuration_lock = RLock()
_users = 0
_handler = None
_previous = None


@contextmanager
def pipeline_logging(stream=None):
    """Configure only our logger during API lifetime; nested users share one sink.

    Existing handlers/root/Uvicorn configuration are preserved. The first active
    caller chooses the stream (stderr by default), and the last restores settings.
    """
    global _users, _handler, _previous
    with _configuration_lock:
        if _users == 0:
            _previous = (logger.level, logger.propagate)
            _handler = PipelineStreamHandler(stream)
            _handler.setFormatter(PipelineJsonFormatter())
            logger.addHandler(_handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
        _users += 1
    try:
        yield
    finally:
        with _configuration_lock:
            _users -= 1
            if _users == 0:
                logger.removeHandler(_handler)
                _handler.close()
                logger.setLevel(_previous[0])
                logger.propagate = _previous[1]
                _handler = _previous = None
