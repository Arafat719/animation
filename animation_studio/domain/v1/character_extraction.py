"""Review-only extractive suggestions, separate from persisted manual profiles."""

import hashlib
import json
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

TraitField = Literal['face', 'hair', 'eyes', 'outfit', 'colors', 'accessories', 'negative_traits']
REQUIRED = ('face', 'hair', 'eyes', 'outfit', 'colors')
FIELDS = (*REQUIRED, 'accessories', 'negative_traits')
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class ExtractionModel(BaseModel):
    model_config = ConfigDict(
        strict=True, frozen=True, extra='forbid', revalidate_instances='always'
    )


class ExtractionRequest(ExtractionModel):
    schema_version: Literal[1] = 1
    character_id: int = Field(gt=0, le=2**63 - 1)
    name: Name
    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
    ]

    @field_validator('schema_version', mode='before')
    @classmethod
    def version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError('Unsupported request version')
        return value


def request_fingerprint(request: ExtractionRequest) -> str:
    request = ExtractionRequest.model_validate(request)
    encoded = json.dumps(
        request.model_dump(), ensure_ascii=False, sort_keys=True, separators=(',', ':')
    ).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


class EvidenceValue(ExtractionModel):
    value: str = Field(min_length=1, max_length=500)
    start: int = Field(ge=0, le=3999)
    end: int = Field(gt=0, le=4000)

    @model_validator(mode='after')
    def span(self):
        if (
            not self.value.strip()
            or self.end <= self.start
            or self.end - self.start != len(self.value)
        ):
            raise ValueError('Invalid evidence span')
        return self


class ExtractionCandidate(ExtractionModel):
    face: EvidenceValue | None = None
    hair: EvidenceValue | None = None
    eyes: EvidenceValue | None = None
    outfit: EvidenceValue | None = None
    colors: tuple[EvidenceValue, ...] = Field(default=(), max_length=20)
    accessories: tuple[EvidenceValue, ...] = Field(default=(), max_length=20)
    negative_traits: tuple[EvidenceValue, ...] = Field(default=(), max_length=100)
    ambiguous_fields: tuple[TraitField, ...] = Field(default=(), max_length=7)

    @model_validator(mode='after')
    def consistency(self):
        if len(set(self.ambiguous_fields)) != len(self.ambiguous_fields):
            raise ValueError('Duplicate ambiguous field')
        if any(getattr(self, field) for field in self.ambiguous_fields):
            raise ValueError('Ambiguous fields must have no suggestion')
        for field in ('colors', 'accessories', 'negative_traits'):
            items = getattr(self, field)
            spans = [(item.start, item.end, item.value) for item in items]
            if len(set(spans)) != len(spans) or spans != sorted(spans):
                raise ValueError('Evidence must be unique and in description order')
        return self


class ProviderIdentity(ExtractionModel):
    provider_id: Name
    provider_version: Name
    is_mock: bool


class ExtractionReport(ExtractionModel):
    request: ExtractionRequest
    request_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    candidate: ExtractionCandidate
    provider: ProviderIdentity
    missing_required: tuple[TraitField, ...]
    status: Literal['REVIEW_REQUIRED'] = 'REVIEW_REQUIRED'

    @model_validator(mode='after')
    def binding(self):
        if self.request_hash != request_fingerprint(self.request):
            raise ValueError('Request fingerprint mismatch')
        missing = tuple(field for field in REQUIRED if not getattr(self.candidate, field))
        if self.missing_required != missing:
            raise ValueError('Incorrect missing required fields')
        for field in FIELDS:
            value = getattr(self.candidate, field)
            items = value if isinstance(value, tuple) else (() if value is None else (value,))
            for item in items:
                if self.request.description[item.start : item.end] != item.value:
                    raise ValueError('Evidence does not match description')
        return self


def build_extraction_report(
    request: ExtractionRequest, candidate: ExtractionCandidate, *, provider: ProviderIdentity
) -> ExtractionReport:
    request = ExtractionRequest.model_validate(request)
    candidate = ExtractionCandidate.model_validate(candidate)
    return ExtractionReport(
        request=request,
        request_hash=request_fingerprint(request),
        candidate=candidate,
        provider=provider,
        missing_required=tuple(field for field in REQUIRED if not getattr(candidate, field)),
    )


def validate_extraction_report(
    report: ExtractionReport,
    *,
    expected_request: ExtractionRequest,
    expected_provider: ProviderIdentity,
) -> ExtractionReport:
    report = ExtractionReport.model_validate(report)
    expected_request = ExtractionRequest.model_validate(expected_request)
    expected_provider = ProviderIdentity.model_validate(expected_provider)
    if report.request != expected_request or report.provider != expected_provider:
        raise ValueError('Extraction report context mismatch')
    return report
