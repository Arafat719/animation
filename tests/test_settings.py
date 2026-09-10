import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from animation_studio.settings import DEFAULT_DATABASE_PATH, Settings, get_settings
from animation_studio.persistence.db import init_db
from apps.api.main import app, get_db_path


def test_default_path_does_not_follow_working_directory(tmp_path, monkeypatch):
    monkeypatch.delenv('ANIMATION_DB_PATH', raising=False)
    monkeypatch.chdir(tmp_path)
    assert get_settings().database_path == DEFAULT_DATABASE_PATH
    assert DEFAULT_DATABASE_PATH.is_absolute()
    assert get_db_path() == str(DEFAULT_DATABASE_PATH)
    assert list(tmp_path.iterdir()) == []


def test_environment_path_is_shared_and_not_cached(tmp_path, monkeypatch):
    for name in ('first.db', 'second.db'):
        target = tmp_path / name
        monkeypatch.setenv('ANIMATION_DB_PATH', str(target))
        assert get_settings().database_path == target
        assert get_db_path() == str(target)
        assert init_db() == str(target)
        assert target.is_file()


def test_relative_override_keeps_existing_cwd_semantics(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('ANIMATION_DB_PATH', 'nested/relative.db')
    assert get_db_path() == 'nested/relative.db'
    assert init_db() == 'nested/relative.db'
    assert (tmp_path / 'nested/relative.db').is_file()


def test_explicit_path_takes_precedence_over_environment(tmp_path, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', '')
    target = str(tmp_path / 'explicit.db')
    assert init_db(target) == target


@pytest.mark.parametrize('value', ['', '   ', ':memory:', 'file:demo.db?mode=memory'])
def test_invalid_environment_rejected_before_creating_files(value, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('ANIMATION_DB_PATH', value)
    with pytest.raises(ValidationError):
        get_settings()
    with pytest.raises(ValidationError):
        init_db()
    assert list(tmp_path.iterdir()) == []


def test_explicit_null_byte_path_is_rejected(tmp_path, monkeypatch):
    # The OS rejects null bytes in environment values before settings can read them.
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValidationError, match='null bytes'):
        init_db('bad\x00path')
    assert list(tmp_path.iterdir()) == []


def test_existing_directory_is_not_a_database_file(tmp_path):
    with pytest.raises(ValidationError, match='existing directory'):
        Settings(database_path=tmp_path)


def test_health_startup_validates_without_creating_database(tmp_path, monkeypatch):
    target = tmp_path / 'not-created' / 'health.db'
    monkeypatch.setenv('ANIMATION_DB_PATH', str(target))
    with TestClient(app) as client:
        assert client.get('/health').json() == {'status': 'ok'}
    assert not target.parent.exists()
    monkeypatch.setenv('ANIMATION_DB_PATH', '')
    with pytest.raises(ValidationError):
        with TestClient(app):
            pytest.fail('Invalid settings must prevent startup')
