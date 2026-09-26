import os
import subprocess
import sys

import pytest
from pydantic import ValidationError

from animation_studio.domain.v1.story_plan import StoryPlan
from animation_studio.providers.planner import MockPlanner, PlannerProvider, PlannerRequest


@pytest.mark.parametrize('prompt', ['A walk by the river', 'বৃষ্টির পরে নদীর ধারে হাঁটা', 'ক' * 4000])
def test_provider_contract_and_determinism(prompt):
    provider: PlannerProvider = MockPlanner()
    request = PlannerRequest(prompt=prompt, seed=42)
    first = provider.plan(request)
    assert first.model_dump_json() == MockPlanner().plan(request).model_dump_json()
    assert StoryPlan.model_validate_json(first.model_dump_json()) == first
    assert first.logline == prompt
    assert [shot.order for shot in first.shots] == list(range(1, 7))
    assert sum(shot.duration_seconds for shot in first.shots) == 30
    assert all(shot.image_prompt == prompt and shot.status == 'pending' for shot in first.shots)


def test_results_do_not_share_mutable_state():
    provider = MockPlanner()
    request = PlannerRequest(prompt='River')
    first = provider.plan(request)
    expected = first.model_dump_json()
    first.shots[0].visible_character_ids.clear()
    first.characters[0].name = 'Changed'
    assert provider.plan(request).model_dump_json() == expected


def test_input_changes_and_whitespace_normalization():
    provider = MockPlanner()
    first = provider.plan(PlannerRequest(prompt='River', seed=0))
    assert first == provider.plan(PlannerRequest(prompt='  River\n', seed=0))
    for request in [PlannerRequest(prompt='Forest'), PlannerRequest(prompt='River', seed=1)]:
        changed = provider.plan(request)
        assert [s.id for s in changed.shots] != [s.id for s in first.shots]
        assert [s.seed for s in changed.shots] != [s.seed for s in first.shots]


@pytest.mark.parametrize(
    'data',
    [
        {'prompt': ''},
        {'prompt': ' \n '},
        {'prompt': 'a' * 4001},
        {'prompt': 12},
        {'prompt': 'River', 'seed': True},
        {'prompt': 'River', 'seed': -1},
        {'prompt': 'River', 'seed': 2**32},
        {'prompt': 'River', 'seed': '1'},
        {'prompt': 'River', 'extra': 'unsupported'},
    ],
)
def test_invalid_requests(data):
    with pytest.raises(ValidationError):
        PlannerRequest.model_validate(data)


def test_provider_revalidates_unchecked_model_copy():
    request = PlannerRequest(prompt='River').model_copy(update={'prompt': ''})
    with pytest.raises(ValidationError):
        MockPlanner().plan(request)


def test_deterministic_across_processes():
    request = PlannerRequest(prompt='নদীর ধারে', seed=2**32 - 1)
    code = (
        'import sys; '
        'from animation_studio.providers.planner import MockPlanner, PlannerRequest; '
        'print(MockPlanner().plan(PlannerRequest.model_validate_json(sys.stdin.read()))'
        '.model_dump_json())'
    )
    expected = MockPlanner().plan(request).model_dump_json()
    for hash_seed in ('1', '2'):
        result = subprocess.run(
            [sys.executable, '-c', code],
            input=request.model_dump_json(),
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
            env={**os.environ, 'PYTHONHASHSEED': hash_seed},
        )
        assert result.stdout.strip() == expected
