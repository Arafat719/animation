import sqlite3
from contextlib import closing

import pytest
from pydantic import ValidationError
from test_character_profile import payload

from animation_studio.domain.v1.character_profile import CharacterProfileDraft
from animation_studio.domain.v1.story_plan import StoryPlan
from animation_studio.persistence.character_profiles import (
    CharacterProfileStore,
    SavedCharacterProfile,
)
from animation_studio.persistence.db import init_db
from animation_studio.providers.character_profile_adapter import to_planner_character
from animation_studio.providers.planner import MockPlanner, PlannerRequest
from animation_studio.providers.planner_traits import TraitsAssemblyError, assemble_planner_traits


def saved(character_id=7):
    return SavedCharacterProfile(
        character_id=character_id,
        profile=CharacterProfileDraft.model_validate(payload()),
        created_at='2026-10-11',
    )


def test_exact_unicode_mapping_and_independent_output():
    original = saved()
    before = original.model_dump_json()
    result = to_planner_character(original, expected_character_id=7)
    assert result.id == 'character-7' and result.name == 'আলো'
    assert result.visual_traits == [
        'face: গোল মুখ',
        'hair: কালো চুল',
        'eyes: বাদামি চোখ',
        'outfit: নীল পোশাক',
        'color: নীল',
        'color: সাদা',
        'accessory: রুপার ঘড়ি',
    ]
    assert result.negative_traits == ['লাল পোশাক']
    assert original.profile.description not in result.model_dump_json()
    result.visual_traits.clear()
    assert original.model_dump_json() == before
    assert to_planner_character(original, expected_character_id=7).visual_traits


@pytest.mark.parametrize('identity', [True, 0, -1, 2**63, '7', 8])
def test_invalid_or_mismatched_selection(identity):
    with pytest.raises(ValueError):
        to_planner_character(saved(), expected_character_id=identity)


@pytest.mark.parametrize(
    'patch', [{'character_id': True}, {'schema_version': 2}, {'schema_version': True}]
)
def test_unchecked_snapshot_rejected(patch):
    with pytest.raises(ValueError):
        to_planner_character(saved().model_copy(update=patch), expected_character_id=7)


def test_unchecked_nested_profile_rejected():
    original = saved()
    changed = original.model_copy(
        update={'profile': original.profile.model_copy(update={'name': ''})}
    )
    with pytest.raises(ValidationError):
        to_planner_character(changed, expected_character_id=7)


def test_duplicate_names_still_have_distinct_ids_and_visibility():
    profiles = [to_planner_character(saved(i), expected_character_id=i) for i in (7, 8)]
    request = PlannerRequest(prompt='River', characters=profiles)
    base = MockPlanner().base_plan(request)
    base.shots[0].visible_character_ids = ['character-8']
    before = base.model_dump_json()
    result = assemble_planner_traits(before, profiles)
    plan = StoryPlan.model_validate_json(result.assembled_json)
    assert 'আলো [character-8]' in plan.shots[0].image_prompt
    assert 'আলো [character-7]' not in plan.shots[0].image_prompt
    assert base.model_dump_json() == before
    with pytest.raises(TraitsAssemblyError, match='TRAITS_ALREADY_PRESENT'):
        assemble_planner_traits(result.assembled_json, profiles)


def test_oversized_combined_traits_fail_without_truncation():
    data = payload()
    data['visual_traits']['colors'] = ['c' * 500] * 20
    original = saved().model_copy(update={'profile': CharacterProfileDraft.model_validate(data)})
    profile = to_planner_character(original, expected_character_id=7)
    assert len(profile.visual_traits) == 25
    base = MockPlanner().base_plan(PlannerRequest(prompt='River', characters=[profile]))
    with pytest.raises(TraitsAssemblyError, match='TRAITS_ASSEMBLY_INVALID'):
        assemble_planner_traits(base.model_dump_json(), [profile])


def test_saved_reopened_profile_uses_same_mapping(tmp_path):
    path = str(tmp_path / 'profile.db')
    init_db(path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("INSERT INTO characters(id,name) VALUES(7,'Legacy name')")
    snapshot = CharacterProfileStore(path).save(7, saved().profile)
    reopened = CharacterProfileStore(path).read(7)
    assert to_planner_character(snapshot, expected_character_id=7) == to_planner_character(
        reopened, expected_character_id=7
    )
    assert to_planner_character(reopened, expected_character_id=7).name == 'আলো'
