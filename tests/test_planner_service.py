import json

import pytest

from animation_studio.providers.planner import MockPlanner, PlannerCharacter, PlannerRequest
from animation_studio.providers.planner_repair import RepairExhausted, repair_plan
from animation_studio.providers.planner_service import MockDraftProvider, PlannerService


def request(duration=30):
    return PlannerRequest(
        prompt='নদীর ধারে',
        duration_seconds=duration,
        characters=[
            PlannerCharacter(
                id='a', name='আলো', visual_traits=['নীল পোশাক'], negative_traits=['hat']
            ),
        ],
    )


class SequenceProvider:
    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def generate(self, req):
        self.calls.append((None, ()))
        return next(self.outputs)

    def repair(self, req, previous_output, issues):
        self.calls.append((previous_output, issues))
        return next(self.outputs)


@pytest.mark.parametrize('duration', [30, 45, 60])
def test_mock_service_matches_existing_plan_with_traits(duration):
    req = request(duration)
    service = PlannerService(MockDraftProvider(), max_retries=1)
    expected = MockPlanner().plan(req)
    assert service.plan(req) == expected == service.plan(req)
    assert all(s.image_prompt.count('আলো [a]: নীল পোশাক') == 1 for s in expected.shots)


@pytest.mark.parametrize('failure', ['prefilled', 'overflow'])
def test_traits_failure_repairs_raw_base_only(failure):
    req = request()
    base = MockPlanner().base_plan(req).model_dump_json()
    if failure == 'prefilled':
        bad = MockPlanner().plan(req).model_dump_json()
        code = 'TRAITS_ALREADY_PRESENT'
    else:
        data = json.loads(base)
        data['shots'][0]['image_prompt'] = 'x' * 4000
        bad = json.dumps(data)
        code = 'TRAITS_ASSEMBLY_INVALID'
    provider = SequenceProvider(bad, base)
    result = repair_plan(provider, req, max_retries=1)
    assert result.attempts == 2 and result.status == 'REVIEW_REQUIRED'
    assert provider.calls[1][0] == bad
    assert provider.calls[1][1][0].code == code
    assert json.loads(result.base_json) == json.loads(base)
    assert result.plan == MockPlanner().plan(req)
    assert json.loads(base)['shots'][0]['image_prompt'] == req.prompt


@pytest.mark.parametrize('limit', [0, 1, 2])
def test_impossible_visible_traits_stop_within_budget(limit):
    req = request()
    req.characters[0].visual_traits = ['x' * 4000]
    raw = MockPlanner().base_plan(req).model_dump_json()
    provider = SequenceProvider(*([raw] * (limit + 1)))
    with pytest.raises(RepairExhausted) as caught:
        repair_plan(provider, req, max_retries=limit)
    assert len(provider.calls) == caught.value.attempts == limit + 1
    assert all(i.code == 'TRAITS_ASSEMBLY_INVALID' for i in caught.value.issues)


def test_shape_then_overflow_then_success_share_single_budget():
    req = request()
    raw = MockPlanner().base_plan(req).model_dump_json()
    data = json.loads(raw)
    data['shots'][0]['motion_prompt'] = 'x' * 4000
    overflow = json.dumps(data)
    provider = SequenceProvider('{', overflow, raw)
    result = repair_plan(provider, req, max_retries=2)
    assert result.attempts == 3
    assert provider.calls[1][0] == '{'
    assert provider.calls[2][0] == overflow
    assert result.plan.shots[0].motion_prompt.count('আলো [a]: নীল পোশাক') == 1
