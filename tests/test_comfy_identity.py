import json

import pytest
from pydantic import ValidationError

from animation_studio.providers.comfy_identity import (
    ComfyExecutionContext,
    ComfyJobRecordV2,
    canonical_origin,
    match_job_context,
    parse_job_record,
)
from animation_studio.providers.comfy_journal import ComfyJobRecord

UUID = '12345678-1234-5678-9abc-123456789abc'


@pytest.fixture
def record():
    return {
        'schema_version': 2,
        'mode': 'mock',
        'job_id': UUID,
        'graph_sha256': 'a' * 64,
        'origin': 'https://comfy.invalid:443/',
        'deployment_id': UUID,
        'runtime_manifest_sha256': 'b' * 64,
        'model_manifest_sha256': 'c' * 64,
        'state': 'intent',
    }


@pytest.mark.parametrize('mode', ['mock', 'live'])
@pytest.mark.parametrize('state', ['intent', 'accepted'])
def test_roundtrip(record, mode, state):
    record.update(mode=mode, state=state)
    if state == 'accepted':
        record['prompt_id'] = UUID
    parsed = parse_job_record(json.dumps(record).encode(), expected_mode=mode)
    assert isinstance(parsed, ComfyJobRecordV2)
    assert parse_job_record(parsed.model_dump_json().encode(), expected_mode=mode) == parsed
    with pytest.raises(ValidationError):
        parsed.mode = 'live'


@pytest.mark.parametrize('state', ['intent', 'accepted'])
def test_legacy_preserved(tmp_path, state):
    data = {'schema_version': 1, 'mode': 'mock', 'graph_sha256': 'a' * 64, 'state': state}
    if state == 'accepted':
        data['prompt_id'] = UUID
    content = json.dumps(data).encode()
    path = tmp_path / 'legacy.json'
    path.write_bytes(content)
    parsed = parse_job_record(path.read_bytes(), expected_mode='mock')
    assert type(parsed) is ComfyJobRecord and parsed.schema_version == 1
    assert parsed.prompt_id == (UUID if state == 'accepted' else None)
    assert path.read_bytes() == content
    with pytest.raises(ValueError):
        parse_job_record(content, expected_mode='live')


@pytest.mark.parametrize(
    'source, expected',
    [
        ('https://COMFY.invalid', 'https://comfy.invalid:443/'),
        ('https://comfy.invalid:443/', 'https://comfy.invalid:443/'),
        ('https://127.0.0.1:8443', 'https://127.0.0.1:8443/'),
        ('https://[2001:0db8::1]', 'https://[2001:db8::1]:443/'),
    ],
)
def test_origin_normalization(source, expected):
    assert canonical_origin(source) == expected


@pytest.mark.parametrize(
    'origin',
    [
        'https://[::1]other',
        'https://host:+443',
        'http://host/',
        'https://user:secret@host/',
        'https://host/?',
        'https://host/#',
        'https://host/path',
        'https://host\\other',
        'https://host\n',
        'https://host\x00',
        'https://',
        'https://host:',
        'https://host:0',
        'https://host:65536',
        'https://0.0.0.0',
        'https://[::]',
        'https://127.1',
        'https://2130706433',
        'https://0x7f000001',
        'https://0x7f.0.0.1',
        'https://host.',
        'https://a..b',
        'https://-host',
        'https://বাংলা',
        'https://[fe80::1%25eth0]',
    ],
)
def test_invalid_origins(origin):
    with pytest.raises(ValueError):
        canonical_origin(origin)


@pytest.mark.parametrize(
    'field, value',
    [
        ('schema_version', True),
        ('schema_version', 2.0),
        ('schema_version', 3),
        ('mode', 'other'),
        ('job_id', UUID.upper()),
        ('deployment_id', '../job'),
        ('graph_sha256', 'A' * 64),
        ('runtime_manifest_sha256', 'x' * 64),
        ('model_manifest_sha256', 'c' * 63),
        ('origin', 'https://comfy.invalid'),
        ('prompt_id', UUID),
        ('state', 'done'),
        ('secret', 'DO-NOT-ECHO'),
    ],
)
def test_invalid_record(record, field, value):
    record[field] = value
    with pytest.raises(ValueError, match='Invalid or incompatible') as error:
        parse_job_record(json.dumps(record).encode(), expected_mode='mock')
    assert 'DO-NOT-ECHO' not in str(error.value)


@pytest.mark.parametrize(
    'field',
    [
        'schema_version',
        'mode',
        'job_id',
        'graph_sha256',
        'origin',
        'deployment_id',
        'runtime_manifest_sha256',
        'model_manifest_sha256',
        'state',
    ],
)
def test_required_identity(record, field):
    del record[field]
    with pytest.raises(ValueError):
        parse_job_record(json.dumps(record).encode(), expected_mode='mock')


