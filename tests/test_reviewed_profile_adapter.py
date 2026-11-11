"""Pure v2 mapping and v1/v2 planner compatibility without enabling API consumers."""

import pytest
from pydantic import ValidationError
from test_character_profile_adapter import saved as manual
from test_character_review import build, review, setup

from animation_studio.domain.v1.story_plan import StoryPlan
from animation_studio.persistence.reviewed_character_profiles import SavedReviewedCharacterProfile
from animation_studio.providers.character_profile_adapter import to_planner_character
from animation_studio.providers.planner import MockPlanner, PlannerRequest
from animation_studio.providers.planner_traits import TraitsAssemblyError, assemble_planner_traits


def saved(**decisions):
    report = setup()
    profile = build(report, review(report, **decisions))
    return SavedReviewedCharacterProfile(
        character_id=1,
        profile=profile,
        created_at='2026-10-12T00:00:00Z',
        reviewed_at='2026-10-12T00:00:00Z',
    )


def test_final_replacements_omissions_order_and_independent_output():
    original = saved(
        hair={'action': 'replace', 'value': ' সাদা চুল '},
        colors={'action': 'replace', 'value': ('সাদা', 'নীল')},
        accessories={'action': 'omit'},
        negative_traits={'action': 'replace', 'value': ('সবুজ', 'কালো')},
    )
    before = original.model_dump_json()
    result = to_planner_character(original, expected_character_id=1)
    assert result.id == 'character-1' and result.name == 'আলো'
    assert result.visual_traits == [
        'face: গোল মুখ',
        'hair: সাদা চুল',
        'eyes: বাদামি চোখ',
        'outfit: নীল পোশাক',
        'color: সাদা',
        'color: নীল',
    ]
    assert result.negative_traits == ['সবুজ', 'কালো']
    assert 'কালো চুল' not in result.model_dump_json()
    assert original.profile.values.description not in result.model_dump_json()
    for private in ('provenance', 'report_hash', 'REVIEW_REQUIRED', 'created_at', 'is_mock'):
        assert private not in result.model_dump_json()
    result.visual_traits.clear()
    result.negative_traits.clear()
    assert original.model_dump_json() == before
    assert original.profile.provenance.report.provider.is_mock is True
    assert to_planner_character(original, expected_character_id=1).visual_traits


def test_accepted_optional_values_and_json_reopened_mapping():
    original = saved()
    reopened = SavedReviewedCharacterProfile.model_validate_json(original.model_dump_json())
    result = to_planner_character(reopened, expected_character_id=1)
    assert result == to_planner_character(original, expected_character_id=1)
    assert result.visual_traits[-1] == 'accessory: ঘড়ি'
    assert result.negative_traits == ['লাল']


@pytest.mark.parametrize('identity', [True, 0, -1, 2**63, '1', 2])
def test_invalid_or_cross_character_selection(identity):
    with pytest.raises(ValueError):
        to_planner_character(saved(), expected_character_id=identity)


@pytest.mark.parametrize(
    'patch',
    [
        {'character_id': True},
        {'character_id': 2},
        {'schema_version': 1},
        {'schema_version': 2.0},
        {'schema_version': True},
        {'schema_version': '2'},
        {'reviewed_at': 'bad'},
        {'extra': 'bad'},
    ],
)
def test_unchecked_saved_envelope_rejected(patch):
    with pytest.raises(ValueError):
        to_planner_character(saved().model_copy(update=patch), expected_character_id=1)


@pytest.mark.parametrize('damage', ['values', 'hash', 'origin', 'confirmation', 'evidence'])
def test_nested_unchecked_copies_revalidated(damage):
    original = saved()
    profile = original.profile
    provenance = profile.provenance
    if damage == 'values':
        profile = profile.model_copy(
            update={'values': profile.values.model_copy(update={'name': 'tampered'})}
        )
    elif damage == 'origin':
        profile = profile.model_copy(
            update={'origins': profile.origins.model_copy(update={'hair': 'user_replacement'})}
        )
    else:
        if damage == 'hash':
            provenance = provenance.model_copy(update={'report_hash': '0' * 64})
        elif damage == 'confirmation':
            provenance = provenance.model_copy(
                update={'review': provenance.review.model_copy(update={'confirmed': 1})}
            )
        else:
            report = provenance.report
            candidate = report.candidate.model_copy(
                update={'hair': report.candidate.hair.model_copy(update={'start': True})}
            )
            provenance = provenance.model_copy(
                update={'report': report.model_copy(update={'candidate': candidate})}
            )
        profile = profile.model_copy(update={'provenance': provenance})
    with pytest.raises(ValidationError):
        to_planner_character(
            original.model_copy(update={'profile': profile}), expected_character_id=1
        )


@pytest.mark.parametrize('kind', ['draft', 'dict', 'none'])
def test_only_saved_wrappers_accepted(kind):
    original = saved()
    value = {'draft': original.profile, 'dict': original.model_dump(), 'none': None}[kind]
    with pytest.raises(TypeError):
        to_planner_character(value, expected_character_id=1)


def test_mixed_versions_visibility_and_no_provenance_in_prompts():
    reviewed = saved(
        hair={'action': 'replace', 'value': 'সাদা চুল'},
        accessories={'action': 'omit'},
        negative_traits={'action': 'omit'},
    )
    profiles = [
        to_planner_character(manual(), expected_character_id=7),
        to_planner_character(reviewed, expected_character_id=1),
    ]
    base = MockPlanner().base_plan(PlannerRequest(prompt='River', characters=profiles))
    base.shots[0].visible_character_ids = ['character-1']
    base.shots[1].visible_character_ids = ['character-7']
    before = base.model_dump_json()
    result = assemble_planner_traits(before, profiles)
    plan = StoryPlan.model_validate_json(result.assembled_json)
    assert 'hair: সাদা চুল' in plan.shots[0].image_prompt
    assert 'hair: কালো চুল' not in plan.shots[0].image_prompt
    assert 'আলো [character-7]' not in plan.shots[0].image_prompt
    assert 'hair: কালো চুল' in plan.shots[1].image_prompt
    assert 'hair: সাদা চুল' not in plan.shots[1].image_prompt
    assert plan.shots[0].negative_prompt == base.shots[0].negative_prompt
    assert reviewed.profile.values.description not in result.assembled_json
    assert reviewed.profile.provenance.report_hash not in result.assembled_json
    assert result.status == 'REVIEW_REQUIRED'
    assert base.model_dump_json() == before
    with pytest.raises(TraitsAssemblyError, match='TRAITS_ALREADY_PRESENT'):
        assemble_planner_traits(result.assembled_json, profiles)


def test_oversized_reviewed_traits_fail_without_truncation():
    original = saved(colors={'action': 'replace', 'value': ('c' * 500,) * 20})
    profile = to_planner_character(original, expected_character_id=1)
    assert len(profile.visual_traits) == 25
    base = MockPlanner().base_plan(PlannerRequest(prompt='River', characters=[profile]))
    with pytest.raises(TraitsAssemblyError, match='TRAITS_ASSEMBLY_INVALID'):
        assemble_planner_traits(base.model_dump_json(), [profile])


def test_adapter_has_no_io(monkeypatch):
    import socket
    import sqlite3
    import subprocess

    original = saved()

    def forbidden(*args, **kwargs):
        pytest.fail('Adapter must be pure')

    for module, name in ((socket, 'socket'), (sqlite3, 'connect'), (subprocess, 'Popen')):
        monkeypatch.setattr(module, name, forbidden)
    assert to_planner_character(original, expected_character_id=1).id == 'character-1'
