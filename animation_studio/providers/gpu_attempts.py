"""Local Linux attempt reservations only; no provider dispatch or spending authority."""

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from animation_studio.providers.gpu import ErrorCode
from animation_studio.providers.gpu_budget import (
    BudgetConfig,
    BudgetExceeded,
    RenderWorkload,
    estimate_render,
)

Digest = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]


class LedgerConflict(ValueError):
    """An identity was reused with a different workload, budget, or shot."""


class AttemptLimitExceeded(ValueError):
    """All planned attempts for this shot are already reserved."""


class _Record(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)


class MockSubmissionReceipt(_Record):
    """Historical mock acceptance only; never the current execution status."""

    provider: Literal['mock-gpu'] = 'mock-gpu'
    job_id: str = Field(pattern=r'^mock-gpu-[1-9][0-9]*$', max_length=100)
    outcome: Literal['submitted'] = 'submitted'


class Reservation(_Record):
    render_digest: Digest
    shot_digest: Digest
    attempt_digest: Digest
    ordinal: int = Field(ge=1, le=1000)
    receipt: MockSubmissionReceipt | None = None


class _Render(_Record):
    identity: Digest
    limits: dict[Digest, Annotated[int, Field(ge=1, le=1000)]] = Field(min_length=1)


class CleanupObservation(_Record):
    pod_id: str = Field(min_length=1, max_length=4000)
    attempt: int = Field(ge=1, le=3)
    compute: Literal['running', 'stopped', 'absent', 'unknown']
    storage: Literal['none', 'retained', 'unknown']
    errors: tuple[Literal['inspect_failed', 'stop_failed', 'terminate_failed'], ...]
    provider_codes: tuple[ErrorCode, ...]


class DurableSessionRecord(_Record):
    identity: Digest
    pod_id: str = Field(min_length=1, max_length=4000)
    started_at: float = Field(ge=0, allow_inf_nan=False)
    deadline: float = Field(gt=0, allow_inf_nan=False)
    closed: bool = False
    cleanup_attempts: int = Field(ge=0, le=3, default=0)
    observation: CleanupObservation | None = None

    @model_validator(mode='after')
    def coherent(self):
        if self.deadline <= self.started_at or (self.cleanup_attempts and not self.closed):
            raise ValueError('Invalid durable session state')
        if self.observation is not None and (
            not self.closed
            or self.observation.pod_id != self.pod_id
            or self.observation.attempt != self.cleanup_attempts
        ):
            raise ValueError('Invalid cleanup observation association')
        return self


class SessionReport(DurableSessionRecord):
    """Historical snapshot only; closed and monotonic times are persisted audit data.

    No owner liveness, remaining time, spending or submission authority is implied.
    complete describes the saved observation, never current cleanup or billing.
    """

    @property
    def source(self) -> Literal['saved', 'unknown']:
        return 'saved' if self.observation is not None else 'unknown'

    @property
    def live_state_verified(self) -> Literal[False]:
        return False

    @property
    def compute(self) -> Literal['running', 'stopped', 'absent', 'unknown']:
        return self.observation.compute if self.observation is not None else 'unknown'

    @property
    def storage(self) -> Literal['none', 'retained', 'unknown']:
        return self.observation.storage if self.observation is not None else 'unknown'

    @property
    def complete(self) -> bool:
        return self.compute == 'absent' and self.storage == 'none'


class _State(_Record):
    schema_version: Literal[1]
    renders: dict[Digest, _Render]
    reservations: dict[Digest, Reservation]
    sessions: dict[Digest, DurableSessionRecord] | None = None

    @model_validator(mode='after')
    def coherent(self):
        if type(self.schema_version) is not int:
            raise ValueError('Invalid ledger version')
        for key, session in (self.sessions or {}).items():
            if key not in self.renders or self.renders[key].identity != session.identity:
                raise ValueError('Session render identity mismatch')
        counts: dict[tuple[str, str], list[int]] = {}
        for key, reservation in self.reservations.items():
            render = self.renders.get(reservation.render_digest)
            if key != reservation.attempt_digest or render is None:
                raise ValueError('Invalid reservation identity')
            limit = render.limits.get(reservation.shot_digest)
            if limit is None or reservation.ordinal > limit:
                raise ValueError('Invalid reservation limit')
            pair = (reservation.render_digest, reservation.shot_digest)
            counts.setdefault(pair, []).append(reservation.ordinal)
        for ordinals in counts.values():
            if sorted(ordinals) != list(range(1, len(ordinals) + 1)):
                raise ValueError('Invalid reservation sequence')
        return self


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
        raise ValueError('Expected a nonempty bounded identifier')
    return _digest(value)


