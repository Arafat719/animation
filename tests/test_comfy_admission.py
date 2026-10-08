import builtins
import socket
import subprocess
from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from animation_studio.providers.comfy_admission import (
    REQUIRED_CAPABILITIES,
    ComfyAdmissionObservation,
    admission_policy_sha256,
    evaluate_admission,
)
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy

UUID = '12345678-1234-4234-8234-123456789abc'
OTHER_UUID = '22345678-1234-4234-8234-123456789abc'


@pytest.fixture
def inputs():
    context = ComfyExecutionContext(
        mode='mock',
        job_id=UUID,
        graph_sha256='a' * 64,
        origin='https://selected.invalid:443/',
        deployment_id=UUID,
        runtime_manifest_sha256='b' * 64,
        model_manifest_sha256='c' * 64,
    )
    policy = ComfySupervisionPolicy(
        ram_limit_bytes=1024,
        host_reserve_bytes=512,
        device_index=0,
        vram_limit_bytes=1024,
        sample_interval_seconds=1.0,
        stale_after_seconds=2.0,
        overall_timeout_seconds=60.0,
        cleanup_reserve_seconds=5.0,
        reap_allowance_seconds=5.0,
    )
    observations = tuple(
        ComfyAdmissionObservation(
            capability=capability,
            status='passed',
            context=context,
            worker_id='worker-1',
            device_index=0,
            policy_sha256=admission_policy_sha256(policy),
            source='fixture',
            clock_session_id=UUID,
            checked_at=100.0,
            evidence_sha256='d' * 64,
        )
        for capability in REQUIRED_CAPABILITIES
    )
    return {
        'context': context,
        'policy': policy,
        'observations': observations,
        'worker_id': 'worker-1',
        'clock_session_id': UUID,
        'expected_source': 'fixture',
        'now': 101.0,
        'max_age_seconds': 2.0,
    }


def change_observation(inputs, **updates):
    first, *rest = inputs['observations']
    inputs['observations'] = (first.model_copy(update=updates), *rest)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Admission must not use network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