@pytest.mark.parametrize('receipt', [None, 'bad', UUID.upper()])
def test_accepted_requires_canonical_receipt(record, receipt):
    record.update(state='accepted', prompt_id=receipt)
    with pytest.raises(ValueError):
        parse_job_record(json.dumps(record).encode(), expected_mode='mock')


@pytest.mark.parametrize(
    'content',
    [
        b'',
        b'[]',
        b'null',
        b'{}',
        b'\xff',
        b'{',
        b'x' * 4097,
        b'{"schema_version":2,"schema_version":1}',
        b'{"schema_version":NaN}',
        b'{"schema_version":Infinity}',
        b'[' * 2000,
    ],
)
def test_malformed(content):
    with pytest.raises(ValueError):
        parse_job_record(content, expected_mode='mock')


def test_mode_and_size_boundaries(record):
    content = json.dumps(record).encode()
    assert parse_job_record(content.ljust(4096), expected_mode='mock').state == 'intent'
    for mode in ('live', 'other', None):
        with pytest.raises(ValueError):
            parse_job_record(content, expected_mode=mode)
    with pytest.raises(ValueError):
        parse_job_record(content.ljust(4097), expected_mode='mock')


@pytest.fixture
def context(record):
    return ComfyExecutionContext(
        **{key: value for key, value in record.items() if key not in ('schema_version', 'state')}
    )


@pytest.mark.parametrize('mode', ['mock', 'live'])
@pytest.mark.parametrize('state', ['intent', 'accepted'])
def test_matching_context_offline(record, context, mode, state, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('Identity matching must not use network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    record.update(mode=mode, state=state)
    if state == 'accepted':
        record['prompt_id'] = UUID
    context = ComfyExecutionContext(**(context.model_dump() | {'mode': mode}))
    content = json.dumps(record).encode()
    matched = match_job_context(content, context)
    assert matched.state == state
    assert matched.prompt_id == (UUID if state == 'accepted' else None)
    assert json.loads(content) == record
    with pytest.raises(ValidationError):
        context.job_id = UUID


@pytest.mark.parametrize(
    'field,value',
    [
        ('mode', 'live'),
        ('job_id', '87654321-1234-5678-9abc-123456789abc'),
        ('graph_sha256', 'd' * 64),
        ('origin', 'https://other.invalid:443/'),
        ('deployment_id', '87654321-1234-5678-9abc-123456789abc'),
        ('runtime_manifest_sha256', 'd' * 64),
        ('model_manifest_sha256', 'd' * 64),
    ],
)
@pytest.mark.parametrize('side', ['journal', 'context'])
def test_each_identity_mismatch(record, context, field, value, side):
    record.update(state='accepted', prompt_id=UUID)
    if side == 'journal':
        record[field] = value
    else:
        context = ComfyExecutionContext(**(context.model_dump() | {field: value}))
    with pytest.raises(ValueError, match='execution context mismatch'):
        match_job_context(json.dumps(record).encode(), context)


@pytest.mark.parametrize('state', ['intent', 'accepted'])
def test_matching_never_upgrades_legacy(context, state):
    data = {'schema_version': 1, 'mode': 'mock', 'graph_sha256': 'a' * 64, 'state': state}
    if state == 'accepted':
        data['prompt_id'] = UUID
    with pytest.raises(ValueError):
        match_job_context(json.dumps(data).encode(), context)


@pytest.mark.parametrize('field', list(ComfyExecutionContext.model_fields))
def test_context_requires_every_field(context, field):
    data = context.model_dump()
    del data[field]
    with pytest.raises(ValidationError):
        ComfyExecutionContext(**data)


@pytest.mark.parametrize(
    'field,value',
    [
        ('mode', True),
        ('job_id', '../bad'),
        ('origin', 'https://comfy.invalid'),
        ('graph_sha256', 'bad'),
        ('deployment_id', UUID.upper()),
        ('runtime_manifest_sha256', 'B' * 64),
        ('model_manifest_sha256', 'bad'),
        ('token', 'DO-NOT-ECHO'),
    ],
)
def test_invalid_context_even_bypassed(record, context, field, value):
    data = context.model_dump() | {field: value}
    with pytest.raises(ValidationError):
        ComfyExecutionContext(**data)
    if field != 'token':
        forged = context.model_copy(update={field: value})
        with pytest.raises(ValueError, match='execution context mismatch'):
            match_job_context(json.dumps(record).encode(), forged)


@pytest.mark.parametrize('content', [b'bad', b'x' * 4097, b'{"token":"DO-NOT-ECHO"}'])
def test_match_parse_errors_sanitized(context, content):
    with pytest.raises(ValueError) as error:
        match_job_context(content, context)
    assert str(error.value) == 'Comfy journal execution context mismatch'


def test_context_is_independent_and_exact_type(record, context):
    with pytest.raises(ValueError):
        match_job_context(json.dumps(record).encode(), context.model_dump())
    forged = ComfyExecutionContext.model_construct(mode='mock')
    with pytest.raises(ValueError):
        match_job_context(json.dumps(record).encode(), forged)