class LocalAttemptLedger:
    """Use a private existing directory on a local Linux filesystem.

    initialize() explicitly creates a fresh ledger. Missing/corrupt existing state
    never resets automatically. Keep the ledger and its persistent lock together;
    deletion, copying or switching paths/IDs can bypass this local accounting.
    Each reserve is permanent, including after a crash. A returned reservation,
    whether new or replayed, is NOT permission to submit or retry a provider job.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def _locked(self):
        fd = os.open(str(self.path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            # Fail fast on contention; callers may retry the same reservation key.
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def _write(self, state: _State):
        fd, name = tempfile.mkstemp(prefix='.gpu-attempts-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(state.model_dump_json(exclude_none=True))
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

    def initialize(self):
        with self._locked():
            if self.path.exists() or self.path.is_symlink():
                raise FileExistsError('Ledger already exists')
            self._write(_State(schema_version=1, renders={}, reservations={}))

    def session_report(self, *, render_id: str) -> SessionReport | None:
        """Read one validated atomic snapshot, without locks, writes or cleanup.

        None means no durable session (including legacy renders). Missing/corrupt
        ledgers raise. Concurrent replacement may leave this snapshot stale.
        """
        key = _identifier(render_id)
        fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'r') as stream:
            state = _State.model_validate_json(stream.read())
        record = (state.sessions or {}).get(key)
        return None if record is None else SessionReport.model_validate(record.model_dump())

    def lookup(self, *, render_id: str, shot_id: str, attempt_key: str) -> Reservation | None:
        """Read an atomic snapshot without writes or provider calls.

        None means not reserved; receipt=None means submission outcome unknown.
        A receipt proves historical mock acceptance, not job completion/liveness.
        Missing/corrupt files raise; they are never interpreted as an empty ledger.
        """
        render_key, shot_key, key = map(_identifier, (render_id, shot_id, attempt_key))
        fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'r') as stream:
            state = _State.model_validate_json(stream.read())
        result = state.reservations.get(key)
        if result is not None and (result.render_digest, result.shot_digest) != (
            render_key,
            shot_key,
        ):
            raise LedgerConflict('Attempt key belongs to another render or shot')
        return result

    def _record_mock_receipt(self, reservation: Reservation, receipt: MockSubmissionReceipt):
        receipt = MockSubmissionReceipt.model_validate(receipt.model_dump())
        with self._locked():
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'r') as stream:
                state = _State.model_validate_json(stream.read())
            current = state.reservations.get(reservation.attempt_digest)
            if current is None or current.model_copy(update={'receipt': None}) != reservation:
                raise LedgerConflict('Reservation does not match receipt target')
            if current.receipt is not None:
                if current.receipt != receipt:
                    raise LedgerConflict('Receipt cannot be replaced')
                return
            state.reservations[reservation.attempt_digest] = current.model_copy(
                update={'receipt': receipt}
            )
            self._write(state)

    def reserve(
        self,
        workload: RenderWorkload,
        config: BudgetConfig,
        *,
        render_id: str,
        shot_id: str,
        attempt_key: str,
    ) -> Reservation:
        reservation, _ = self._reserve_once(
            workload, config, render_id=render_id, shot_id=shot_id, attempt_key=attempt_key
        )
        return reservation

    def _reserve_once(
        self,
        workload: RenderWorkload,
        config: BudgetConfig,
        *,
        render_id: str,
        shot_id: str,
        attempt_key: str,
    ) -> tuple[Reservation, bool]:
        """Return freshness under the same lock as the durable write.

        Only the current caller receiving True may perform the mock dispatch.
        Existing reservations, including ledger-only ones, cannot be dispatched.
        """
        workload = RenderWorkload.model_validate(workload.model_dump())
        config = BudgetConfig.model_validate(config.model_dump())
        estimate = estimate_render(workload, config)
        if not estimate.allowed:
            raise BudgetExceeded(estimate)
        if not any(shot.shot_id == shot_id for shot in workload.shots):
            raise ValueError('Shot is not part of the estimated render')
        render_key, shot_key, key = map(_identifier, (render_id, shot_id, attempt_key))
        identity = _digest(
            json.dumps(
                {
                    'workload': workload.model_dump(mode='json'),
                    'config': config.model_dump(mode='json'),
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=False,
            )
        )
        with self._locked():
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'r') as stream:
                state = _State.model_validate_json(stream.read())
            render = state.renders.get(render_key)
            if render is not None and render.identity != identity:
                raise LedgerConflict('Render workload or budget changed')
            previous = state.reservations.get(key)
            if previous is not None:
                if (previous.render_digest, previous.shot_digest) != (render_key, shot_key):
                    raise LedgerConflict('Attempt key belongs to another render or shot')
                return previous, False
            if render is None:
                render = _Render(
                    identity=identity,
                    limits={_digest(shot.shot_id): shot.attempts for shot in workload.shots},
                )
                state.renders[render_key] = render
            count = sum(
                r.render_digest == render_key and r.shot_digest == shot_key
                for r in state.reservations.values()
            )
            if count >= render.limits[shot_key]:
                raise AttemptLimitExceeded('Shot attempt allowance exhausted')
            result = Reservation(
                render_digest=render_key,
                shot_digest=shot_key,
                attempt_digest=key,
                ordinal=count + 1,
            )
            state.reservations[key] = result
            self._write(state)
            return result, True
