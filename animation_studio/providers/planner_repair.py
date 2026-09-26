"""Bounded synchronous output repair; offline utility, not a live-provider adapter."""

import math
from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import ValidationError

from animation_studio.domain.v1.story_plan import StoryPlan
from animation_studio.providers.planner import PlannerRequest
from animation_studio.providers.planner_traits import TraitsAssemblyError, assemble_planner_traits


@dataclass(frozen=True)
class RepairIssue:
    code: Literal[
        'INVALID_JSON',
        'INVALID_PLAN',
        'DURATION_MISMATCH',
        'NON_FRESH_PLAN',
        'CAST_MISSING',
        'CAST_NAME_MISMATCH',
        'TRAITS_ALREADY_PRESENT',
        'TRAITS_ASSEMBLY_INVALID',
    ]
    path: tuple[str | int, ...]
    message: str


class RepairProvider(Protocol):
    def generate(self, request: PlannerRequest) -> str: ...

    def repair(
        self, request: PlannerRequest, previous_output: str, issues: tuple[RepairIssue, ...]
    ) -> str: ...


@dataclass(frozen=True)
class RepairResult:
    plan: StoryPlan
    attempts: int
    base_json: str
    status: Literal['REVIEW_REQUIRED'] = field(default='REVIEW_REQUIRED', init=False)


class RepairExhausted(ValueError):
    """All allowed outputs failed validation; no candidate is returned."""

    def __init__(self, attempts: int, issues: tuple[RepairIssue, ...]):
        self.attempts = attempts
        self.issues = issues
        super().__init__(f'Planner output invalid after {attempts} attempt(s)')


def repair_plan(
    provider: RepairProvider, request: PlannerRequest, *, max_retries: int = 0
) -> RepairResult:
    """Validate each output, allowing only explicitly budgeted repair calls.

    Provider exceptions propagate without retry. This function does not enforce
    timeouts or assess narrative quality; callers must review successful plans.
    Each provider call receives a fresh request copy, including nested profiles.
    """
    if type(max_retries) is not int or not 0 <= max_retries <= 2:
        raise ValueError('max_retries must be an integer from 0 to 2')
    snapshot = PlannerRequest.model_validate(request.model_dump())
    raw = ''
    issues: tuple[RepairIssue, ...] = ()
    for attempt in range(1, max_retries + 2):
        call_request = snapshot.model_copy(deep=True)
        # Deliberately outside the output-validation exception boundary.
        raw = (
            provider.generate(call_request)
            if attempt == 1
            else provider.repair(call_request, raw, issues)
        )
        if not isinstance(raw, str):
            raise TypeError('Planner provider must return a JSON string')
        try:
            plan = StoryPlan.model_validate_json(raw)
        except ValidationError as error:
            issues = tuple(
                RepairIssue(
                    'INVALID_JSON' if item['type'] == 'json_invalid' else 'INVALID_PLAN',
                    tuple(item['loc']),
                    item['msg'],
                )
                for item in error.errors(include_url=False, include_input=False)
            )
        else:
            if math.isclose(
                plan.estimated_total_duration_seconds,
                snapshot.duration_seconds,
                rel_tol=0,
                abs_tol=1e-6,
            ):
                expected = (
                    ('status', 'pending'),
                    ('attempts', 0),
                    ('error', None),
                    ('keyframe_path', None),
                    ('raw_clip_path', None),
                    ('lip_synced_clip_path', None),
                )
                issues = tuple(
                    RepairIssue(
                        'NON_FRESH_PLAN',
                        ('shots', index, name),
                        f'New plan requires {name}={value!r}',
                    )
                    for index, shot in enumerate(plan.shots)
                    for name, value in expected
                    if getattr(shot, name) != value
                )
                if issues:
                    continue
                cast = {
                    character.id: (index, character)
                    for index, character in enumerate(plan.characters)
                }
                cast_issues = []
                for requested in snapshot.characters:
                    if requested.id not in cast:
                        cast_issues.append(
                            RepairIssue(
                                'CAST_MISSING',
                                ('characters',),
                                f'Missing supplied character ID {requested.id!r}',
                            )
                        )
                    else:
                        index, character = cast[requested.id]
                        if character.name != requested.name:
                            cast_issues.append(
                                RepairIssue(
                                    'CAST_NAME_MISMATCH',
                                    ('characters', index, 'name'),
                                    f'Character {requested.id!r} requires name {requested.name!r}',
                                )
                            )
                issues = tuple(cast_issues)
                if not issues:
                    try:
                        assembly = assemble_planner_traits(raw, snapshot.characters)
                    except TraitsAssemblyError as error:
                        if error.code not in ('TRAITS_ALREADY_PRESENT', 'TRAITS_ASSEMBLY_INVALID'):
                            raise
                        # Raw remains the unassembled provider response for repair.
                        issues = tuple(
                            RepairIssue(
                                error.code,
                                path,
                                'Return base prompts without caller trait blocks and with room for traits',
                            )
                            for path in error.paths
                        )
                        continue
                    return RepairResult(
                        plan=StoryPlan.model_validate_json(assembly.assembled_json),
                        attempts=attempt,
                        base_json=assembly.base_json,
                    )
                continue
            issues = (
                RepairIssue(
                    'DURATION_MISMATCH',
                    ('estimated_total_duration_seconds',),
                    'Plan duration must match the requested duration',
                ),
            )
    raise RepairExhausted(attempt, issues)
