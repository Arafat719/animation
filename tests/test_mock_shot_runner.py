import subprocess
import sys

import pytest
from pydantic import ValidationError

from animation_studio.pipeline.mock_shot_runner import MockShotExecutor, MockShotRunner
from animation_studio.providers.planner import MockPlanner, PlannerRequest


class RecordingExecutor(MockShotExecutor):
    def __init__(self, fail_shot_id=None):
        super().__init__(fail_shot_id)
        self.calls = []

    def execute(self, shot):
        self.calls.append(shot.id)
        super().execute(shot)


def setup(tmp_path, **kwargs):
    runner = MockShotRunner(tmp_path / 'plan.json', **kwargs)
    plan = MockPlanner().plan(PlannerRequest(prompt='নদীর ধারে'))
    runner.create(plan)
    return runner, plan


def test_failed_shot_resumes_after_process_restart(tmp_path):
    runner, plan = setup(tmp_path)
    ids = [s.id for s in plan.shots]
    executor = RecordingExecutor(ids[2])
    failed = runner.run(executor)
    assert executor.calls == ids[:3]
    assert [s.status for s in failed.shots] == ['completed'] * 2 + ['failed'] + ['pending'] * 3
    assert failed.shots[2].error.code == 'mock_failure'
    completed = [s.model_dump_json() for s in failed.shots[:2]]
    code = """import sys
from pathlib import Path
from animation_studio.pipeline.mock_shot_runner import MockShotRunner, MockShotExecutor
class Trace(MockShotExecutor):
    def execute(self, shot):
        print(shot.id)
        super().execute(shot)
MockShotRunner(Path(sys.argv[1])).run(Trace(sys.argv[2]))
"""
    result = subprocess.run(
        [sys.executable, '-c', code, str(runner.checkpoint), ids[2]],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert result.stdout.splitlines() == ids[2:]
    resumed = runner.load()
    assert all(s.status == 'completed' for s in resumed.shots)
    assert [s.attempts for s in resumed.shots] == [1, 1, 2, 1, 1, 1]
    assert [s.model_dump_json() for s in resumed.shots[:2]] == completed
    assert resumed.shots[2].error is None
    executor = RecordingExecutor()
    assert runner.run(executor) == resumed
    assert executor.calls == []
    assert all(s.status == 'pending' for s in plan.shots)


def test_attempt_limit_stops_without_execution(tmp_path):
    runner, plan = setup(tmp_path, max_attempts=1)
    failed = runner.run(MockShotExecutor(plan.shots[1].id))
    executor = RecordingExecutor()
    assert runner.run(executor) == failed
    assert executor.calls == []


def test_cancelled_and_interrupted_checkpoints(tmp_path):
    runner, plan = setup(tmp_path)
    plan.shots[0].status = 'cancelled'
    runner._save(plan)
    executor = RecordingExecutor()
    assert runner.run(executor) == plan
    assert executor.calls == []
    plan.shots[0].status = 'running'
    runner._save(plan)
    with pytest.raises(ValueError, match='reconciliation'):
        runner.run(executor)
    assert executor.calls == []


def test_corrupt_checkpoint_and_existing_file_are_not_overwritten(tmp_path):
    runner, plan = setup(tmp_path)
    with pytest.raises(FileExistsError):
        runner.create(plan)
    runner.checkpoint.write_text('{broken', encoding='utf-8')
    with pytest.raises(ValidationError):
        runner.run()
    assert runner.checkpoint.read_text() == '{broken'


def test_save_failure_prevents_execution_and_preserves_snapshot(tmp_path, monkeypatch):
    runner, plan = setup(tmp_path)

    def fail_replace(*args):
        raise OSError('disk failure')

    monkeypatch.setattr('animation_studio.pipeline.mock_shot_runner.os.replace', fail_replace)
    executor = RecordingExecutor()
    with pytest.raises(OSError, match='disk failure'):
        runner.run(executor)
    assert executor.calls == []
    assert runner.load() == plan
    assert list(tmp_path.iterdir()) == [runner.checkpoint]


def test_unexpected_executor_failure_is_visible_and_blocks_blind_replay(tmp_path):
    runner, _ = setup(tmp_path)

    class Broken(MockShotExecutor):
        def execute(self, shot):
            raise RuntimeError('unexpected bug')

    with pytest.raises(RuntimeError, match='unexpected bug'):
        runner.run(Broken())
    assert runner.load().shots[0].status == 'running'
    with pytest.raises(ValueError, match='reconciliation'):
        runner.run()


@pytest.mark.parametrize('limit', [0, -1, True, 1.5, '2'])
def test_invalid_attempt_limit(tmp_path, limit):
    with pytest.raises(ValueError):
        MockShotRunner(tmp_path / 'plan.json', max_attempts=limit)


def test_create_rejects_previously_started_plan(tmp_path):
    plan = MockPlanner().plan(PlannerRequest(prompt='River'))
    plan.shots[0].attempts = 1
    runner = MockShotRunner(tmp_path / 'plan.json')
    with pytest.raises(ValueError, match='untouched'):
        runner.create(plan)
    assert not runner.checkpoint.exists()
