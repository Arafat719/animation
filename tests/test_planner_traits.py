from dataclasses import FrozenInstanceError
import json

import pytest
from pydantic import ValidationError

from animation_studio.providers.planner import MockPlanner, PlannerCharacter, PlannerRequest
from animation_studio.providers.planner_traits import assemble_planner_traits, TraitsAssemblyError


def profiles():
    return [PlannerCharacter(id='a', name='আলো', visual_traits=['নীল\nপোশাক'], negative_traits=['hat']),
            PlannerCharacter(id='b', name='Bee', visual_traits=['green'])]


def base():
    data = json.loads(MockPlanner().plan(PlannerRequest(prompt='River', characters=profiles())).model_dump_json())
    for shot in data['shots']:
        shot.update(image_prompt='Image', motion_prompt='Motion', negative_prompt='blur')
    return data


def test_visible_order_offscreen_extra_and_preservation():
    data = base()
    data['characters'].append({'id': 'extra', 'name': 'Extra'})
    data['shots'][0]['visible_character_ids'] = ['b', 'extra', 'a']
    data['shots'][1]['visible_character_ids'] = ['b']
    data['shots'][1]['dialogue'] = [{'speaker_id': 'a', 'text': 'Hello'}]
    data['shots'][2]['visible_character_ids'] = []
    raw = json.dumps(data)
    supplied = profiles()
    before = [p.model_dump() for p in supplied]
    result = assemble_planner_traits(raw, supplied)
    out = json.loads(result.assembled_json)
    assert result.status == 'REVIEW_REQUIRED'
    assert out['shots'][0]['image_prompt'] == 'Image\nBee [b]: green\nআলো [a]: নীল\nপোশাক'
    assert out['shots'][0]['motion_prompt'] == 'Motion\nBee [b]: green\nআলো [a]: নীল\nপোশাক'
    assert out['shots'][0]['negative_prompt'] == 'blur\nআলো [a]: hat'
    assert out['shots'][1]['image_prompt'] == 'Image\nBee [b]: green'
    assert out['shots'][1]['negative_prompt'] == 'blur'
    assert out['shots'][2] == data['shots'][2]
    assert json.loads(result.base_json) == data
    assert assemble_planner_traits(raw, supplied) == result
    supplied[0].visual_traits.clear()
    assert json.loads(result.base_json) == data
    assert before[0]['visual_traits'] == ['নীল\nপোশাক']
    with pytest.raises(FrozenInstanceError):
        result.base_json = '{}'


@pytest.mark.parametrize('mode', ['empty', 'invisible'])
def test_noop_reassembly(mode):
    data = base()
    for shot in data['shots']:
        shot['visible_character_ids'] = []
    supplied = [] if mode == 'empty' else profiles()
    result = assemble_planner_traits(json.dumps(data), supplied)
    assert result.base_json == result.assembled_json
    assert assemble_planner_traits(result.assembled_json, supplied) == result


@pytest.mark.parametrize('source', ['helper', 'mock'])
def test_assembled_output_rejected(source):
    raw = (assemble_planner_traits(json.dumps(base()), profiles()).assembled_json
           if source == 'helper' else MockPlanner().plan(
               PlannerRequest(prompt='River', characters=profiles())).model_dump_json())
    with pytest.raises(TraitsAssemblyError) as caught:
        assemble_planner_traits(raw, profiles())
    assert caught.value.code == 'TRAITS_ALREADY_PRESENT'
    assert caught.value.paths == (('shots', 0, 'image_prompt'),)


@pytest.mark.parametrize('name', ['image_prompt', 'motion_prompt', 'negative_prompt'])
@pytest.mark.parametrize('block', ['আলো [a]: নীল\nপোশাক', 'আলো [a]: hat'])
def test_prefilled_blocks_rejected_even_invisible(name, block):
    data = base()
    data['shots'][0]['visible_character_ids'] = []
    data['shots'][0][name] = 'prefix ' + block + ' suffix'
    with pytest.raises(TraitsAssemblyError) as caught:
        assemble_planner_traits(json.dumps(data), profiles())
    assert (caught.value.code, caught.value.paths) == ('TRAITS_ALREADY_PRESENT', (('shots', 0, name),))


@pytest.mark.parametrize('mode', ['duplicate', 'unknown', 'name'])
def test_profile_mismatch(mode):
    supplied = profiles()
    expected = ('profiles', 1, 'id')
    if mode == 'duplicate':
        supplied[1] = supplied[0]
    elif mode == 'unknown':
        supplied[1] = supplied[1].model_copy(update={'id': 'unknown'})
    else:
        supplied[1] = supplied[1].model_copy(update={'name': 'Changed'})
        expected = ('characters', 1, 'name')
    with pytest.raises(TraitsAssemblyError) as caught:
        assemble_planner_traits(json.dumps(base()), supplied)
    assert caught.value.code == 'TRAITS_PROFILE_MISMATCH'
    assert caught.value.paths == (expected,)


@pytest.mark.parametrize('name', ['image_prompt', 'motion_prompt', 'negative_prompt'])
@pytest.mark.parametrize('overflow', [False, True])
def test_prompt_limit_no_truncation(name, overflow):
    data = base()
    supplied = profiles()[:1]
    block = 'আলো [a]: ' + ('hat' if name == 'negative_prompt' else 'নীল\nপোশাক')
    data['shots'][0][name] = 'x' * (4000 - len(block) - 1 + int(overflow))
    raw = json.dumps(data)
    if overflow:
        with pytest.raises(TraitsAssemblyError) as caught:
            assemble_planner_traits(raw, supplied)
        assert caught.value.code == 'TRAITS_ASSEMBLY_INVALID'
        assert caught.value.paths == (('shots', 0, name),)
    else:
        result = assemble_planner_traits(raw, supplied)
        assert len(json.loads(result.assembled_json)['shots'][0][name]) == 4000
    assert json.loads(raw) == data


def test_invalid_inputs_propagate():
    with pytest.raises(TypeError):
        assemble_planner_traits({}, [])
    with pytest.raises(ValidationError):
        assemble_planner_traits('{', [])
    supplied = profiles()
    supplied[0].visual_traits.clear()
    with pytest.raises(ValidationError):
        assemble_planner_traits(json.dumps(base()), supplied)
