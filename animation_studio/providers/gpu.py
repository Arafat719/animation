"""Vendor-neutral job boundary; the local mock performs no inference or I/O."""

from threading import Lock
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=4000)]
ErrorCode = Literal[
    'invalid_input',
    'not_found',
    'unsupported',
    'timeout',
    'unavailable',
    'unauthorized',
    'idempotency_conflict',
    'invalid_response',
]


class GPUProviderError(Exception):
    def __init__(self, code: ErrorCode, message: str):
        self.code = code
        super().__init__(message)


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, str_strip_whitespace=True)


class GPUHealth(Contract):
    healthy: bool
    provider_name: Text
    provider_version: Text


class GPUCapabilities(Contract):
    operations: tuple[Text, ...]


class GPUJobRequest(Contract):
    operation: Text
    prompt: Text
    model_name: Text
    model_version: Text
    seed: int = Field(default=0, ge=0, le=2**32 - 1, strict=True)


class GPUJob(Contract):
    job_id: Text
    status: Literal['queued', 'running', 'succeeded', 'failed', 'cancelled']
    progress: int = Field(ge=0, le=100, strict=True)
    request: GPUJobRequest
    error_code: Text | None = None

    @model_validator(mode='after')
    def coherent_status(self):
        if (self.status == 'failed') != (self.error_code is not None):
            raise ValueError('Only failed jobs must include an error code')
        if self.status == 'succeeded' and self.progress != 100:
            raise ValueError('Successful jobs must have progress 100')
        if self.status == 'queued' and self.progress != 0:
            raise ValueError('Queued jobs must have progress 0')
        if self.status != 'succeeded' and self.progress == 100:
            raise ValueError('Only successful jobs may have progress 100')
        return self


class GPUProvider(Protocol):
    """Synchronous calls, intended for workers, with positive finite call deadlines.

    Requests are validated models. Transport errors raise GPUProviderError; job
    failures are snapshots. Unknown IDs raise not_found. Status is read-only;
    cancel is repeatable and preserves terminal jobs. Results retain the submitted
    model/version/seed. Artifact delivery and compute/storage lifecycle are later
    contracts; job success alone is not evidence of verified media.
    """

    def health_check(self, *, timeout_seconds: float = 10) -> GPUHealth: ...
    def capabilities(self, *, timeout_seconds: float = 10) -> GPUCapabilities: ...
    def submit(self, request: GPUJobRequest, *, timeout_seconds: float = 10) -> GPUJob: ...
    def status(self, job_id: str, *, timeout_seconds: float = 10) -> GPUJob: ...
    def cancel(self, job_id: str, *, timeout_seconds: float = 10) -> GPUJob: ...


class MockGPUProvider:
    """In-memory mock; advance() explicitly simulates work, never generates media.

    Only mock.noop with mock-worker/1 is supported. No implicit polling progress,
    persistence, retry or idempotency. A new submission always creates a new job.
    """

    def __init__(self):
        self._jobs: dict[str, GPUJob] = {}
        self._lock = Lock()

    @staticmethod
    def _deadline(timeout_seconds: float):
        import math

        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise GPUProviderError('invalid_input', 'Timeout must be positive and finite')
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise GPUProviderError('invalid_input', 'Timeout must be positive and finite')

    def health_check(self, *, timeout_seconds: float = 10) -> GPUHealth:
        self._deadline(timeout_seconds)
        return GPUHealth(healthy=True, provider_name='mock-gpu', provider_version='1')

    def capabilities(self, *, timeout_seconds: float = 10) -> GPUCapabilities:
        self._deadline(timeout_seconds)
        return GPUCapabilities(operations=('mock.noop',))

    def submit(self, request: GPUJobRequest, *, timeout_seconds: float = 10) -> GPUJob:
        self._deadline(timeout_seconds)
        if not isinstance(request, GPUJobRequest):
            raise GPUProviderError('invalid_input', 'Expected GPUJobRequest')
        if (request.operation, request.model_name, request.model_version) != (
            'mock.noop',
            'mock-worker',
            '1',
        ):
            raise GPUProviderError('unsupported', 'Unsupported operation or model')
        with self._lock:
            job = GPUJob(
                job_id=f'mock-gpu-{len(self._jobs) + 1}',
                status='queued',
                progress=0,
                request=request,
            )
            self._jobs[job.job_id] = job
            return job

    def _get(self, job_id: str) -> GPUJob:
        try:
            return self._jobs[job_id]
        except KeyError:
            raise GPUProviderError('not_found', 'Unknown GPU job') from None

    def status(self, job_id: str, *, timeout_seconds: float = 10) -> GPUJob:
        self._deadline(timeout_seconds)
        with self._lock:
            return self._get(job_id)

    def cancel(self, job_id: str, *, timeout_seconds: float = 10) -> GPUJob:
        self._deadline(timeout_seconds)
        with self._lock:
            job = self._get(job_id)
            if job.status in ('queued', 'running'):
                job = GPUJob(**{**job.model_dump(), 'status': 'cancelled'})
                self._jobs[job_id] = job
            return job

    def advance(self, job_id: str, *, fail: bool = False) -> GPUJob:
        """Test control outside GPUProvider: queued → running → succeeded/failed."""
        with self._lock:
            job = self._get(job_id)
            if job.status in ('queued', 'running'):
                status = (
                    'failed' if fail else ('running' if job.status == 'queued' else 'succeeded')
                )
                progress = job.progress if fail else (50 if status == 'running' else 100)
                job = GPUJob(
                    **{
                        **job.model_dump(),
                        'status': status,
                        'progress': progress,
                        'error_code': 'mock_failure' if fail else None,
                    }
                )
                self._jobs[job_id] = job
            return job
