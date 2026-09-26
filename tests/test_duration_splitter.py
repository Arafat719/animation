import hashlib
import json
import math

import pytest
from pydantic import ValidationError

from animation_studio.domain.duration import split_duration
from animation_studio.domain.v1.story_plan import StoryPlan
from animation_studio.providers.planner import MockPlanner, PlannerRequest


def test_every_millisecond_in_supported_range():
    for milliseconds in range(30000, 60001):
        total = milliseconds / 1000
        durations = split_duration(total)
        assert 6 <= len(durations) <= 10
        assert all(3 <= duration <= 6 for duration in durations)
        assert math.isclose(math.fsum(durations), total, rel_tol=0, abs_tol=1e-6)


@pytest.mark.parametrize('boundary', [36.0, 42.0, 48.0, 54.0])
def test_shot_count_changes_at_six_second_ceiling(boundary):
    count = int(boundary / 6)
    assert len(split_duration(math.nextafter(boundary, -math.inf))) == count
    assert split_duration(boundary) == [6.0] * count
    assert len(split_duration(math.nextafter(boundary, math.inf))) == count + 1


@pytest.mark.parametrize('total', [*range(30, 61), 30.001, 36.001, 59.999])
def test_requested_duration_produces_valid_repeatable_plan(total):
    request = PlannerRequest(prompt='নদীর ধারে হাঁটা', duration_seconds=total)
    plan = MockPlanner().plan(request)
    assert StoryPlan.model_validate_json(plan.model_dump_json()) == plan
    assert plan == MockPlanner().plan(request)
    assert plan.estimated_total_duration_seconds == total
    assert math.isclose(sum(s.duration_seconds for s in plan.shots), total, abs_tol=1e-6)
    assert plan.shots[-1].action == 'The scene settles'


@pytest.mark.parametrize('value', [29.999, 60.001, True, '30', None, float('nan'), float('inf')])
def test_invalid_duration_rejected_by_splitter_and_request(value):
    with pytest.raises(ValidationError):
        split_duration(value)
    with pytest.raises(ValidationError):
        PlannerRequest(prompt='River', duration_seconds=value)


def test_default_plan_preserves_previous_ids_and_timing():
    request = PlannerRequest(prompt='River', seed=42)
    plan = MockPlanner().plan(request)
    legacy_json = json.dumps({'prompt': 'River', 'seed': 42}, separators=(',', ':'))
    fingerprint = hashlib.sha256(legacy_json.encode()).hexdigest()
    assert [s.duration_seconds for s in plan.shots] == [5.0] * 6
    for order, shot in enumerate(plan.shots, start=1):
        digest = hashlib.sha256(f'{fingerprint}:{order}'.encode()).hexdigest()
        assert shot.id == f'mock-{digest[:24]}'
        assert shot.seed == int(digest[:8], 16)
    assert plan == MockPlanner().plan(PlannerRequest(prompt='River', seed=42, duration_seconds=30))


def test_provider_revalidates_unchecked_duration():
    request = PlannerRequest(prompt='River').model_copy(update={'duration_seconds': 90})
    with pytest.raises(ValidationError):
        MockPlanner().plan(request)
