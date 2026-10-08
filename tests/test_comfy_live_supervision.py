"""Synthetic live-mode records only; no real endpoint or stop evidence."""

import json
import socket

import pytest
from pydantic import ValidationError

from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_supervision import (
    ComfySupervisionObservation,
    LiveComfySupervisionObservation,
    parse_live_supervision_observation,
    parse_supervision_observation,
)

UUID = '12345678-1234-4234-8234-123456789abc'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Offline schema must not use network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


@pytest.fixture
def context():
    return ComfyExecutionContext(
        mode='live',
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
        'schema_version': 2,
        'context': context.model_dump(),
        'primary_outcome': 'timeout',
        'cleanup_phase': 'not_requested',
        'attempt_count': 0,
        'created_at': 100,
        'updated_at': 100,
        'source': 'none',
    }


@pytest.mark.parametrize(
    'phase,count',
    [
        ('not_requested', 0),
        ('intent', 1),
        ('unknown', 0),
        ('unknown', 1),
        ('observed', 1),
    ],
)
def test_roundtrip_frozen_and_mock_parser_rejection(context, record, phase, count):
    record.update(cleanup_phase=phase, attempt_count=count)
    if phase == 'observed':
        record.update(source='live', evidence_sha256='d' * 64)
    content = json.dumps(record).encode()
    result = parse_live_supervision_observation(content, context)
    assert type(result) is LiveComfySupervisionObservation
    assert result.primary_outcome == 'timeout' and result.compute_status == 'unknown'
    assert parse_live_supervision_observation(result.model_dump_json().encode(), context) == result
    with pytest.raises(ValidationError):
        result.attempt_count = 1
    with pytest.raises(ValueError):
        parse_supervision_observation(content, context)


@pytest.mark.parametrize('ack', [True, False])
def test_ack_is_not_stop_proof(context, record, ack):
    record.update(
        cleanup_phase='observed',
        attempt_count=1,
        source='live',
        evidence_sha256='d' * 64,
        prompt_id=UUID,
        cancel_dispatched=ack,
    )
    result = parse_live_supervision_observation(json.dumps(record).encode(), context)
    assert all(
        getattr(result, field) == 'unknown'
        for field in (
            'job_status',
            'worker_status',
            'compute_status',
            'storage_status',
        )
    )


@pytest.mark.parametrize(
    'change',
    [
        {'schema_version': 1},
        {'schema_version': True},
        {'schema_version': 2.0},
        {'source': 'mock'},
        {'source': 'live'},
        {'token': 'synthetic-secret'},
        {'attempt_count': True},
        {'attempt_count': 2},
        {'attempt_count': 1},
        {'created_at': -1},
        {'updated_at': 99},
        {'updated_at': 253402300800},
        {'primary_outcome': 'private-error'},
        {'prompt_id': 'bad'},
        {'compute_status': 'stopped'},
        {'cleanup_phase': 'intent'},
        {'cleanup_phase': 'observed', 'attempt_count': 1, 'source': 'live'},
        {
            'cleanup_phase': 'observed',
            'attempt_count': 1,
            'source': 'mock',
            'evidence_sha256': 'd' * 64,
        },
        {
            'cleanup_phase': 'observed',
            'attempt_count': 1,
            'source': 'live',
            'evidence_sha256': 'd' * 64,
            'cancel_dispatched': True,
        },
    ],
)
def test_invalid_and_secret_safe(context, record, change):
    with pytest.raises(ValueError) as caught:
        parse_live_supervision_observation(json.dumps(record | change).encode(), context)
    assert str(caught.value) == 'Invalid or incompatible Comfy supervision observation'


@pytest.mark.parametrize(
    'field,value',
    [
        ('mode', 'mock'),
        ('job_id', '22345678-1234-4234-8234-123456789abc'),
        ('deployment_id', '22345678-1234-4234-8234-123456789abc'),
        ('origin', 'https://different.invalid:443/'),
        ('graph_sha256', 'd' * 64),
        ('runtime_manifest_sha256', 'd' * 64),
        ('model_manifest_sha256', 'd' * 64),
    ],
)
def test_every_identity_field(context, record, field, value):
    changed = context.model_copy(update={field: value})
    with pytest.raises(ValueError):
        parse_live_supervision_observation(json.dumps(record).encode(), changed)
    record['context'][field] = value
    with pytest.raises(ValueError):
        parse_live_supervision_observation(json.dumps(record).encode(), context)


@pytest.mark.parametrize(
    'content',
    [
        b'',
        b'[]',
        b'null',
        b'\xff',
        b'x' * 4097,
        b'{"schema_version":2,"schema_version":2}',
        b'{"created_at":NaN}',
        b'[' * 1100 + b']' * 1100,
        'not bytes',
        None,
    ],
)
def test_bounded_malformed_input(context, content):
    with pytest.raises(ValueError):
        parse_live_supervision_observation(content, context)


def test_exact_cap_nested_duplicate_and_bypassed_validation(context, record):
    content = json.dumps(record).encode()
    assert parse_live_supervision_observation(content.ljust(4096), context)
    with pytest.raises(ValueError):
        parse_live_supervision_observation(content.ljust(4097), context)
    duplicate = content.replace(b'"mode": "live"', b'"mode":"live","mode":"live"')
    with pytest.raises(ValueError):
        parse_live_supervision_observation(duplicate, context)
    result = LiveComfySupervisionObservation(**record)
    with pytest.raises(ValidationError):
        LiveComfySupervisionObservation.model_validate(result.model_copy(update={'source': 'mock'}))


@pytest.mark.parametrize('phase', ['not_requested', 'intent', 'observed', 'unknown'])
def test_v1_backward_read_no_automatic_migration(context, record, phase):
    mock = context.model_copy(update={'mode': 'mock'})
    record.update(
        schema_version=1,
        context=mock.model_dump(),
        cleanup_phase=phase,
        attempt_count=0 if phase == 'not_requested' else 1,
    )
    if phase == 'observed':
        record.update(source='mock', evidence_sha256='d' * 64)
    content = json.dumps(record).encode()
    assert type(parse_supervision_observation(content, mock)) is ComfySupervisionObservation
    for expected in (mock, context):
        with pytest.raises(ValueError):
            parse_live_supervision_observation(content, expected)
    # Changing just the discriminator must not promote old mock data to live.
    record['schema_version'] = 2
    with pytest.raises(ValueError):
        parse_live_supervision_observation(json.dumps(record).encode(), context)
