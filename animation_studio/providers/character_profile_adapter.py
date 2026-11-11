"""Pure saved-profile mapping to planner traits; no database or provider calls."""

from animation_studio.persistence.character_profiles import SavedCharacterProfile
from animation_studio.persistence.reviewed_character_profiles import SavedReviewedCharacterProfile
from animation_studio.providers.planner import PlannerCharacter


def to_planner_character(
    saved: SavedCharacterProfile | SavedReviewedCharacterProfile, *, expected_character_id: int
) -> PlannerCharacter:
    """Bind an explicitly selected database identity to a canonical planner ID.

    Only structured visual/negative traits enter prompts. Description and storage
    metadata stay out. Final assembled prompt limits remain the assembler's job.
    The caller retains the saved snapshot for provenance/mock-origin display;
    PlannerCharacter is only prompt input, not an extraction authenticity claim.
    """
    if type(expected_character_id) is not int or not 1 <= expected_character_id <= 2**63 - 1:
        raise ValueError('Invalid selected character identity')
    if type(saved) is SavedCharacterProfile:
        if type(saved.schema_version) is not int or saved.schema_version != 1:
            raise ValueError('Unsupported character profile version')
        # V1 does not revalidate instances; rebuild its Python payload.
        snapshot = SavedCharacterProfile.model_validate(saved.model_dump())
        profile = snapshot.profile
    elif type(saved) is SavedReviewedCharacterProfile:
        # V2 recursively revalidates values, decisions, provenance and identity.
        snapshot = SavedReviewedCharacterProfile.model_validate(saved)
        profile = snapshot.profile.values
    else:
        raise TypeError('Expected saved character profile')
    if snapshot.character_id != expected_character_id:
        raise ValueError('Selected character profile mismatch')
    traits = profile.visual_traits
    visual = [
        f'face: {traits.face}',
        f'hair: {traits.hair}',
        f'eyes: {traits.eyes}',
        f'outfit: {traits.outfit}',
        *(f'color: {value}' for value in traits.colors),
        *(f'accessory: {value}' for value in traits.accessories),
    ]
    return PlannerCharacter(
        id=f'character-{expected_character_id}',
        name=profile.name,
        visual_traits=visual,
        negative_traits=list(profile.negative_traits),
    )
