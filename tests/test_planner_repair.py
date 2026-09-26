import json

import pytest
from pydantic import ValidationError

from animation_studio.providers.planner import MockPlanner, PlannerCharacter, PlannerRequest
from animation_studio.providers.planner_repair import RepairExhausted, repair_plan


class ScriptedProvider:
    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def generate(self, request):
        return self.respond(request, None, ())

    def repair(self, request, previous_output, issues):
        return self.respond(request, previous_output, issues)

    def respond(self, request, previous, issues):
        self.calls.append((request, previous, issues))
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        return output


def valid(duration=30):
    return (
        MockPlanner()
        .plan(PlannerRequest(prompt='River', duration_seconds=duration))
        .model_dump_json()
    )


def test_first_output_and_independent_results():
    raw = valid()
    provider = ScriptedProvider(raw, raw)
    first = repair_plan(provider, PlannerRequest(prompt='River'))
    assert first.attempts == 1 and len(provider.calls) == 1
    assert first.status == 'REVIEW_REQUIRED'
    first.plan.shots.clear()
    second = repair_plan(provider, PlannerRequest(prompt='River'))
    assert len(second.plan.shots) == 6
    assert provider.calls[0][1:] == (None, ())


@pytest.mark.parametrize('kind', ['json', 'reference', 'timeline', 'field'])
def test_invalid_output_repaired_with_original_feedback(kind):
    data = json.loads(valid())
    if kind == 'reference':
        data['shots'][0]['visible_character_ids'] = ['unknown']
    elif kind == 'timeline':
        data['estimated_total_duration_seconds'] = 31
    elif kind == 'field':
        data['shots'][0]['order'] = '1'
    raw = '```json\n' + valid() + '\n```' if kind == 'json' else json.dumps(data)
    provider = ScriptedProvider(raw, valid())
    result = repair_plan(provider, PlannerRequest(prompt=' River '), max_retries=1)
    assert result.attempts == 2 and result.status == 'REVIEW_REQUIRED'
    assert provider.calls[1][1] == raw
    issue = provider.calls[1][2][0]
    assert issue.code == ('INVALID_JSON' if kind == 'json' else 'INVALID_PLAN')
    assert issue.path == (('shots', 0, 'order') if kind == 'field' else ())
    assert provider.calls[1][0].prompt == 'River'


def test_requested_duration_mismatch():
    provider = ScriptedProvider(valid(), valid(60))
    result = repair_plan(
        provider, PlannerRequest(prompt='River', duration_seconds=60), max_retries=1
    )
    assert result.plan.estimated_total_duration_seconds == 60
    issue = provider.calls[1][2][0]
    assert (issue.code, issue.path) == ('DURATION_MISMATCH', ('estimated_total_duration_seconds',))


@pytest.mark.parametrize('limit', [0, 1, 2])
def test_exhaustion_validates_every_repair_and_stops(limit):
    provider = ScriptedProvider(*(['{'] * (limit + 1)))
    with pytest.raises(RepairExhausted) as caught:
        repair_plan(provider, PlannerRequest(prompt='River'), max_retries=limit)
    assert len(provider.calls) == caught.value.attempts == limit + 1
    assert caught.value.issues[0].code == 'INVALID_JSON'
    assert not hasattr(caught.value, 'plan')


def test_second_repair_uses_latest_failure():
    provider = ScriptedProvider('{', '{}', valid())
    result = repair_plan(provider, PlannerRequest(prompt='River'), max_retries=2)
    assert result.attempts == 3
    assert provider.calls[2][1] == '{}'
    assert all(i.code == 'INVALID_PLAN' for i in provider.calls[2][2])


@pytest.mark.parametrize('limit', [-1, 3, True, False, 1.0, '1', None])
def test_invalid_budget_makes_zero_calls(limit):
    provider = ScriptedProvider()
    with pytest.raises(ValueError):
        repair_plan(provider, PlannerRequest(prompt='River'), max_retries=limit)
    assert not provider.calls


def test_unchecked_invalid_request_makes_zero_calls():
    provider = ScriptedProvider()
    request = PlannerRequest(prompt='River').model_copy(update={'prompt': ''})
    with pytest.raises(ValidationError):
        repair_plan(provider, request, max_retries=2)
    assert not provider.calls


@pytest.mark.parametrize('stage', [0, 1])
@pytest.mark.parametrize('kind', ['timeout', 'validation', 'runtime', 'object', 'bytes'])
def test_provider_failures_are_never_retried(stage, kind):
    if kind == 'validation':
        try:
            PlannerRequest(prompt='')
        except ValidationError as error:
            output = error
    else:
        output = {
            'timeout': TimeoutError('timeout'),
            'runtime': RuntimeError('broken'),
            'object': {},
            'bytes': b'{}',
        }[kind]
    provider = ScriptedProvider(*(['{'] * stage), output)
    expected = type(output) if isinstance(output, Exception) else TypeError
    with pytest.raises(expected) as caught:
        repair_plan(provider, PlannerRequest(prompt='River'), max_retries=2)
    if isinstance(output, Exception):
        assert caught.value is output
    assert len(provider.calls) == stage + 1


