import pytest
from fastapi.testclient import TestClient

from animation_studio.persistence.db import init_db
from animation_studio.settings import DEFAULT_DATABASE_PATH
from apps.api import main


@pytest.fixture
def client(monkeypatch):
    def unexpected_database_access(*args, **kwargs):
        pytest.fail('Reading settings must not connect to or initialize the database')

    monkeypatch.setattr(main, 'get_connection', unexpected_database_access)
    monkeypatch.setattr(main, 'init_db', unexpected_database_access)
    with TestClient(main.app) as session:
        yield session


def test_settings_default_path_independent_of_cwd(client, tmp_path, monkeypatch):
    monkeypatch.delenv('ANIMATION_DB_PATH', raising=False)
    monkeypatch.chdir(tmp_path)
    response = client.get('/settings')
    assert response.status_code == 200
    assert response.json() == {'database_path': str(DEFAULT_DATABASE_PATH)}
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('relative', [False, True])
def test_settings_override_is_absolute_and_creates_nothing(client, tmp_path, monkeypatch, relative):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / 'folder বাংলা #%?' / 'scene.db'
    configured = target.relative_to(tmp_path) if relative else target
    monkeypatch.setenv('ANIMATION_DB_PATH', str(configured))
    response = client.get('/settings')
    assert response.status_code == 200
    assert response.json() == {'database_path': str(target)}
    assert list(tmp_path.iterdir()) == []


def test_settings_reads_current_environment(client, tmp_path, monkeypatch):
    for name in ('first.db', 'second.db'):
        target = tmp_path / name
        monkeypatch.setenv('ANIMATION_DB_PATH', str(target))
        assert client.get('/settings').json() == {'database_path': str(target)}
    assert list(tmp_path.iterdir()) == []


def test_settings_preserves_existing_database_and_rejects_writes(client, tmp_path, monkeypatch):
    target = tmp_path / 'existing.db'
    init_db(str(target))
    monkeypatch.setenv('ANIMATION_DB_PATH', str(target))
    before = target.read_bytes(), target.stat().st_mtime_ns
    for _ in range(2):
        assert client.get('/settings').json() == {'database_path': str(target)}
    for method in ('post', 'put', 'patch', 'delete'):
        response = client.request(method, '/settings', json={'database_path': str(tmp_path / 'other.db')})
        assert response.status_code == 405
    assert (target.read_bytes(), target.stat().st_mtime_ns) == before
    assert list(tmp_path.iterdir()) == [target]
