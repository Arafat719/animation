"""Transactional revision/approval boundary for local mock plan execution."""

import sqlite3
from contextlib import closing

from pydantic import BaseModel, ConfigDict, Field

from animation_studio.domain.pipeline_state import transition_shot
from animation_studio.domain.v1.story_plan import StoryPlan
from animation_studio.pipeline.mock_shot_runner import MockShotExecutor


class PlanVersion(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    revision: int = Field(ge=0)


class SavePlan(PlanVersion):
    plan: StoryPlan


class PlanView(PlanVersion):
    plan: StoryPlan | None
    approved: bool = False
    result: StoryPlan | None = None


class PlanConflict(ValueError):
    pass


class PlanStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @staticmethod
    def _view(row):
        return PlanView(
            revision=row['revision'],
            plan=StoryPlan.model_validate_json(row['plan_json']),
            approved=bool(row['approved']),
            result=StoryPlan.model_validate_json(row['result_json'])
            if row['result_json']
            else None,
        )

    def read(self, project_id: int) -> PlanView | None:
        with closing(sqlite3.connect(self.db_path)) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                'SELECT * FROM project_plans WHERE project_id=?', (project_id,)
            ).fetchone()
            return self._view(row) if row else None

    def update(
        self, project_id: int, revision: int, action: str, plan: StoryPlan | None = None
    ) -> PlanView:
        with closing(sqlite3.connect(self.db_path, timeout=30)) as db, db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT id FROM projects WHERE id=?', (project_id,)).fetchone():
                raise LookupError('Project not found')
            row = db.execute(
                'SELECT * FROM project_plans WHERE project_id=?', (project_id,)
            ).fetchone()
            if revision != (row['revision'] if row else 0):
                raise PlanConflict('Plan changed. Reload before continuing.')
            if action == 'save':
                if plan is None:
                    raise ValueError('Plan required')
                plan = StoryPlan.model_validate(plan.model_dump())
                if any(
                    s.status != 'pending'
                    or s.attempts
                    or s.error
                    or s.keyframe_path
                    or s.raw_clip_path
                    or s.lip_synced_clip_path
                    for s in plan.shots
                ):
                    raise PlanConflict('Save a pending plan without execution results.')
                db.execute(
                    """INSERT INTO project_plans(project_id,revision,plan_json,approved)
                    VALUES(?,?,?,0) ON CONFLICT(project_id) DO UPDATE SET
                    revision=excluded.revision,plan_json=excluded.plan_json,approved=0,result_json=NULL""",
                    (project_id, revision + 1, plan.model_dump_json()),
                )
            elif action == 'approve':
                if row is None:
                    raise PlanConflict('Save the plan before approval.')
                db.execute('UPDATE project_plans SET approved=1 WHERE project_id=?', (project_id,))
            elif action == 'run':
                if row is None or not row['approved']:
                    raise PlanConflict('Approve the saved plan before mock rendering.')
                if not row['result_json']:
                    result = StoryPlan.model_validate_json(row['plan_json'])
                    executor = MockShotExecutor()
                    for shot_id in [s.id for s in result.shots]:
                        result = transition_shot(result, shot_id, 'running')
                        executor.execute(next(s for s in result.shots if s.id == shot_id))
                        result = transition_shot(result, shot_id, 'completed')
                    db.execute(
                        'UPDATE project_plans SET result_json=? WHERE project_id=?',
                        (result.model_dump_json(), project_id),
                    )
            else:
                raise ValueError('Unknown plan action')
            return self._view(
                db.execute(
                    'SELECT * FROM project_plans WHERE project_id=?', (project_id,)
                ).fetchone()
            )
