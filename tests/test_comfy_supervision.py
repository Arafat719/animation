import json
import socket

import pytest
from pydantic import ValidationError

from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_supervision import (
    ComfySupervisionObservation,
    ComfySupervisionPolicy,
    parse_supervision_observation,
)

UUID = '12345678-1234-4234-8234-123456789abc'


@pytest.fixture
def context():
    return ComfyExecutionContext(
        mode='mock',
        job_id=UUID,
        graph_sha256='a' * 64,
        origin='https://selected.invalid:443/',
        deployment_id=UUID,
        runtime_manifest_sha256='b' * 64,
        model_manifest_sha256='c' * 64,
    )


@pytest.fixture
def record(context):
    return {
        'schema_version': 1,
        'context': context.model_dump(),
        'primary_outcome': 'timeout',
        'cleanup_phase': 'not_requested',
        'attempt_count': 0,
        'created_at': 100,
        'updated_at': 100,
        'source': 'none',
    }


@pytest.fixture
def policy():
    return {
        'ram_limit_bytes': 1024,
        'host_reserve_bytes': 512,
        'device_index': 0,
        'vram_limit_bytes': 1024,
        'sample_interval_seconds': 1.0,
        'stale_after_seconds': 2.0,
        'overall_timeout_seconds': 60.0,
        'cleanup_reserve_seconds': 5.0,
        'reap_allowance_seconds': 5.0,
    }


@pytest.mark.parametrize('field', ['ram_limit_bytes', 'host_reserve_bytes', 'vram_limit_bytes'])
@pytest.mark.parametrize('value', [True, 0, -1, 1.5, '100'])
def test_byte_policy_rejected(policy, field, value):
    policy[field] = value
    with pytest.raises(ValidationError):
        ComfySupervisionPolicy(**policy)


@pytest.mark.parametrize(
    'field',
    [
        'sample_interval_seconds',
        'stale_after_seconds',
        'overall_timeout_seconds',
        'cleanup_reserve_seconds',
        'reap_allowance_seconds',
    ],
)
@pytest.mark.parametrize('value', [True, 0, -1, float('nan'), float('inf'), '5'])
def test_time_policy_rejected(policy, field, value):
    policy[field] = value
    with pytest.raises(ValidationError):
        ComfySupervisionPolicy(**policy)


@pytest.mark.parametrize(
    'change',
    [
        {'overall_timeout_seconds': 10.0},
        {'stale_after_seconds': 0.5},
        {'device_index': True},
        {'device_index': -1},
        {'extra': 1},
    ],
)
def test_policy_consistency(policy, change):
    with pytest.raises(ValidationError):
        ComfySupervisionPolicy(**(policy | change))


