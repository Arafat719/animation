import pytest
from pydantic import ValidationError

from animation_studio.domain.v1.story_plan import DialogueLine, StoryPlan
from animation_studio.providers.planner import (
    MockPlanner,
    PlannerCharacter,
    PlannerRequest,
    inject_character_traits,
)


def profiles():
    return [
        PlannerCharacter(
            id='a', name='আলো', visual_traits=['কালো চুল', 'নীল পোশাক'], negative_traits=['লাল পোশাক']
        ),
        PlannerCharacter(id='b', name='B', visual_traits=['green eyes']),
    ]


@pytest.mark.parametrize('duration', [30, 45, 60])
def test_profiles_in_every_mock_shot(duration):
    request = PlannerRequest(prompt='River', characters=profiles(), duration_seconds=duration)
    plan = MockPlanner().plan(request)
    assert plan == MockPlanner().plan(request)
    assert StoryPlan.model_validate_json(plan.model_dump_json()) == plan
    for shot in plan.shots:
        assert shot.image_prompt == 'River\nআলো [a]: কালো চুল; নীল পোশাক\nB [b]: green eyes'
        assert shot.motion_prompt == shot.action + '\nআলো [a]: কালো চুল; নীল পোশাক\nB [b]: green eyes'
        assert shot.negative_prompt == 'আলো [a]: লাল পোশাক'
    changed = request.model_copy(deep=True)
    changed.characters[0].visual_traits[0] = 'white hair'
    assert MockPlanner().plan(changed).shots[0].id != plan.shots[0].id
    assert request.characters[0].visual_traits[0] == 'কালো চুল'


def test_visibility_offscreen_dialogue_and_input_preservation():
    cast = profiles()
    base = MockPlanner().plan(PlannerRequest(prompt='River', characters=cast))
    for shot in base.shots:
        shot.image_prompt = 'Image'
        shot.motion_prompt = 'Motion'
        shot.negative_prompt = 'blur'
    base.shots[0].visible_character_ids = ['b']
    base.shots[0].dialogue = [DialogueLine(speaker_id='a', text='Hello')]
    base.shots[1].visible_character_ids = []
    before = base.model_dump_json()
    result = inject_character_traits(base, cast)
    assert result.shots[0].image_prompt == 'Image\nB [b]: green eyes'
    assert result.shots[0].negative_prompt == 'blur'
    assert result.shots[1] == base.shots[1]
    assert base.model_dump_json() == before
    assert result.shots[2].negative_prompt == 'blur\nআলো [a]: লাল পোশাক'


@pytest.mark.parametrize('traits', [[], [' '], [123], ['x' * 4001]])
def test_invalid_visual_traits(traits):
    with pytest.raises(ValidationError):
        PlannerCharacter(id='a', name='A', visual_traits=traits)


def test_duplicate_and_unchecked_profiles_rejected():
    cast = profiles()
    with pytest.raises(ValidationError):
        PlannerRequest(prompt='River', characters=[cast[0], cast[0]])
    request = PlannerRequest(prompt='River', characters=cast)
    request.characters[0].visual_traits.clear()
    with pytest.raises(ValidationError):
        MockPlanner().plan(request)


def test_overflow_rejected_without_truncation():
    request = PlannerRequest(prompt='x' * 4000, characters=profiles())
    with pytest.raises(ValidationError):
        MockPlanner().plan(request)


def test_unknown_profile_and_duplicate_injection_rejected():
    base = MockPlanner().plan(PlannerRequest(prompt='River'))
    with pytest.raises(ValueError, match='plan cast'):
        inject_character_traits(base, profiles())
    with pytest.raises(ValueError, match='unique'):
        inject_character_traits(base, [profiles()[0]] * 2)
