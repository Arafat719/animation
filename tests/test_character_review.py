import hashlib
import json

import pytest
from pydantic import ValidationError

from animation_studio.domain.v1.character_extraction import (
    FIELDS,
    ExtractionCandidate,
    build_extraction_report,
)
from animation_studio.domain.v1.character_review import (
    ExtractionReviewDecision,
    ReviewedExtractionProfile,
    TraitDecisions,
    build_reviewed_profile,
    report_fingerprint,
)
from animation_studio.providers.character_extraction import FixtureExtractionProvider
from tests.test_character_extraction import complete, request


def setup(candidate=None):
    req = request()
    report = FixtureExtractionProvider([(req, candidate or complete(req))]).report(req)
    return report


def review(report, **decisions):
    return ExtractionReviewDecision(
        character_id=report.request.character_id,
        report_hash=report_fingerprint(report),
        confirmed=True,
        decisions=TraitDecisions.model_validate(
            {field: {'action': 'accept'} for field in FIELDS} | decisions
        ),
    )


def build(report, decision=None, **context):
    return build_reviewed_profile(
        report,
        decision or review(report),
        **({'expected_request': report.request, 'expected_provider': report.provider} | context),
    )


def test_complete_unicode_immutable_roundtrip_and_canonical_hash():
    report = setup()
    profile = build(report)
    assert profile.schema_version == 2 and profile.source == 'reviewed_extraction'
    assert profile.values.name == 'আলো'
    assert profile.values.visual_traits.hair == report.candidate.hair.value
    assert profile.values.visual_traits.colors == ('নীল',)
    assert profile.provenance.report == report
    assert profile.provenance.report.status == 'REVIEW_REQUIRED'
    assert profile.provenance.report.provider.is_mock is True
    assert set(profile.origins.model_dump().values()) == {'extraction_accepted'}
    assert (
        report_fingerprint(report)
        == hashlib.sha256(
            json.dumps(
                report.model_dump(), ensure_ascii=False, sort_keys=True, separators=(',', ':')
            ).encode()
        ).hexdigest()
    )
    assert ReviewedExtractionProfile.model_validate_json(profile.model_dump_json()) == profile
    with pytest.raises(ValidationError):
        profile.values.visual_traits.hair = 'changed'


def test_partial_ambiguous_replace_omit_and_normalization():
    report = setup(ExtractionCandidate(ambiguous_fields=('hair', 'accessories')))
    decisions = {field: {'action': 'replace', 'value': ' গোল '} for field in FIELDS[:4]}
    decisions |= {
        'colors': {'action': 'replace', 'value': (' নীল ', 'লাল')},
        'accessories': {'action': 'omit'},
        'negative_traits': {'action': 'omit'},
    }
    profile = build(report, review(report, **decisions))
    assert profile.values.visual_traits.hair == 'গোল'
    assert profile.values.visual_traits.colors == ('নীল', 'লাল')
    assert profile.values.negative_traits == ()
    assert profile.origins.accessories == 'user_omitted'
    assert profile.origins.hair == 'user_replacement'
    assert profile.provenance.report.provider.is_mock is True
    with pytest.raises(ValueError):
        build(report)


def test_same_replacement_keeps_origin_and_list_order():
    report = setup()
    result = build(
        report,
        review(
            report,
            hair={'action': 'replace', 'value': ' কালো চুল '},
            colors={'action': 'replace', 'value': ('লাল', 'নীল')},
        ),
    )
    assert result.values.visual_traits.hair == 'কালো চুল'
    assert result.origins.hair == 'user_replacement'
    assert result.values.visual_traits.colors == ('লাল', 'নীল')


@pytest.mark.parametrize('field', FIELDS)
def test_missing_decisions_and_unknown_accept_rejected(field):
    report = setup()
    payload = review(report).model_dump()
    del payload['decisions'][field]
    with pytest.raises(ValidationError):
        ExtractionReviewDecision.model_validate(payload)
    candidate = report.candidate.model_copy(update={field: None if field in FIELDS[:4] else ()})
    partial = build_extraction_report(report.request, candidate, provider=report.provider)
    with pytest.raises(ValueError):
        build(partial)


@pytest.mark.parametrize(
    'field,decision',
    [
        ('face', {'action': 'omit'}),
        ('colors', {'action': 'omit'}),
        ('hair', {'action': 'accept', 'value': 'x'}),
        ('accessories', {'action': 'omit', 'value': ()}),
        ('hair', {'action': 'replace', 'value': 1}),
        ('hair', {'action': 'replace', 'value': ' '}),
        ('hair', {'action': 'replace', 'value': 'x' * 501}),
        ('hair', {'action': 'replace', 'value': ('x',)}),
        ('colors', {'action': 'replace', 'value': 'x'}),
        ('colors', {'action': 'replace', 'value': ['x']}),
        ('colors', {'action': 'replace', 'value': ()}),
        ('colors', {'action': 'replace', 'value': ('x',) * 21}),
        ('accessories', {'action': 'replace', 'value': ('x',) * 21}),
        ('negative_traits', {'action': 'replace', 'value': ('x',) * 101}),
    ],
)
def test_bad_decision_shapes_and_bounds(field, decision):
    with pytest.raises(ValidationError):
        review(setup(), **{field: decision})


