"""Validated local application settings; loading does not create files."""

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / 'data' / 'animation.db'


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True, validate_default=True)

    database_path: Path = DEFAULT_DATABASE_PATH

    @field_validator('database_path', mode='before')
    @classmethod
    def validate_database_path(cls, value: object) -> object:
        if isinstance(value, (str, Path)):
            text = str(value)
            if not text.strip() or '\x00' in text:
                raise ValueError('Database path must be a non-empty filesystem path without null bytes')
            if text == ':memory:' or text.startswith('file:'):
                raise ValueError('Database path must be a persistent filesystem path, not a SQLite URI')
            if Path(text).is_dir():
                raise ValueError('Database path must name a file, not an existing directory')
        return value


def get_settings() -> Settings:
    # Read on demand: tests and embedded callers may change environment settings.
    # Do not load unrelated environment variables or implicitly read .env files.
    value = os.environ.get('ANIMATION_DB_PATH')
    return Settings() if value is None else Settings(database_path=value)


def get_database_path(override: str | None = None) -> str:
    settings = get_settings() if override is None else Settings(database_path=override)
    return str(settings.database_path)
