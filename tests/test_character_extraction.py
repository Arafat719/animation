import hashlib
import json

import pytest
from pydantic import ValidationError

from animation_studio.domain.v1.character_extraction import (
    EvidenceValue,
    ExtractionCandidate,
    ExtractionReport,
    ExtractionRequest,
    ProviderIdentity,
    request_fingerprint,
    validate_extraction_report,
)
from animation_studio.providers.character_extraction import (
    FixtureExtractionProvider,
    FixtureNotFound,
)


def request(description='গোল মুখ কালো চুল বাদামি চোখ নীল পোশাক নীল ঘড়ি লাল', **changes):
    return ExtractionRequest(character_id=1, name=' আলো ', description=description, **changes)


def evidence(req, value):
    start = req.description.index(value)
    return EvidenceValue(value=value, start=start, end=start + len(value))


def complete(req):
    return ExtractionCandidate(
        face=evidence(req, 'গোল মুখ'),
        hair=evidence(req, 'কালো চুল'),
        eyes=evidence(req, 'বাদামি চোখ'),
        outfit=evidence(req, 'নীল পোশাক'),
        colors=(evidence(req, 'নীল'),),
        accessories=(evidence(req, 'ঘড়ি'),),
        negative_traits=(evidence(req, 'লাল'),),
    )


def test_unicode_complete_fixture_and_binding():
    req = request()
    provider = FixtureExtractionProvider([(req, complete(req))])
    report = provider.report(req)
    assert report.request.name == 'আলো'
    assert report.missing_required == ()
    assert report.status == 'REVIEW_REQUIRED' and report.provider.is_mock is True
    assert report == provider.report(req)
    assert ExtractionReport.model_validate_json(report.model_dump_json()) == report
    expected = hashlib.sha256(
        json.dumps(
            req.model_dump(), ensure_ascii=False, sort_keys=True, separators=(',', ':')
        ).encode()
    ).hexdigest()
    assert report.request_hash == expected
    assert (
        validate_extraction_report(
            report, expected_request=req, expected_provider=provider.identity
        )
        == report
    )
    with pytest.raises(ValidationError):
        report.candidate.hair.value = 'changed'


@pytest.mark.parametrize(
    'description,value',
    [('😀 e\u0301 hair', 'e\u0301'), ('black hair', 'black hair'), ('x' * 500, 'x' * 500)],
)
def test_codepoint_spans_and_boundaries(description, value):
    req = request(description)
    report = FixtureExtractionProvider(
        [(req, ExtractionCandidate(hair=evidence(req, value)))]
    ).report(req)
    assert report.candidate.hair.value == value
    assert report.missing_required == ('face', 'eyes', 'outfit', 'colors')


def test_unknown_and_ambiguity_do_not_invent_traits():
    req = request('Someone by the river')
    candidate = ExtractionCandidate(ambiguous_fields=('hair', 'accessories'))
    report = FixtureExtractionProvider([(req, candidate)]).report(req)
    assert report.missing_required == ('face', 'hair', 'eyes', 'outfit', 'colors')
    assert report.candidate.accessories == ()
    assert report.candidate.ambiguous_fields == ('hair', 'accessories')


@pytest.mark.parametrize(
    'change', [{'character_id': 2}, {'description': 'Other text'}, {'name': 'Other name'}]
)
def test_cross_request_and_unknown_fixture(change):
    req = request()
    provider = FixtureExtractionProvider([(req, complete(req))])
    other = ExtractionRequest.model_validate(req.model_dump() | change)
    assert request_fingerprint(req) != request_fingerprint(other)
    with pytest.raises(FixtureNotFound):
        provider.extract(other)
    with pytest.raises(ValueError):
        validate_extraction_report(
            provider.report(req), expected_request=other, expected_provider=provider.identity
        )


@pytest.mark.parametrize(
    'change',
    [
        {'character_id': True},
        {'character_id': '1'},
        {'character_id': 0},
        {'character_id': 2**63},
        {'schema_version': True},
        {'schema_version': 1.0},
        {'schema_version': 2},
        {'name': ' '},
        {'name': 'n' * 121},
        {'description': ' '},
        {'description': 'd' * 4001},
        {'extra': 1},
    ],
)
def test_request_rejects_invalid_and_unchecked_copies(change):
    req = request()
    with pytest.raises(ValidationError):
        ExtractionRequest.model_validate(req.model_copy(update=change))


@pytest.mark.parametrize(
    'change',
    [
        {'start': True},
        {'end': True},
        {'start': -1},
        {'end': 0},
        {'end': 4001},
        {'start': 3, 'end': 2},
        {'value': ''},
        {'value': ' '},
        {'value': 'x' * 501},
        {'value': 'xx'},
        {'extra': 'bad'},
    ],
)
def test_evidence_invalid(change):
    with pytest.raises(ValidationError):
        EvidenceValue.model_validate({'value': 'x', 'start': 0, 'end': 1} | change)


