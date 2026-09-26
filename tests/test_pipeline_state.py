from itertools import product

import pytest
from pydantic import ValidationError

from animation_studio.domain.pipeline_state import (
    IllegalShotTransition,
    UnknownShotError,
    transition_shot,
)
from animation_studio.domain.v1.story_plan import ShotError, StoryPlan
from animation_studio.providers.planner import MockPlanner, PlannerRequest

STATUSES = ('pending', 'running', 'completed', 'failed', 'cancelled')
LEGAL = {
    ('pending', 'running'),
    ('pending', 'cancelled'),
    ('running', 'completed'),
    ('running', 'failed'),
    ('running', 'cancelled'),
    ('failed', 'running'),
    ('failed', 'cancelled'),
}


def plan():
    return MockPlanner().plan(PlannerRequest(prompt='নদীর ধারে'))


def failure():
    return ShotError(code='mock_failure', message='ইচ্ছাকৃত ব্যর্থতা')


@pytest.mark.parametrize(('source', 'target'), list(product(STATUSES, repeat=2)))
def test_complete_transition_matrix(source, target):
    original = plan()
    shot = original.shots[0]
    shot.status = source
    shot.attempts = 0 if source == 'pending' else 1
    shot.error = failure() if source == 'failed' else None
    before = original.model_dump_json()
    error = failure() if target == 'failed' else None
    if (source, target) not in LEGAL:
        with pytest.raises(IllegalShotTransition):
            transition_shot(original, shot.id, target, error=error)
    else:
        result = transition_shot(original, shot.id, target, error=error)
        changed = result.shots[0]
        assert changed.status == target
        assert changed.attempts == shot.attempts + (target == 'running')
        assert changed.error == error
        assert result.shots[1:] == original.shots[1:]
        assert StoryPlan.model_validate_json(result.model_dump_json()) == result
        assert changed.model_dump(exclude={'status', 'attempts', 'error'}) == shot.model_dump(
            exclude={'status', 'attempts', 'error'}
        )
    assert original.model_dump_json() == before


def test_retry_lifecycle_preserves_completed_shot_and_artifacts():
    current = plan()
    first, second = [s.id for s in current.shots[:2]]
    current = transition_shot(current, first, 'running')
    current.shots[0].keyframe_path = 'fixture/keyframe.png'
    current = transition_shot(current, first, 'completed')
    completed = current.shots[0].model_dump_json()
    current = transition_shot(current, second, 'running')
    error = failure()
    current = transition_shot(current, second, 'failed', error=error)
    error.message = 'Changed outside'
    assert current.shots[1].error.message == 'ইচ্ছাকৃত ব্যর্থতা'
    current = transition_shot(current, second, 'running')
    assert current.shots[1].attempts == 2
    assert current.shots[1].error is None
    current = transition_shot(current, second, 'completed')
    assert current.shots[0].model_dump_json() == completed
    with pytest.raises(IllegalShotTransition):
        transition_shot(current, first, 'running')


@pytest.mark.parametrize('target', ['running', 'completed', 'cancelled'])
def test_error_only_allowed_for_failure(target):
    current = plan()
    if target == 'completed':
        current = transition_shot(current, current.shots[0].id, 'running')
    with pytest.raises(ValueError, match='Only a failed'):
        transition_shot(current, current.shots[0].id, target, error=failure())


def test_failure_requires_valid_error_and_is_atomic():
    current = plan()
    current = transition_shot(current, current.shots[0].id, 'running')
    before = current.model_dump_json()
    with pytest.raises(ValueError, match='requires'):
        transition_shot(current, current.shots[0].id, 'failed')
    invalid = failure().model_copy(update={'code': ''})
    with pytest.raises(ValidationError):
        transition_shot(current, current.shots[0].id, 'failed', error=invalid)
    assert current.model_dump_json() == before


@pytest.mark.parametrize('target', ['unknown', '', None, True, []])
def test_invalid_target(target):
    current = plan()
    with pytest.raises(IllegalShotTransition):
        transition_shot(current, current.shots[0].id, target)


def test_unknown_shot_and_invalid_snapshot():
    current = plan()
    with pytest.raises(UnknownShotError):
        transition_shot(current, 'missing', 'running')
    current.shots[0].attempts = -1
    with pytest.raises(ValidationError):
        transition_shot(current, current.shots[0].id, 'running')


def test_independent_snapshot():
    original = plan()
    result = transition_shot(original, original.shots[0].id, 'running')
    result.shots[1].visible_character_ids.clear()
    result.characters[0].name = 'Changed'
    assert original == plan()
