"""Immutable, user-authored profile draft; no extraction, storage or inference."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

TraitText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=500)
]


class VisualTraits(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', revalidate_instances='always')

    face: TraitText
    hair: TraitText
    eyes: TraitText
    outfit: TraitText
    colors: tuple[TraitText, ...] = Field(min_length=1, max_length=20)
    accessories: tuple[TraitText, ...] = Field(default=(), max_length=20)


class CharacterProfileDraft(BaseModel):
    """Explicit traits accompany the description; missing traits are never guessed.

    Nested models and sequences are immutable. This is not a saved CharacterRecord,
    nor a generated/approved keyframe or a model-derived semantic profile.
    """

    model_config = ConfigDict(frozen=True, extra='forbid', revalidate_instances='always')

    name: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=120)
    ]
    description: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000)
    ]
    visual_traits: VisualTraits
    negative_traits: tuple[TraitText, ...] = Field(default=(), max_length=100)
    source: Literal['user_provided'] = 'user_provided'
