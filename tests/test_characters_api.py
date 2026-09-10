import sqlite3

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', str(tmp_path / 'characters.db'))
    with TestClient(app) as session:
        yield session


def test_character_save_list_and_reload(client):
    assert client.get('/characters').json() == []
    response = client.post('/characters', json={'name': '  Airi  ', 'description': 'Blue hair\nRed jacket'})
    assert response.status_code == 201
    saved = response.json()
    assert saved['name'] == 'Airi'
    assert saved['description'] == 'Blue hair\nRed jacket'
    assert saved['created_at']
    assert client.get('/characters').json() == [saved]
    with TestClient(app) as reopened:
        assert reopened.get('/characters').json() == [saved]


@pytest.mark.parametrize('payload', [
    {}, {'name': ''}, {'name': '   '}, {'name': 'a' * 121},
    {'name': 'Airi', 'description': 'a' * 4001},
    {'name': 'Airi', 'reference_image_paths': ['/private/reference.png']},
])
def test_invalid_character_rejected_without_saving(client, payload):
    assert client.post('/characters', json=payload).status_code == 422
    assert client.get('/characters').json() == []


def test_optional_description_and_sql_text_are_preserved_safely(client):
    name = "Airi'); DROP TABLE characters; --"
    first = client.post('/characters', json={'name': name, 'description': '  '})
    assert first.status_code == 201
    assert first.json()['description'] is None
    assert client.post('/characters', json={'name': 'Second'}).status_code == 201
    assert [item['name'] for item in client.get('/characters').json()] == [name, 'Second']


def test_existing_character_row_remains_readable(client, tmp_path):
    client.get('/characters')
    connection = sqlite3.connect(tmp_path / 'characters.db')
    try:
        connection.execute("INSERT INTO characters (name, reference_image_paths) VALUES ('Existing', '/private/image.png')")
        connection.commit()
    finally:
        connection.close()
    saved = client.get('/characters').json()[0]
    assert saved['name'] == 'Existing'
    assert saved['description'] is None
    assert 'reference_image_paths' not in saved
