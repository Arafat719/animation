"""Voice metadata baseline v1; no synthesis, audio or consent contract."""

from pydantic import BaseModel, ConfigDict, Field


class VoiceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str = Field(min_length=1, max_length=120)
    language: str | None = Field(default=None, max_length=80)
    style: str | None = Field(default=None, max_length=400)


class Voice(BaseModel):
    id: int
    name: str
    voice_type: str
    language: str | None
    style: str | None
    created_at: str


class VoiceRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)

    id: int
    name: str
    voice_type: str
    language: str | None
    style: str | None
    created_at: str