def test_pure_roundtrip_and_frozen(policy, record, context, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    validated = ComfySupervisionPolicy(**policy)
    observation = ComfySupervisionObservation(**record)
    content = observation.model_dump_json().encode()
    assert parse_supervision_observation(content, context) == observation
    assert observation.compute_status == observation.job_status == 'unknown'
    with pytest.raises(ValidationError):
        validated.ram_limit_bytes = 1
    with pytest.raises(ValidationError):
        observation.attempt_count = 1
    # Revalidation also rejects bypassed instances.
    with pytest.raises(ValidationError):
        ComfySupervisionPolicy.model_validate(validated.model_copy(update={'device_index': -1}))


@pytest.mark.parametrize(
    'change',
    [
        {'schema_version': True},
        {'schema_version': 1.0},
        {'schema_version': 2},
        {'attempt_count': True},
        {'attempt_count': 2},
        {'attempt_count': 1},
        {'created_at': -1},
        {'created_at': True},
        {'updated_at': 99},
        {'updated_at': 253402300800},
        {'source': 'live'},
        {'token': 'synthetic-secret'},
        {'primary_outcome': 'arbitrary error'},
        {'prompt_id': 'bad'},
        {'cleanup_phase': 'intent'},
        {'compute_status': 'stopped'},
        {'cancel_dispatched': True},
        {'evidence_sha256': 'a' * 64},
        {'cleanup_phase': 'observed', 'attempt_count': 1, 'source': 'mock'},
    ],
)
def test_invalid_observation(record, context, change):
    with pytest.raises(ValueError, match='Invalid or incompatible') as caught:
        parse_supervision_observation(json.dumps(record | change).encode(), context)
    assert 'synthetic-secret' not in str(caught.value)


@pytest.mark.parametrize('ack', [True, False])
def test_cancel_ack_does_not_prove_stop(record, context, ack):
    record.update(
        cleanup_phase='observed',
        attempt_count=1,
        source='mock',
        prompt_id=UUID,
        cancel_dispatched=ack,
        evidence_sha256='d' * 64,
    )
    result = parse_supervision_observation(json.dumps(record).encode(), context)
    assert result.job_status == result.compute_status == result.storage_status == 'unknown'
    record['prompt_id'] = None
    with pytest.raises(ValueError):
        parse_supervision_observation(json.dumps(record).encode(), context)


@pytest.mark.parametrize(
    'status,value',
    [
        ('job_status', 'terminal'),
        ('worker_status', 'exited'),
        ('compute_status', 'stopped'),
        ('storage_status', 'absent'),
    ],
)
def test_statuses_are_independent_mock_claims(record, context, status, value):
    record.update(
        cleanup_phase='observed',
        attempt_count=1,
        source='mock',
        prompt_id=UUID,
        evidence_sha256='d' * 64,
    )
    record[status] = value
    result = parse_supervision_observation(json.dumps(record).encode(), context)
    for field in ('job_status', 'worker_status', 'compute_status', 'storage_status'):
        assert getattr(result, field) == (value if field == status else 'unknown')


@pytest.mark.parametrize('phase,count', [('intent', 1), ('unknown', 0), ('unknown', 1)])
def test_ambiguous_states_preserved(record, context, phase, count):
    record.update(cleanup_phase=phase, attempt_count=count)
    result = parse_supervision_observation(json.dumps(record).encode(), context)
    assert result.prompt_id is None and result.compute_status == 'unknown'
    assert result.primary_outcome == 'timeout'


@pytest.mark.parametrize(
    'field,value',
    [
        ('mode', 'live'),
        ('job_id', '22345678-1234-4234-8234-123456789abc'),
        ('deployment_id', '22345678-1234-4234-8234-123456789abc'),
        ('origin', 'https://other.invalid:443/'),
        ('graph_sha256', 'd' * 64),
        ('runtime_manifest_sha256', 'd' * 64),
        ('model_manifest_sha256', 'd' * 64),
    ],
)
def test_every_context_field_matched(record, context, field, value):
    changed = context.model_copy(update={field: value})
    with pytest.raises(ValueError):
        parse_supervision_observation(json.dumps(record).encode(), changed)
    record['context'][field] = value
    with pytest.raises(ValueError):
        parse_supervision_observation(json.dumps(record).encode(), context)


@pytest.mark.parametrize(
    'content',
    [
        b'',
        b'[]',
        b'null',
        b'\xff',
        b'{}' + b' ' * 4095,
        b'{"schema_version":1,"schema_version":1}',
        b'{"created_at":NaN}',
        b'[' * 1100 + b']' * 1100,
        'not bytes',
        None,
    ],
)
def test_malformed_bounded_input(context, content):
    with pytest.raises(ValueError, match='Invalid or incompatible'):
        parse_supervision_observation(content, context)


def test_nested_duplicate_and_exact_byte_cap(record, context):
    content = json.dumps(record).encode()
    assert parse_supervision_observation(content + b' ' * (4096 - len(content)), context)
    duplicate = content.replace(b'"mode": "mock"', b'"mode":"mock","mode":"mock"')
    with pytest.raises(ValueError):
        parse_supervision_observation(duplicate, context)
    record['context'] = context.model_copy(update={'job_id': 'bad'})
    with pytest.raises(ValidationError):
        ComfySupervisionObservation(**record)


def test_live_observation_rejected_even_with_matching_context(record, context):
    live = context.model_copy(update={'mode': 'live'})
    record['context'] = live.model_dump()
    with pytest.raises(ValueError):
        parse_supervision_observation(json.dumps(record).encode(), live)


def test_success_and_cleanup_unknown_are_independent(record, context):
    record.update(primary_outcome='success', cleanup_phase='unknown', attempt_count=1)
    result = parse_supervision_observation(json.dumps(record).encode(), context)
    assert result.primary_outcome == 'success'
    assert result.compute_status == 'unknown'
