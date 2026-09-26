"""Single-writer, local dry-run execution with durable StoryPlan checkpoints.

One mock execution step per shot; no media or external provider is invoked.
A running checkpoint after interruption requires reconciliation, not blind replay.
"""

import os
from pathlib import Path
import tempfile

from animation_studio.domain.pipeline_state import transition_shot
from animation_studio.domain.v1.story_plan import ShotError, ShotPlan, StoryPlan


class MockShotFailure(RuntimeError):
    pass


class MockShotExecutor:
    """Fail the selected shot on its first attempt, then succeed without media."""

    def __init__(self, fail_shot_id: str | None = None):
        self.fail_shot_id = fail_shot_id

    def execute(self, shot: ShotPlan) -> None:
        if shot.id == self.fail_shot_id and shot.attempts == 1:
            raise MockShotFailure('Deliberate mock shot failure')


class MockShotRunner:
    """Caller owns exclusive access to the checkpoint for the entire run.

    No automatic retry: run again explicitly after a saved failure. max_attempts
    counts the initial attempt. Checkpoint I/O failures propagate to the caller.
    """

    def __init__(self, checkpoint: Path, *, max_attempts: int = 2):
        if type(max_attempts) is not int or max_attempts < 1:
            raise ValueError('max_attempts must be a positive integer')
        self.checkpoint = Path(checkpoint)
        self.max_attempts = max_attempts

    def create(self, plan: StoryPlan) -> None:
        plan = StoryPlan.model_validate(plan.model_dump(warnings=False))
        if any(s.status != 'pending' or s.attempts or s.error for s in plan.shots):
            raise ValueError('A new mock run requires an untouched pending plan')
        # Exclusive creation never overwrites an existing run.
        with self.checkpoint.open('x', encoding='utf-8') as stream:
            stream.write(plan.model_dump_json())
            stream.flush()
            os.fsync(stream.fileno())

    def load(self) -> StoryPlan:
        return StoryPlan.model_validate_json(self.checkpoint.read_text(encoding='utf-8'))

    def _save(self, plan: StoryPlan) -> None:
        payload = StoryPlan.model_validate(plan.model_dump()).model_dump_json()
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=self.checkpoint.parent, delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.checkpoint)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def run(self, executor: MockShotExecutor | None = None) -> StoryPlan:
        plan = self.load()
        if any(s.status == 'running' for s in plan.shots):
            raise ValueError('Interrupted running shot requires reconciliation before resume')
        executor = executor if executor is not None else MockShotExecutor()
        for index in range(len(plan.shots)):
            shot = plan.shots[index]
            if shot.status == 'completed':
                continue
            if shot.status == 'cancelled' or shot.attempts >= self.max_attempts:
                return plan
            plan = transition_shot(plan, shot.id, 'running')
            self._save(plan)
            try:
                executor.execute(plan.shots[index].model_copy(deep=True))
            except MockShotFailure as error:
                plan = transition_shot(
                    plan,
                    shot.id,
                    'failed',
                    error=ShotError(
                        code='mock_failure', message=str(error)[:4000] or 'Mock failed'
                    ),
                )
                self._save(plan)
                return plan
            # Unexpected bugs remain visible; the saved running state prevents
            # unreviewed replay when the outcome is unknown.
            plan = transition_shot(plan, shot.id, 'completed')
            self._save(plan)
        return plan
