"""Pure traits assembly from explicit base prompts; no provider calls."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import ValidationError

from animation_studio.domain.v1.story_plan import StoryPlan
from animation_studio.providers.planner import PlannerCharacter, inject_character_traits


class TraitsAssemblyError(ValueError):
    def __init__(self, code: str, paths: tuple[tuple[str | int, ...], ...]):
        self.code = code
        self.paths = paths
        super().__init__(f'{code}: {paths}')


@dataclass(frozen=True)
class TraitsAssemblyResult:
    base_json: str
    assembled_json: str
    status: Literal['REVIEW_REQUIRED'] = field(default='REVIEW_REQUIRED', init=False)


def assemble_planner_traits(
    base_json: str, profiles: list[PlannerCharacter]
) -> TraitsAssemblyResult:
    """Assemble once, rejecting exact reserved blocks and prompt overflow.

    Returned JSON is normalized, not the original provider byte stream. Exact
    block detection is conservative; it does not detect semantic repetition.
    Duration/freshness and narrative acceptance belong to other boundaries.
    """
    if not isinstance(base_json, str):
        raise TypeError('Base plan must be a JSON string')
    snapshots = [PlannerCharacter.model_validate(p.model_dump()) for p in profiles]
    base = StoryPlan.model_validate_json(base_json)
    cast = {c.id: (index, c) for index, c in enumerate(base.characters)}
    seen = set()
    blocks = []
    for index, profile in enumerate(snapshots):
        if profile.id in seen or profile.id not in cast:
            raise TraitsAssemblyError('TRAITS_PROFILE_MISMATCH', (('profiles', index, 'id'),))
        seen.add(profile.id)
        cast_index, character = cast[profile.id]
        if character.name != profile.name:
            raise TraitsAssemblyError(
                'TRAITS_PROFILE_MISMATCH', (('characters', cast_index, 'name'),)
            )
        for traits in (profile.visual_traits, profile.negative_traits):
            if traits:
                blocks.append(f'{profile.name} [{profile.id}]: ' + '; '.join(traits))
    for index, shot in enumerate(base.shots):
        for name in ('image_prompt', 'motion_prompt', 'negative_prompt'):
            if any(block in getattr(shot, name) for block in blocks):
                raise TraitsAssemblyError('TRAITS_ALREADY_PRESENT', (('shots', index, name),))
    try:
        assembled = inject_character_traits(base, snapshots)
    except ValidationError as error:
        raise TraitsAssemblyError(
            'TRAITS_ASSEMBLY_INVALID',
            tuple(tuple(item['loc']) for item in error.errors(include_url=False, include_input=False)),
        ) from error
    return TraitsAssemblyResult(base.model_dump_json(), assembled.model_dump_json())