def test_pure_fixture_allow_and_immutable(inputs, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Evaluator must not perform I/O or launch a process')

    with monkeypatch.context() as patch:
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(subprocess, 'Popen', forbidden)
        decision = evaluate_admission(**inputs)
    assert decision.action == 'allow' and decision.source == 'fixture' and not decision.reasons
    with pytest.raises(FrozenInstanceError):
        decision.action = 'allow'
    with pytest.raises(ValidationError):
        inputs['observations'][0].status = 'failed'
    with pytest.raises(ValidationError):
        inputs['observations'][0].context.mode = 'live'


@pytest.mark.parametrize('capability', REQUIRED_CAPABILITIES)
@pytest.mark.parametrize('status', ['missing', 'failed', 'unknown', 'duplicate'])
def test_each_required_capability(inputs, capability, status):
    values = list(inputs['observations'])
    index = REQUIRED_CAPABILITIES.index(capability)
    if status == 'missing':
        values.pop(index)
    elif status == 'duplicate':
        values[index] = values[(index + 1) % len(values)]
    else:
        values[index] = values[index].model_copy(update={'status': status})
    result = evaluate_admission(**(inputs | {'observations': tuple(values)}))
    assert result.action == 'deny' and f'capability_{status}' in result.reasons


@pytest.mark.parametrize(
    'field,value',
    [
        ('mode', 'live'),
        ('job_id', OTHER_UUID),
        ('deployment_id', OTHER_UUID),
        ('origin', 'https://other.invalid:443/'),
        ('graph_sha256', 'e' * 64),
        ('runtime_manifest_sha256', 'e' * 64),
        ('model_manifest_sha256', 'e' * 64),
    ],
)
def test_every_context_field(inputs, field, value):
    change_observation(inputs, context=inputs['context'].model_copy(update={field: value}))
    result = evaluate_admission(**inputs)
    assert result.action == 'deny' and 'context_mismatch' in result.reasons


@pytest.mark.parametrize(
    'field,value,reason',
    [
        ('worker_id', 'worker-2', 'worker_mismatch'),
        ('device_index', 1, 'device_mismatch'),
        ('policy_sha256', 'e' * 64, 'policy_mismatch'),
        ('source', 'target', 'source_mismatch'),
        ('clock_session_id', OTHER_UUID, 'clock_session_mismatch'),
    ],
)
def test_bindings(inputs, field, value, reason):
    change_observation(inputs, **{field: value})
    assert evaluate_admission(**inputs).reasons == (reason,)


@pytest.mark.parametrize('field', list(ComfySupervisionPolicy.model_fields))
def test_all_policy_fields_bound(inputs, field):
    policy = inputs['policy']
    changed = ComfySupervisionPolicy(**(policy.model_dump() | {field: getattr(policy, field) + 1}))
    assert admission_policy_sha256(changed) != admission_policy_sha256(policy)
    result = evaluate_admission(**(inputs | {'policy': changed}))
    assert result.action == 'deny' and 'policy_mismatch' in result.reasons


@pytest.mark.parametrize(
    'checked_at,reason',
    [
        (101.0, None),
        (99.0, None),
        (98.99, 'evidence_stale'),
        (101.01, 'evidence_future'),
    ],
)
def test_freshness_boundaries(inputs, checked_at, reason):
    change_observation(inputs, checked_at=checked_at)
    result = evaluate_admission(**inputs)
    assert result.action == ('deny' if reason else 'allow')
    assert result.reasons == ((reason,) if reason else ())


@pytest.mark.parametrize('field', ['now', 'max_age_seconds'])
@pytest.mark.parametrize('value', [True, -1, float('nan'), float('inf'), '100', 10**400])
def test_invalid_clock_inputs(inputs, field, value):
    result = evaluate_admission(**(inputs | {field: value}))
    assert result.action == 'deny' and result.reasons == ('input_invalid',)


@pytest.mark.parametrize(
    'field,value',
    [
        ('capability', 'synthetic-secret'),
        ('status', 'synthetic-secret'),
        ('checked_at', float('nan')),
        ('checked_at', True),
        ('checked_at', 10**400),
        ('device_index', True),
        ('policy_sha256', 'secret'),
        ('evidence_sha256', 'secret'),
        ('clock_session_id', 'bad'),
        ('source', 'secret'),
        ('worker_id', 'x' * 129),
        ('context', {'mode': 'synthetic-secret'}),
        ('unexpected', 'synthetic-secret'),
    ],
)
def test_bypassed_observation_denies_with_bounded_codes(inputs, field, value):
    change_observation(inputs, **{field: value})
    result = evaluate_admission(**inputs)
    assert result.action == 'deny' and 'observation_invalid' in result.reasons
    assert 'secret' not in repr(result)


def test_bypassed_nested_context_and_policy_revalidated(inputs):
    change_observation(inputs, context=inputs['context'].model_copy(update={'job_id': 'bad'}))
    assert 'observation_invalid' in evaluate_admission(**inputs).reasons
    policy = inputs['policy'].model_copy(update={'ram_limit_bytes': 0})
    assert evaluate_admission(**(inputs | {'policy': policy})).reasons == ('input_invalid',)
    with pytest.raises(ValueError, match='Invalid admission policy'):
        admission_policy_sha256(policy)


@pytest.mark.parametrize(
    'case', ['empty', 'too_many', 'list', 'dict', 'bad_item', 'bad_context', 'age_zero']
)
def test_snapshot_input_boundaries(inputs, case):
    changes = {
        'empty': {'observations': ()},
        'too_many': {'observations': inputs['observations'] * 2},
        'list': {'observations': list(inputs['observations'])},
        'dict': {'observations': {}},
        'bad_item': {'observations': (None,)},
        'bad_context': {'context': inputs['context'].model_copy(update={'origin': 'bad'})},
        'age_zero': {'max_age_seconds': 0},
    }
    result = evaluate_admission(**(inputs | changes[case]))
    assert result.action == 'deny'


def test_target_claims_are_not_fixture_promotion(inputs):
    # Synthetic data describing target claims is not actual target evidence.
    context = inputs['context'].model_copy(update={'mode': 'live'})
    observations = tuple(
        o.model_copy(update={'context': context, 'source': 'target'})
        for o in inputs['observations']
    )
    target = inputs | {
        'context': context,
        'expected_source': 'target',
        'observations': observations,
    }
    result = evaluate_admission(**target)
    assert result.action == 'allow' and result.source == 'target'
    for changes in (
        {'expected_source': 'fixture'},
        {'observations': inputs['observations']},
        {'context': inputs['context']},
    ):
        assert evaluate_admission(**(target | changes)).action == 'deny'
    assert evaluate_admission(**(inputs | {'context': context})).action == 'deny'


def test_restart_clock_session_and_determinism(inputs):
    result = evaluate_admission(**inputs)
    assert evaluate_admission(**inputs) == result
    changed = inputs | {'clock_session_id': OTHER_UUID}
    assert evaluate_admission(**changed).reasons == ('clock_session_mismatch',)
    # Stable reason ordering independent of capability order; no raw values copied.
    change_observation(inputs, status='unknown', worker_id='other', checked_at=0.0)
    one = evaluate_admission(**inputs)
    two = evaluate_admission(**(inputs | {'observations': tuple(reversed(inputs['observations']))}))
    assert one == two and len(one.reasons) <= 14


@pytest.mark.parametrize('location', ['expected_context', 'observed_context', 'policy'])
def test_forged_extra_fields_cannot_disappear_during_revalidation(inputs, location):
    if location == 'policy':
        inputs['policy'] = inputs['policy'].model_copy(update={'secret': 'synthetic-secret'})
    else:
        forged = inputs['context'].model_copy(update={'secret': 'synthetic-secret'})
        if location == 'expected_context':
            inputs['context'] = forged
        else:
            change_observation(inputs, context=forged)
    result = evaluate_admission(**inputs)
    assert result.action == 'deny' and 'synthetic-secret' not in repr(result)


def test_missing_fields_on_constructed_observation_fail_closed(inputs):
    inputs['observations'] = (
        ComfyAdmissionObservation.model_construct(capability='runtime_native'),
    )
    result = evaluate_admission(**inputs)
    assert result.action == 'deny' and 'observation_invalid' in result.reasons
