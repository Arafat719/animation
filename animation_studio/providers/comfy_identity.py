"""Offline journal identity parsing. No file writes, transport or live activation."""

import ipaddress
import json
import re
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from animation_studio.providers.comfy_journal import ComfyJobRecord

MAX_RECORD_BYTES = 4096


def canonical_origin(value: str) -> str:
    """Normalize an explicit HTTPS root origin without resolving any host."""
    if type(value) is not str or not value.isascii() or any(c.isspace() for c in value):
        raise ValueError('Invalid origin')
    if any(ord(c) < 32 or ord(c) == 127 for c in value) or any(c in value for c in '@?#%\\'):
        raise ValueError('Invalid origin')
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or parsed.path not in ('', '/') or not parsed.hostname:
        raise ValueError('Expected HTTPS root origin')
    if not re.fullmatch(r'(?:\[[0-9a-fA-F:]+\]|[a-zA-Z0-9.-]+)(?::[0-9]+)?', parsed.netloc):
        raise ValueError('Invalid origin authority')
    host = parsed.hostname
    port = parsed.port
    if parsed.netloc.endswith(':') or (port is not None and not 1 <= port <= 65535):
        raise ValueError('Invalid origin port')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # Reject legacy numeric IP spellings and DNS names with ambiguous empty labels.
        if len(host) > 253 or re.fullmatch(r'[0-9.]+', host):
            raise ValueError('Invalid origin host') from None
        labels = host.split('.')
        if any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', x) for x in labels):
            raise ValueError('Invalid origin host') from None
        if labels[-1].isdigit() or re.fullmatch(r'0x[0-9a-f]+', labels[-1]):
            raise ValueError('Ambiguous origin host')
    else:
        if address.is_unspecified:
            raise ValueError('Unspecified origin host')
        host = f'[{address.compressed}]' if address.version == 6 else str(address)
    return f'https://{host}:{port or 443}/'


class ComfyJobRecordV2(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)
    schema_version: Literal[2]
    mode: Literal['mock', 'live']
    job_id: str
    graph_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    origin: str
    deployment_id: str
    runtime_manifest_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    model_manifest_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    state: Literal['intent', 'accepted']
    prompt_id: str | None = None

    @field_validator('schema_version', mode='before')
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int:
            raise ValueError('Invalid journal version')
        return value

    @field_validator('job_id', 'deployment_id', 'prompt_id')
    @classmethod
    def canonical_uuid(cls, value):
        if value is not None and str(UUID(value)) != value:
            raise ValueError('Expected canonical UUID')
        return value

    @field_validator('origin')
    @classmethod
    def stored_origin(cls, value):
        if canonical_origin(value) != value:
            raise ValueError('Journal origin must be canonical')
        return value

    @model_validator(mode='after')
    def coherent(self):
        if (self.state == 'accepted') != (self.prompt_id is not None):
            raise ValueError('Receipt does not match journal state')
        return self


def parse_job_record(content: bytes, *, expected_mode: Literal['mock', 'live']):
    """Parse bounded bytes; v1 stays v1 and is never eligible for live recovery.

    This only validates records, not deployment attestation or recovery context.
    The caller must separately match all execution identity fields before I/O.
    """
    try:
        if expected_mode not in ('mock', 'live') or type(expected_mode) is not str:
            raise ValueError
        if type(content) is not bytes or len(content) > MAX_RECORD_BYTES:
            raise ValueError

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError
                result[key] = value
            return result

        def reject_constant(value):
            raise ValueError

        data = json.loads(content, object_pairs_hook=unique, parse_constant=reject_constant)
        if not isinstance(data, dict) or type(data.get('schema_version')) is not int:
            raise ValueError
        version = data['schema_version']
        if version == 1:
            record = ComfyJobRecord.model_validate(data)
        elif version == 2:
            record = ComfyJobRecordV2.model_validate(data)
        else:
            raise ValueError
        if record.mode != expected_mode:
            raise ValueError
        return record
    except (ValueError, TypeError, RecursionError):
        # Do not echo untrusted content (which could contain a misplaced secret).
        raise ValueError('Invalid or incompatible Comfy journal') from None


class ComfyExecutionContext(BaseModel):
    """Original trusted execution identity, supplied independently of the journal.

    No credentials or current inventory belong here. Validation is local syntax
    checking, not proof that a deployment or its manifest has been verified.
    """

    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)
    mode: Literal['mock', 'live']
    job_id: str
    graph_sha256: str
    origin: str
    deployment_id: str
    runtime_manifest_sha256: str
    model_manifest_sha256: str

    @model_validator(mode='after')
    def valid_identity(self):
        # Reuse the stored identity rules without adding journal state to context.
        ComfyJobRecordV2.model_validate(dict(self.model_dump(), schema_version=2, state='intent'))
        return self


def match_job_context(content: bytes, context: ComfyExecutionContext) -> ComfyJobRecordV2:
    """Read v2 bytes only when every field matches independent trusted context.

    Intent remains intent: matching does not authorize resubmission or recovery.
    A recovery caller must additionally require accepted state. Legacy v1 stays
    on its separate mock recovery path. No inventory, filesystem or network I/O.
    """
    try:
        if type(context) is not ComfyExecutionContext:
            raise ValueError
        # Revalidate even instances built via model_construct/model_copy.
        expected = ComfyExecutionContext.model_validate(context.model_dump()).model_dump()
        record = parse_job_record(content, expected_mode=expected['mode'])
        if type(record) is not ComfyJobRecordV2:
            raise ValueError
        if any(getattr(record, field) != value for field, value in expected.items()):
            raise ValueError
        return record
    except (ValueError, TypeError, RecursionError):
        raise ValueError('Comfy journal execution context mismatch') from None
