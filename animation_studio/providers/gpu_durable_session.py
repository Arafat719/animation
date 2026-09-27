"""Opt-in local session ownership. Recovery closes admission, never resumes it."""

import fcntl
import json
import os
from dataclasses import dataclass
from typing import Literal

from animation_studio.providers.gpu_attempts import (
    CleanupObservation,
    DurableSessionRecord,
    LedgerConflict,
    _digest,
    _identifier,
    _Render,
    _State,
)
from animation_studio.providers.gpu_lifecycle import CleanupResult, ResourceState
from animation_studio.providers.gpu_mock_session import MockRenderSession, MockSessionClosed


@dataclass(frozen=True)
class ObservedCleanupResult(CleanupResult):
    # state/complete describe the observation only, never verified live state.
    source: Literal['current_call', 'saved', 'unknown'] = 'unknown'
    observed_attempt: int | None = None
    live_state_verified: Literal[False] = False


class DurableMockRenderSession(MockRenderSession):
    """Use create/recover and a context manager (or release).

    One owner per ledger, deliberately stricter than one per render. Lock order:
    lifetime owner lease, then short ledger mutation lock. Never unlink either.
    Legacy used renders cannot be enrolled. Standalone APIs remain outside this guard.
    """

    @classmethod
    def create(cls, *args, **kwargs):
        return cls(*args, **kwargs, recovering=False)

    @classmethod
    def recover(cls, *args, **kwargs):
        return cls(*args, **kwargs, recovering=True)

    def __init__(
        self, provider, backend, ledger, workload, config, *, render_id, clock, recovering
    ):
        self._lease = None
        self._record = None
        self._key = _identifier(render_id)
        # Validate exact mock inputs/config before opening ownership files.
        # Recovery ignores the new clock: old monotonic values are audit-only.
        super().__init__(
            provider,
            backend,
            ledger,
            workload,
            config,
            render_id=render_id,
            clock=(lambda: 0.0) if recovering else clock,
        )
        self._clock = clock
        identity = _digest(
            json.dumps(
                {
                    'workload': self._work.model_dump(mode='json'),
                    'config': self._config.model_dump(mode='json'),
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=False,
            )
        )
        fd = os.open(
            str(ledger.path) + '.owner.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lease = fd
            with ledger._locked():
                state = self._read()
                records = state.sessions or {}
                previous = records.get(self._key)
                if recovering:
                    if previous is None:
                        raise ValueError('No durable session to recover')
                    if previous.identity != identity or previous.pod_id != backend.state.pod_id:
                        raise LedgerConflict('Session identity mismatch')
                    self._record = previous
                    self._controller.deadline = previous.deadline
                    self._controller.closed = True
                else:
                    if self._key in state.renders:
                        raise LedgerConflict('Existing or legacy render cannot start a new session')
                    record = DurableSessionRecord(
                        identity=identity,
                        pod_id=backend.state.pod_id,
                        started_at=float(self._controller._last),
                        deadline=self.deadline,
                    )
                    state.renders[self._key] = _Render(
                        identity=identity,
                        limits={_digest(shot.shot_id): shot.attempts for shot in self._work.shots},
                    )
                    records[self._key] = record
                    ledger._write(state.model_copy(update={'sessions': records}))
                    self._record = record
            if recovering:
                self.cleanup_result = self._cleanup()
        except BaseException:
            os.close(fd)
            self._lease = None
            self._controller.closed = True
            raise

    def _read(self):
        fd = os.open(self._ledger.path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'r') as stream:
            return _State.model_validate_json(stream.read())

    def _owned(self):
        if self._lease is None:
            raise MockSessionClosed('Session ownership released')

    def _cleanup(self):
        self._owned()
        self._controller.closed = True  # Remains closed even if persistence fails.
        with self._ledger._locked():
            state = self._read()
            record = (state.sessions or {}).get(self._key)
            if record is None or record != self._record:
                raise LedgerConflict('Durable session changed or missing')
            observation = record.observation
            if observation is not None and (
                observation.compute == 'absent'
                or 'unauthorized' in observation.provider_codes
                or record.cleanup_attempts >= 3
            ):
                return ObservedCleanupResult(
                    ResourceState(record.pod_id, observation.compute, observation.storage),
                    observation.errors,
                    observation.provider_codes,
                    'saved',
                    observation.attempt,
                )
            if record.cleanup_attempts >= 3:
                return ObservedCleanupResult(ResourceState(record.pod_id, 'unknown', 'unknown'), ())
            pending = record.model_copy(
                update={
                    'closed': True,
                    'cleanup_attempts': record.cleanup_attempts + 1,
                    'observation': None,
                }
            )
            state.sessions[self._key] = pending
            self._ledger._write(state)
            self._record = pending
        result = self._controller.cleanup()
        observation = CleanupObservation(
            pod_id=result.state.pod_id,
            attempt=pending.cleanup_attempts,
            compute=result.state.compute,
            storage=result.state.storage,
            errors=result.errors,
            provider_codes=result.provider_codes,
        )
        with self._ledger._locked():
            state = self._read()
            if (state.sessions or {}).get(self._key) != pending:
                raise LedgerConflict('Cleanup intent changed before observation write')
            final = pending.model_copy(update={'observation': observation})
            state.sessions[self._key] = final
            self._ledger._write(state)
            self._record = final
        return ObservedCleanupResult(
            result.state,
            result.errors,
            result.provider_codes,
            'current_call',
            observation.attempt,
        )

    def tick(self):
        self._owned()
        if self.closed:
            return self.cleanup_result
        now = self._clock()
        # Controller validates the clock without invoking cleanup before durable intent.
        import math

        if (
            isinstance(now, bool)
            or not isinstance(now, (int, float))
            or not math.isfinite(now)
            or now < self._controller._last
        ):
            raise ValueError('Clock must be finite and monotonic')
        if now >= self.deadline:
            self.cleanup_result = self._cleanup()
            return self.cleanup_result
        return self._controller.tick(now)

    def finish(self):
        self._owned()
        if not self.closed:
            self.cleanup_result = self._cleanup()
        return self.cleanup_result

    def fail(self):
        return self.finish()

    def release(self):
        if self._lease is not None:
            self._controller.closed = True
            os.close(self._lease)
            self._lease = None

    def __enter__(self):
        self._owned()
        return self

    def __exit__(self, *exc):
        try:
            self.finish()
        finally:
            self.release()
