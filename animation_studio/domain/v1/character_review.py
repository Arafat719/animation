"""Pure reviewed-extraction v2 values; no persistence or approval of media."""

import hashlib
import json
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from animation_studio.domain.v1.character_extraction import (
    FIELDS,
    REQUIRED,
    ExtractionModel,
    ExtractionReport,
    ExtractionRequest,
    ProviderIdentity,
    validate_extraction_report,
)
from animation_studio.domain.v1.character_profile import (
    CharacterProfileDraft,
    TraitText,
    VisualTraits,
)


class Accept(ExtractionModel):
    action: Literal['accept']


class ReplaceScalar(ExtractionModel):
    action: Literal['replace']
    value: TraitText


class ReplaceList(ExtractionModel):
    action: Literal['replace']
    value: tuple[TraitText, ...] = Field(max_length=100)


class Omit(ExtractionModel):
    action: Literal['omit']


ScalarDecision = Annotated[Accept | ReplaceScalar, Field(discriminator='action')]
ListDecision = Annotated[Accept | ReplaceList, Field(discriminator='action')]
OptionalDecision = Annotated[Accept | ReplaceList | Omit, Field(discriminator='action')]


class TraitDecisions(ExtractionModel):
    face: ScalarDecision
    hair: ScalarDecision
    eyes: ScalarDecision
    outfit: ScalarDecision
    colors: ListDecision
    accessories: OptionalDecision
    negative_traits: OptionalDecision

    @model_validator(mode='after')
    def bounds(self):
        for field in ('colors', 'accessories'):
            decision = getattr(self, field)
            if isinstance(decision, ReplaceList) and (
                len(decision.value) > 20 or (field == 'colors' and not decision.value)
            ):
                raise ValueError('Invalid replacement list size')
        return self


class ExtractionReviewDecision(ExtractionModel):
    report_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    character_id: int = Field(gt=0, le=2**63 - 1)
    confirmed: Literal[True]
    decisions: TraitDecisions

    @field_validator('confirmed', mode='before')
    @classmethod
    def confirmation(cls, value):
        if type(value) is not bool or value is not True:
            raise ValueError('Explicit confirmation required')
        return value


class ReviewedVisualTraits(VisualTraits):
    model_config = ConfigDict(strict=True)


ProfileName = CharacterProfileDraft.model_fields['name'].rebuild_annotation()
ProfileDescription = CharacterProfileDraft.model_fields['description'].rebuild_annotation()


class ReviewedProfileValues(ExtractionModel):
    name: ProfileName
    description: ProfileDescription
    visual_traits: ReviewedVisualTraits
    negative_traits: tuple[TraitText, ...] = Field(max_length=100)


Origin = Literal['extraction_accepted', 'user_replacement', 'user_omitted']


class TraitOrigins(ExtractionModel):
    face: Origin
    hair: Origin
    eyes: Origin
    outfit: Origin
    colors: Origin
    accessories: Origin
    negative_traits: Origin


def report_fingerprint(report: ExtractionReport) -> str:
    report = ExtractionReport.model_validate(report)
    payload = json.dumps(
        report.model_dump(), ensure_ascii=False, sort_keys=True, separators=(',', ':')
    ).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


class ReviewProvenance(ExtractionModel):
    report: ExtractionReport
    report_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    review: ExtractionReviewDecision

    @model_validator(mode='after')
    def binding(self):
        if self.report_hash != report_fingerprint(self.report):
            raise ValueError('Report fingerprint mismatch')
        if self.review.report_hash != self.report_hash:
            raise ValueError('Stale review decision')
        if self.review.character_id != self.report.request.character_id:
            raise ValueError('Review character mismatch')
        return self


def _derive(provenance: ReviewProvenance) -> tuple[ReviewedProfileValues, TraitOrigins]:
    traits = {}
    origins = {}
    candidate = provenance.report.candidate
    for field in FIELDS:
        decision = getattr(provenance.review.decisions, field)
        if isinstance(decision, Accept):
            suggestion = getattr(candidate, field)
            if field in candidate.ambiguous_fields or not suggestion:
                raise ValueError('Accept requires a nonempty unambiguous candidate')
            traits[field] = (
                tuple(item.value for item in suggestion)
                if isinstance(suggestion, tuple)
                else suggestion.value
            )
            origins[field] = 'extraction_accepted'
        elif isinstance(decision, Omit):
            if field in REQUIRED:
                raise ValueError('Required trait cannot be omitted')
            traits[field] = ()
            origins[field] = 'user_omitted'
        else:
            traits[field] = decision.value
            origins[field] = 'user_replacement'
    negatives = traits.pop('negative_traits')
    values = ReviewedProfileValues(
        name=provenance.report.request.name,
        description=provenance.report.request.description,
        visual_traits=ReviewedVisualTraits(**traits),
        negative_traits=negatives,
    )
    return values, TraitOrigins(**origins)


class ReviewedExtractionProfile(ExtractionModel):
    schema_version: Literal[2] = 2
    character_id: int = Field(gt=0, le=2**63 - 1)
    source: Literal['reviewed_extraction'] = 'reviewed_extraction'
    values: ReviewedProfileValues
    provenance: ReviewProvenance
    origins: TraitOrigins

    @field_validator('schema_version', mode='before')
    @classmethod
    def version(cls, value):
        if type(value) is not int or value != 2:
            raise ValueError('Unsupported reviewed profile version')
        return value

    @model_validator(mode='after')
    def derived_values(self):
        if self.character_id != self.provenance.review.character_id:
            raise ValueError('Profile character mismatch')
        values, origins = _derive(self.provenance)
        if self.values != values or self.origins != origins:
            raise ValueError('Inconsistent derived profile values or origins')
        return self


def build_reviewed_profile(
    report: ExtractionReport,
    review: ExtractionReviewDecision,
    *,
    expected_request: ExtractionRequest,
    expected_provider: ProviderIdentity,
) -> ReviewedExtractionProfile:
    report = validate_extraction_report(
        report, expected_request=expected_request, expected_provider=expected_provider
    )
    provenance = ReviewProvenance(
        report=report, report_hash=report_fingerprint(report), review=review
    )
    values, origins = _derive(provenance)
    return ReviewedExtractionProfile(
        character_id=report.request.character_id,
        values=values,
        origins=origins,
        provenance=provenance,
    )
