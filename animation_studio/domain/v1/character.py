"""Character metadata baseline v1, preserving the existing API and stored text.

reference_image_paths is opaque SQLite TEXT, not a validated list or upload
contract. See docs/contracts/character-v1.md for record/API differences.
"""

from pydantic import BaseModel, ConfigDict, Field


class CharacterCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)


class Character(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: str


class CharacterRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)

    id: int
    name: str
    description: str | None
    reference_image_paths: str | None
    created_at: str