@pytest.mark.parametrize(
    'change',
    [
        {'ambiguous_fields': ('hair', 'hair')},
        {'ambiguous_fields': ('unknown',)},
        {'is_mock': False},
        {'source': 'user_provided'},
        {'colors': ()},
    ],
)
def test_candidate_rejection_or_valid_missing_color(change):
    req = request()
    if change == {'colors': ()}:
        result = FixtureExtractionProvider([(req, complete(req).model_copy(update=change))]).report(
            req
        )
        assert result.missing_required == ('colors',)
    else:
        with pytest.raises(ValidationError):
            ExtractionCandidate.model_validate(complete(req).model_copy(update=change))


def test_wrong_evidence_and_nested_unchecked_payloads():
    req = request('abc')
    wrong = EvidenceValue(value='xyz', start=0, end=3)
    with pytest.raises(ValidationError):
        FixtureExtractionProvider([(req, ExtractionCandidate(hair=wrong))])
    beyond = EvidenceValue(value='x', start=3, end=4)
    with pytest.raises(ValidationError):
        FixtureExtractionProvider([(req, ExtractionCandidate(hair=beyond))])
    bad = evidence(req, 'abc').model_copy(update={'start': True})
    candidate = ExtractionCandidate().model_copy(update={'hair': bad})
    with pytest.raises(ValidationError):
        FixtureExtractionProvider([(req, candidate)])


def test_list_order_duplicates_ambiguity_and_count_bounds():
    req = request(' '.join(str(i) for i in range(101)))
    values = tuple(evidence(req, str(i)) for i in range(101))
    for candidate in [
        {'colors': values[:21]},
        {'accessories': values[:21]},
        {'negative_traits': values},
        {'colors': (values[0], values[0])},
        {'colors': (values[1], values[0])},
        {'hair': values[0], 'ambiguous_fields': ('hair',)},
        {'colors': (values[0],), 'ambiguous_fields': ('colors',)},
    ]:
        with pytest.raises(ValidationError):
            ExtractionCandidate(**candidate)
    result = FixtureExtractionProvider(
        [
            (
                req,
                ExtractionCandidate(
                    colors=values[:20],
                    accessories=values[:20],
                    negative_traits=values[:100],
                ),
            )
        ]
    ).report(req)
    assert len(result.candidate.negative_traits) == 100


def test_tampered_report_metadata_and_fixture_duplicates():
    req = request()
    provider = FixtureExtractionProvider([(req, complete(req))])
    report = provider.report(req)
    for changes in [
        {'request_hash': '0' * 64},
        {'missing_required': ('hair',)},
        {'status': 'APPROVED'},
    ]:
        with pytest.raises(ValidationError):
            ExtractionReport.model_validate(report.model_copy(update=changes))
    with pytest.raises(ValueError):
        validate_extraction_report(
            report,
            expected_request=req,
            expected_provider=ProviderIdentity(
                provider_id='other', provider_version='1', is_mock=False
            ),
        )
    with pytest.raises(ValueError):
        FixtureExtractionProvider([(req, complete(req)), (req, complete(req))])
    provider.identity = ProviderIdentity(provider_id='spoof', provider_version='1', is_mock=False)
    assert provider.report(req).provider.is_mock is True


def test_canonical_whitespace_and_no_io(monkeypatch):
    import socket
    import sqlite3
    import subprocess

    def forbidden(*args, **kwargs):
        pytest.fail('Pure fixture must not perform I/O')

    for module, name in [(socket, 'socket'), (sqlite3, 'connect'), (subprocess, 'Popen')]:
        monkeypatch.setattr(module, name, forbidden)
    req = request('  black hair  ')
    assert req.description == 'black hair'
    provider = FixtureExtractionProvider(
        [(req, ExtractionCandidate(hair=evidence(req, 'black hair')))]
    )
    assert provider.report(req).candidate.hair.start == 0
    with pytest.raises(FixtureNotFound):
        FixtureExtractionProvider([]).report(req)


def test_request_maximum_and_provider_strictness():
    req = ExtractionRequest(character_id=2**63 - 1, name='n' * 120, description='d' * 4000)
    assert len(request_fingerprint(req)) == 64
    for changes in [{'is_mock': 1}, {'provider_id': ' '}, {'provider_version': 'v' * 121}]:
        with pytest.raises(ValidationError):
            ProviderIdentity.model_validate(
                {'provider_id': 'fixture', 'provider_version': '1', 'is_mock': True} | changes
            )