def test_nested_request_mutation_is_isolated():
    request = PlannerRequest(
        prompt='River',
        characters=[
            PlannerCharacter(
                id='hero',
                name='Hero',
                visual_traits=['blue coat'],
                negative_traits=['hat'],
            )
        ],
    )
    before = request.model_dump()

    class MutatingProvider(ScriptedProvider):
        def respond(self, received, previous, issues):
            assert received.model_dump() == before
            received.characters[0].visual_traits.append('changed')
            received.characters.clear()
            return super().respond(received, previous, issues)

    raw = MockPlanner().base_plan(request).model_dump_json()
    result = repair_plan(MutatingProvider('{', raw), request, max_retries=1)
    assert result.attempts == 2
    assert request.model_dump() == before


NONFRESH_FIELDS = [
    ('status', 'running'),
    ('status', 'completed'),
    ('status', 'failed'),
    ('status', 'cancelled'),
    ('attempts', 1),
    ('error', {'code': 'old', 'message': 'Old failure'}),
    ('keyframe_path', 'old.png'),
    ('raw_clip_path', 'old.mp4'),
    ('lip_synced_clip_path', 'old-lip.mp4'),
]


@pytest.mark.parametrize(('field', 'value'), NONFRESH_FIELDS)
def test_nonfresh_field_rejected_without_changing_shared_schema(field, value):
    from animation_studio.domain.v1.story_plan import StoryPlan

    data = json.loads(valid())
    data['shots'][2][field] = value
    raw = json.dumps(data)
    StoryPlan.model_validate_json(raw)  # Persisted lifecycle states remain valid.
    provider = ScriptedProvider(raw)
    with pytest.raises(RepairExhausted) as caught:
        repair_plan(provider, PlannerRequest(prompt='River'))
    assert caught.value.attempts == 1
    assert [(i.code, i.path) for i in caught.value.issues] == [
        ('NON_FRESH_PLAN', ('shots', 2, field)),
    ]


def test_nonfresh_feedback_order_and_repair_preserve_raw():
    data = json.loads(valid())
    dirty = dict(NONFRESH_FIELDS)
    data['shots'][0].update(dirty)
    data['shots'][1]['attempts'] = 2
    raw = json.dumps(data)
    provider = ScriptedProvider(raw, valid())
    result = repair_plan(provider, PlannerRequest(prompt='River'), max_retries=1)
    assert result.attempts == 2 and result.status == 'REVIEW_REQUIRED'
    assert provider.calls[1][1] == raw
    issues = provider.calls[1][2]
    assert all(i.code == 'NON_FRESH_PLAN' for i in issues)
    assert [i.path for i in issues] == [
        ('shots', 0, field)
        for field in (
            'status',
            'attempts',
            'error',
            'keyframe_path',
            'raw_clip_path',
            'lip_synced_clip_path',
        )
    ] + [('shots', 1, 'attempts')]
    assert json.loads(raw)['shots'][0]['attempts'] == 1


@pytest.mark.parametrize('limit', [0, 1, 2])
def test_nonfresh_repairs_exhaust_existing_budget(limit):
    data = json.loads(valid())
    data['shots'][0]['status'] = 'completed'
    provider = ScriptedProvider(*([json.dumps(data)] * (limit + 1)))
    with pytest.raises(RepairExhausted) as caught:
        repair_plan(provider, PlannerRequest(prompt='River'), max_retries=limit)
    assert caught.value.attempts == len(provider.calls) == limit + 1
    assert caught.value.issues[0].code == 'NON_FRESH_PLAN'


def test_duration_precedes_freshness():
    data = json.loads(valid())
    data['shots'][0]['status'] = 'completed'
    provider = ScriptedProvider(json.dumps(data))
    with pytest.raises(RepairExhausted) as caught:
        repair_plan(provider, PlannerRequest(prompt='River', duration_seconds=60))
    assert [i.code for i in caught.value.issues] == ['DURATION_MISMATCH']


def test_fresh_defaults_and_reference_inputs_preserved():
    data = json.loads(valid())
    for shot in data['shots']:
        for field in dict(NONFRESH_FIELDS):
            del shot[field]
    data['shots'][0]['reference_inputs'] = ['opaque-reference.png']
    result = repair_plan(ScriptedProvider(json.dumps(data)), PlannerRequest(prompt='River'))
    assert result.attempts == 1 and result.status == 'REVIEW_REQUIRED'
    assert result.plan.shots[0].reference_inputs == ['opaque-reference.png']
    assert all(s.status == 'pending' and s.attempts == 0 for s in result.plan.shots)


