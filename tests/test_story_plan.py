import copy
import json

import pytest
from pydantic import ValidationError

from animation_studio.domain.v1.story_plan import ShotPlan, StoryPlan
from scripts import export_schemas


def fixture():
    return dict(
        schema_version=1,
        logline='A quiet journey',
        setting='Dhaka',
        mood='Calm',
        visual_style='Anime',
        characters=[dict(id='a', name='Airi')],
        estimated_total_duration_seconds=30,
        shots=[
            dict(
                id=f's{i}',
                order=i,
                duration_seconds=5,
                camera_framing='Wide',
                camera_movement='Static',
                background='River',
                action='Walking',
                lighting='Daylight',
                visible_character_ids=['a'],
                dialogue=[dict(speaker_id='a', text='চলো')],
                image_prompt='Walking by river',
                negative_prompt='',
                motion_prompt='Walk slowly',
                seed=i,
            )
            for i in range(1, 7)
        ],
    )


def test_valid_roundtrip_and_published_schemas():
    data = fixture()
    plan = StoryPlan.model_validate(data)
    assert StoryPlan.model_validate_json(plan.model_dump_json()) == plan
    assert all(s.status == 'pending' and s.attempts == 0 and s.error is None for s in plan.shots)
    assert export_schemas.export(export_schemas.OUTPUT, check=True) == 0
    for name, model in [('story-plan', StoryPlan), ('shot-plan', ShotPlan)]:
        schema = json.loads((export_schemas.OUTPUT / f'{name}.schema.json').read_text())
        assert schema.pop('$id') == f'urn:animation-studio:contracts:v1:{name}'
        schema.pop('$schema')
        assert schema == model.model_json_schema(mode='validation')


@pytest.mark.parametrize(
    'case',
    [
        'count',
        'order',
        'duplicate_shot',
        'duplicate_cast',
        'unknown_visible',
        'unknown_speaker',
        'duplicate_visible',
        'total',
        'short',
        'long',
        'nan',
        'string_duration',
        'bool_seed',
        'extra',
        'blank',
        'negative_attempts',
    ],
)
def test_invalid_plans(case):
    data = copy.deepcopy(fixture())
    shot = data['shots'][0]
    if case == 'count':
        data['shots'].pop()
    elif case == 'order':
        shot['order'] = 2
    elif case == 'duplicate_shot':
        shot['id'] = 's2'
    elif case == 'duplicate_cast':
        data['characters'] *= 2
    elif case == 'unknown_visible':
        shot['visible_character_ids'] = ['missing']
    elif case == 'unknown_speaker':
        shot['dialogue'][0]['speaker_id'] = 'missing'
    elif case == 'duplicate_visible':
        shot['visible_character_ids'] = ['a', 'a']
    elif case == 'total':
        data['estimated_total_duration_seconds'] = 31
    elif case == 'short':
        shot['duration_seconds'] = 2
    elif case == 'long':
        shot['duration_seconds'] = 7
    elif case == 'nan':
        shot['duration_seconds'] = float('nan')
    elif case == 'string_duration':
        shot['duration_seconds'] = '5'
    elif case == 'bool_seed':
        shot['seed'] = True
    elif case == 'extra':
        shot['surprise'] = 1
    elif case == 'blank':
        shot['action'] = '  '
    elif case == 'negative_attempts':
        shot['attempts'] = -1
    with pytest.raises(ValidationError):
        StoryPlan.model_validate(data)


def test_upper_boundary_and_offscreen_dialogue():
    data = fixture()
    data['shots'] = [
        {
            **data['shots'][0],
            'id': f's{i}',
            'order': i,
            'duration_seconds': 6,
            'visible_character_ids': [],
        }
        for i in range(1, 11)
    ]
    data['estimated_total_duration_seconds'] = 60
    assert len(StoryPlan.model_validate(data).shots) == 10


@pytest.mark.parametrize('version', [True, False, 1.0, '1', 2, None])
def test_schema_version_rejects_non_integer_or_unsupported_values(version):
    data = fixture()
    data['schema_version'] = version
    with pytest.raises(ValidationError):
        StoryPlan.model_validate(data)
    with pytest.raises(ValidationError):
        StoryPlan.model_validate_json(json.dumps(data))
