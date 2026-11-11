import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_character_profile import payload

from animation_studio.domain.v1.character_profile import CharacterProfileDraft
from animation_studio.persistence.character_profiles import CharacterProfileStore, ProfileConflict
from animation_studio.persistence.db import init_db
from apps.api.main import app


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = str(tmp_path / 'profiles.db')
    monkeypatch.setenv('ANIMATION_DB_PATH', path)
    init_db(path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(
            "INSERT INTO characters(id,name,description,reference_image_paths) VALUES(1,'Legacy',' unchanged ','not JSON [')"
        )
        db.execute("INSERT INTO characters(id,name) VALUES(2,'Other')")
    return path


def test_api_save_reopen_and_legacy_response_unchanged(database):
    with TestClient(app) as client:
        before = client.get('/characters').json()
        assert client.get('/characters/1/profile').json() is None
        response = client.post('/characters/1/profile', json=payload())
        assert response.status_code == 201
        saved = response.json()
        assert saved['profile']['name'] == 'আলো'
        assert saved['profile']['source'] == 'user_provided'
        assert saved['character_id'] == saved['schema_version'] == 1
        assert saved['created_at']
        assert client.post('/characters/1/profile', json=payload()).status_code == 409
    init_db(database)
    with TestClient(app) as client:
        assert client.get('/characters/1/profile').json() == saved
        assert client.get('/characters/2/profile').json() is None
        assert client.get('/characters').json() == before
    with closing(sqlite3.connect(database)) as db:
        assert db.execute('SELECT reference_image_paths FROM characters WHERE id=1').fetchone() == (
            'not JSON [',
        )
        assert db.execute('SELECT COUNT(*) FROM character_profiles').fetchone() == (1,)


@pytest.mark.parametrize('method', ['get', 'post'])
def test_unknown_character(database, method):
    client = TestClient(app)
    response = getattr(client, method)(
        '/characters/999/profile', **({'json': payload()} if method == 'post' else {})
    )
    assert response.status_code == 404
    assert CharacterProfileStore(database).read(1) is None


@pytest.mark.parametrize('identifier', ['0', '-1', str(2**63), 'not-an-id'])
def test_invalid_identity_before_db(tmp_path, monkeypatch, identifier):
    path = tmp_path / 'absent.db'
    monkeypatch.setenv('ANIMATION_DB_PATH', str(path))
    client = TestClient(app)
    assert client.post(f'/characters/{identifier}/profile', json=payload()).status_code == 422
    assert not path.exists()


def test_invalid_payload_before_db(tmp_path, monkeypatch):
    path = tmp_path / 'absent.db'
    monkeypatch.setenv('ANIMATION_DB_PATH', str(path))
    data = payload()
    del data['visual_traits']['hair']
    assert TestClient(app).post('/characters/1/profile', json=data).status_code == 422
    assert not path.exists()


def test_repository_revalidates_before_open(tmp_path):
    path = tmp_path / 'absent.db'
    draft = CharacterProfileDraft.model_validate(payload()).model_copy(update={'name': ''})
    with pytest.raises(ValidationError):
        CharacterProfileStore(str(path)).save(1, draft)
    assert not path.exists()


def test_concurrent_save_has_one_winner(database):
    draft = CharacterProfileDraft.model_validate(payload())

    def save(_):
        try:
            CharacterProfileStore(database).save(1, draft)
            return 'saved'
        except ProfileConflict:
            return 'conflict'

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, range(2))) == ['conflict', 'saved']
    assert CharacterProfileStore(database).read(1).profile == draft


def test_sql_update_rejected_and_snapshot_preserved(database):
    store = CharacterProfileStore(database)
    saved = store.save(1, CharacterProfileDraft.model_validate(payload()))
    with (
        closing(sqlite3.connect(database)) as db,
        db,
        pytest.raises(sqlite3.IntegrityError, match='immutable'),
    ):
        db.execute("UPDATE character_profiles SET profile_json='{}' WHERE character_id=1")
    assert store.read(1) == saved


def test_corrupt_stored_profile_not_exposed(database):
    with closing(sqlite3.connect(database)) as db, db:
        db.execute(
            'INSERT INTO character_profiles(character_id,schema_version,profile_json) VALUES(1,1,?)',
            ('private-corrupt',),
        )
    response = TestClient(app).get('/characters/1/profile')
    assert response.status_code == 500
    assert response.json() == {'detail': 'Stored character profile invalid'}
    assert 'private-corrupt' not in response.text
