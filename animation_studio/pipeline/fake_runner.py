"""Run one explicitly queued fixture job; no thread pool or API side effects."""

import sqlite3
from threading import Event
from typing import Callable, Protocol

from pydantic import ValidationError

from animation_studio.persistence.job_results import Outcome, SavedOutcome, StoredError, UnknownJobError
from animation_studio.persistence.runner_store import JobNotRunnableError, RunnerStore, cancelled_outcome
from animation_studio.providers.fake import FakeProvider, FakeRequest, FakeResult, ProgressEvent, ProviderError


class FixtureProvider(Protocol):
    def generate(self, request: FakeRequest, *, cancel: Event,
                 on_progress: Callable[[ProgressEvent], None]) -> FakeResult: ...


class FakeJobRunner:
    def __init__(self, db_path: str, provider: FixtureProvider | None = None):
        self.store = RunnerStore(db_path)
        self.provider = provider if provider is not None else FakeProvider()

    def run(self, job_id: int, *, seed: int = 0, timeout_seconds: float = 10,
            cancel: Event | None = None) -> SavedOutcome:
        claimed = self.store.claim(job_id)
        if isinstance(claimed, SavedOutcome):
            return claimed
        cancel = cancel if cancel is not None else Event()

        def report(event: ProgressEvent):
            event = ProgressEvent.model_validate(event.model_dump(warnings=False))
            self.store.progress(job_id, event)

        if cancel.is_set():
            return self.store.finish(job_id, cancelled_outcome(), cancel)
        try:
            request = FakeRequest(prompt=claimed, seed=seed, timeout_seconds=timeout_seconds)
        except ValidationError:
            return self.store.finish(job_id, Outcome(error=StoredError(
                code='invalid_input', message='A valid saved prompt, seed and timeout are required',
            )), cancel)
        try:
            result = self.provider.generate(request, cancel=cancel, on_progress=report)
            # Revalidation still rejects malformed output. Serializer warnings
            # would otherwise print its raw values to stderr before rejection.
            outcome = Outcome(result=result.model_dump(warnings=False))
        except (sqlite3.Error, JobNotRunnableError, UnknownJobError):
            # Persistence/state failures must remain visible to the caller.
            raise
        except ProviderError as error:
            outcome = Outcome(error=StoredError(code=error.code, message=str(error).strip()[:2000] or 'Provider failed'))
        except Exception as error:
            outcome = Outcome(error=StoredError(
                code='provider_error', message=f'{type(error).__name__}: {error}'[:2000],
            ))
        return self.store.finish(job_id, outcome, cancel)