def cast_request():
    return PlannerRequest(
        prompt='River',
        characters=[
            PlannerCharacter(id='a', name='আলো', visual_traits=['blue']),
            PlannerCharacter(id='b', name='Bee', visual_traits=['green']),
        ],
    )


def cast_output(characters):
    data = json.loads(valid())
    data['characters'] = characters
    for shot in data['shots']:
        shot['visible_character_ids'] = []
    return data


@pytest.mark.parametrize('mode', ['normal', 'reverse_extra', 'whitespace', 'offscreen'])
def test_supplied_cast_subset_and_visibility(mode):
    cast = [{'id': 'a', 'name': 'আলো'}, {'id': 'b', 'name': 'Bee'}]
    if mode == 'reverse_extra':
        cast = [cast[1], {'id': 'extra', 'name': 'Extra'}, cast[0]]
    if mode == 'whitespace':
        cast[0]['name'] = ' আলো \n'
    data = cast_output(cast)
    if mode == 'offscreen':
        data['shots'][0]['dialogue'] = [{'speaker_id': 'a', 'text': 'Hello'}]
    result = repair_plan(ScriptedProvider(json.dumps(data)), cast_request())
    assert result.status == 'REVIEW_REQUIRED'
    assert [c.id for c in result.plan.characters] == [c['id'] for c in cast]


@pytest.mark.parametrize('name', ['Changed', 'আলা', 'bee'])
def test_cast_name_mismatch_uses_output_index(name):
    data = cast_output([{'id': 'b', 'name': name}, {'id': 'a', 'name': 'আলো'}])
    with pytest.raises(RepairExhausted) as caught:
        repair_plan(ScriptedProvider(json.dumps(data)), cast_request())
    (issue,) = caught.value.issues
    assert (issue.code, issue.path) == ('CAST_NAME_MISMATCH', ('characters', 0, 'name'))
    assert 'Bee' in issue.message and "'b'" in issue.message


def test_missing_cast_same_name_and_request_order():
    data = cast_output([{'id': 'other', 'name': 'আলো'}])
    with pytest.raises(RepairExhausted) as caught:
        repair_plan(ScriptedProvider(json.dumps(data)), cast_request())
    assert [i.code for i in caught.value.issues] == ['CAST_MISSING'] * 2
    assert [i.path for i in caught.value.issues] == [('characters',)] * 2
    assert "'a'" in caught.value.issues[0].message
    assert "'b'" in caught.value.issues[1].message


def test_mixed_cast_errors_repair_without_raw_rewrite():
    data = cast_output([{'id': 'b', 'name': 'Wrong'}])
    raw = json.dumps(data)
    request = cast_request()
    provider = ScriptedProvider(raw, MockPlanner().base_plan(request).model_dump_json())
    result = repair_plan(provider, request, max_retries=1)
    assert result.attempts == 2
    assert provider.calls[1][1] == raw
    assert [i.code for i in provider.calls[1][2]] == ['CAST_MISSING', 'CAST_NAME_MISMATCH']


@pytest.mark.parametrize('limit', [0, 1, 2])
def test_cast_repairs_obey_budget(limit):
    # Each attempted repair introduces a different invalid cast.
    outputs = [
        json.dumps(cast_output([])),
        json.dumps(cast_output([{'id': 'a', 'name': 'Wrong'}])),
        json.dumps(cast_output([{'id': 'b', 'name': 'Wrong'}])),
    ]
    provider = ScriptedProvider(*outputs)
    with pytest.raises(RepairExhausted) as caught:
        repair_plan(provider, cast_request(), max_retries=limit)
    assert caught.value.attempts == len(provider.calls) == limit + 1
    assert caught.value.issues[0].code == ('CAST_NAME_MISMATCH' if limit == 1 else 'CAST_MISSING')


@pytest.mark.parametrize(
    ('kind', 'code'),
    [
        ('duplicate', 'INVALID_PLAN'),
        ('reference', 'INVALID_PLAN'),
        ('duration', 'DURATION_MISMATCH'),
        ('lifecycle', 'NON_FRESH_PLAN'),
    ],
)
def test_cast_checks_follow_existing_precedence(kind, code):
    data = json.loads(valid())  # Missing requested a/b.
    request = cast_request()
    if kind == 'duplicate':
        data['characters'].append(data['characters'][0].copy())
    elif kind == 'reference':
        data['shots'][0]['visible_character_ids'] = ['missing']
    elif kind == 'duration':
        request = request.model_copy(update={'duration_seconds': 60.0})
    else:
        data['shots'][0]['status'] = 'completed'
    with pytest.raises(RepairExhausted) as caught:
        repair_plan(ScriptedProvider(json.dumps(data)), request)
    assert all(i.code == code for i in caught.value.issues)
