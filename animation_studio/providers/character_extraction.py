"""Explicit fixture boundary; no natural-language inference, persistence or I/O."""

from collections.abc import Iterable
from types import MappingProxyType
from typing import Protocol

from animation_studio.domain.v1.character_extraction import (
    ExtractionCandidate,
    ExtractionReport,
    ExtractionRequest,
    ProviderIdentity,
    build_extraction_report,
    request_fingerprint,
)


class CharacterProfileExtractionProvider(Protocol):
    def extract(self, request: ExtractionRequest) -> ExtractionCandidate: ...


class FixtureNotFound(LookupError):
    pass


class FixtureExtractionProvider:
    identity = ProviderIdentity(
        provider_id='fixture-extraction', provider_version='1', is_mock=True
    )

    def __init__(self, fixtures: Iterable[tuple[ExtractionRequest, ExtractionCandidate]]):
        records = {}
        for request, candidate in fixtures:
            report = build_extraction_report(request, candidate, provider=self.identity)
            if report.request_hash in records:
                raise ValueError('Duplicate fixture request')
            records[report.request_hash] = report
        self._records = MappingProxyType(records)

    def extract(self, request: ExtractionRequest) -> ExtractionCandidate:
        request = ExtractionRequest.model_validate(request)
        record = self._records.get(request_fingerprint(request))
        if record is None or record.request != request:
            raise FixtureNotFound('No extraction fixture for this request')
        return ExtractionCandidate.model_validate(record.candidate)

    def report(self, request: ExtractionRequest) -> ExtractionReport:
        return build_extraction_report(
            request,
            self.extract(request),
            provider=ProviderIdentity(
                provider_id='fixture-extraction', provider_version='1', is_mock=True
            ),
        )