@pytest.mark.parametrize(
    'change',
    [
        {'confirmed': False},
        {'confirmed': 1},
        {'confirmed': 'true'},
        {'character_id': True},
        {'character_id': 2},
        {'report_hash': '0' * 64},
        {'extra': 1},
    ],
)
def test_review_unchecked_copy_rejected(change):
    report = setup()
    with pytest.raises(ValueError):
        build(report, review(report).model_copy(update=change))


@pytest.mark.parametrize(
    'change',
    [
        {'schema_version': True},
        {'schema_version': 2.0},
        {'schema_version': 1},
        {'character_id': 2},
        {'source': 'user_provided'},
    ],
)
def test_envelope_tampering(change):
    with pytest.raises(ValidationError):
        ReviewedExtractionProfile.model_validate(build(setup()).model_copy(update=change))


def test_derived_nested_copy_tampering():
    profile = build(setup())
    corruptions = [
        {'origins': profile.origins.model_copy(update={'hair': 'user_replacement'})},
        {'values': profile.values.model_copy(update={'name': 'Changed'})},
        {
            'values': profile.values.model_copy(
                update={
                    'visual_traits': profile.values.visual_traits.model_copy(
                        update={'colors': ['blue']}
                    )
                }
            )
        },
        {'provenance': profile.provenance.model_copy(update={'report_hash': '0' * 64})},
    ]
    for change in corruptions:
        with pytest.raises(ValidationError):
            ReviewedExtractionProfile.model_validate(profile.model_copy(update=change))
    report = setup()
    decision = review(report)
    broken = decision.decisions.hair.model_copy(update={'value': 'extra'})
    with pytest.raises(ValidationError):
        build(
            report,
            decision.model_copy(
                update={'decisions': decision.decisions.model_copy(update={'hair': broken})}
            ),
        )


def test_changed_report_stale_decision_and_context():
    report = setup()
    changed_candidate = report.candidate.model_copy(update={'accessories': ()})
    other = build_extraction_report(report.request, changed_candidate, provider=report.provider)
    provider = report.provider.model_copy(update={'provider_version': '2'})
    other_provider = build_extraction_report(report.request, report.candidate, provider=provider)
    for changed in (other, other_provider):
        assert changed.request_hash == report.request_hash
        assert report_fingerprint(changed) != report_fingerprint(report)
        with pytest.raises(ValueError):
            build(changed, review(report))
    with pytest.raises(ValueError):
        build(report, expected_provider=provider)
    with pytest.raises(ValueError):
        build(report, expected_request=report.request.model_copy(update={'character_id': 2}))


def test_pure_builder_no_io_or_clock(monkeypatch):
    import socket
    import sqlite3
    import subprocess
    import time

    report = setup()

    def forbidden(*args, **kwargs):
        pytest.fail('Pure builder attempted I/O or clock access')

    for module, name in (
        (socket, 'socket'),
        (sqlite3, 'connect'),
        (subprocess, 'Popen'),
        (time, 'time'),
        (time, 'monotonic'),
    ):
        monkeypatch.setattr(module, name, forbidden)
    assert build(report) == build(report)


def test_accepted_list_order_and_replacement_boundaries():
    from tests.test_character_extraction import evidence

    report = setup()
    candidate = report.candidate.model_copy(
        update={
            'colors': (evidence(report.request, 'নীল'), evidence(report.request, 'লাল')),
        }
    )
    report = build_extraction_report(report.request, candidate, provider=report.provider)
    assert build(report).values.visual_traits.colors == ('নীল', 'লাল')
    profile = build(
        report,
        review(
            report,
            hair={'action': 'replace', 'value': 'x' * 500},
            colors={'action': 'replace', 'value': ('x',) * 20},
            accessories={'action': 'replace', 'value': ('x',) * 20},
            negative_traits={'action': 'replace', 'value': ('x',) * 100},
        ),
    )
    assert len(profile.values.negative_traits) == 100
    broken = report.candidate.hair.model_copy(update={'start': True})
    report = report.model_copy(
        update={'candidate': report.candidate.model_copy(update={'hair': broken})}
    )
    with pytest.raises(ValidationError):
        report_fingerprint(report)
