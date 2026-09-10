import sqlite3

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', str(tmp_path / 'voices.db'))
    with TestClient(app) as session:
        yield session


def test_voice_save_list_and_reopen(client):
    assert client.get('/voices').json() == []
    response = client.post('/voices', json={
        'name': '  Narrator  ', 'language': '  বাংলা  ', 'style': '  Calm\nWarm  ',
    })
    assert response.status_code == 201
    saved = response.json()
    assert saved == {
        'id': saved['id'], 'name': 'Narrator', 'voice_type': 'built_in',
        'language': 'বাংলা', 'style': 'Calm\nWarm', 'created_at': saved['created_at'],
    }
    assert saved['created_at']
    with TestClient(app) as reopened:
        assert reopened.get('/voices').json() == [saved]


@pytest.mark.parametrize('payload', [
    {}, {'name': ''}, {'name': '   '}, {'name': None}, {'name': 'a' * 121},
    {'name': 'Narrator', 'language': 'a' * 81},
    {'name': 'Narrator', 'style': 'a' * 401},
    {'name': 'Narrator', 'language': 123},
    {'name': 'Narrator', 'voice_type': 'custom'},
    {'name': 'Narrator', 'reference_audio_path': '/private/sample.wav'},
])
def test_invalid_voice_rejected_without_saving(client, payload):
    assert client.post('/voices', json=payload).status_code == 422
    assert client.get('/voices').json() == []


def test_optional_fields_duplicate_names_and_sql_text(client):
    name = "Narrator'); DROP TABLE voices; --"
    for fields in ({}, {'language': None, 'style': None}, {'language': '  ', 'style': '  '}):
        response = client.post('/voices', json={'name': name, **fields})
        assert response.status_code == 201
        assert response.json()['language'] is None
        assert response.json()['style'] is None
    saved = client.get('/voices').json()
    assert [voice['name'] for voice in saved] == [name] * 3
    assert len({voice['id'] for voice in saved}) == 3


def test_maximum_lengths_are_accepted(client):
    response = client.post('/voices', json={
        'name': 'a' * 120, 'language': 'b' * 80, 'style': 'c' * 400,
    })
    assert response.status_code == 201


def test_existing_voice_rows_remain_readable_and_unchanged(client, tmp_path):
    client.get('/voices')
    connection = sqlite3.connect(tmp_path / 'voices.db')
    try:
        connection.execute("INSERT INTO voices (name, voice_type) VALUES ('Existing', 'custom')")
        connection.commit()
        before = connection.execute('SELECT * FROM voices').fetchall()
        saved = client.get('/voices').json()
        assert len(saved) == 1
        assert saved[0]['name'] == 'Existing'
        assert saved[0]['voice_type'] == 'custom'
        assert saved[0]['language'] is None
        assert saved[0]['style'] is None
        assert connection.execute('SELECT * FROM voices').fetchall() == before
    finally:
        connection.close()
