"""Character v1 publication and lossless legacy metadata compatibility."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from animation_studio.domain.v1.character import Character, CharacterCreate, CharacterRecord
from animation_studio.persistence import db
from apps.api import main as api
from scripts import export_schemas

LEGACY_SCHEMA = Path(__file__).parent / 'fixtures/legacy_schema.sql'


def test_character_api_uses_versioned_models_and_matching_published_schemas():
    assert api.CharacterCreate is CharacterCreate
    assert api.Character is Character
    assert export_schemas.export(export_schemas.OUTPUT, check=True) == 0
    components = api.app.openapi()['components']['schemas']
    for suffix, model, mode in (
        ('create', CharacterCreate, 'validation'),
        ('response', Character, 'serialization'),
        ('record', CharacterRecord, 'validation'),
    ):
        schema = json.loads((export_schemas.OUTPUT / f'character.{suffix}.schema.json').read_text())
        assert schema.pop('$id') == f'urn:animation-studio:contracts:v1:character.{suffix}'
        assert schema.pop('$schema') == 'https://json-schema.org/draft/2020-12/schema'
        assert schema == model.model_json_schema(mode=mode)
        if suffix != 'record':
            for field in schema['properties'].values():
                if 'default' in field and field['default'] is None:
                    field.pop('default')
            assert schema == components[schema['title']]


def test_character_schema_drift_is_detected_without_overwriting(tmp_path):
    export_schemas.export(tmp_path, check=False)
    target = tmp_path / 'character.response.schema.json'
    target.unlink()
    assert export_schemas.export(tmp_path, check=True) == 1
    assert not target.exists()
    target.write_text('{}\n')
    assert export_schemas.export(tmp_path, check=True) == 1
    assert target.read_text() == '{}\n'


@pytest.mark.parametrize(
    'revision', ['legacy', '0001_initial', '0002_job_results', '0003_fixture_jobs']
)
def test_character_migrations_preserve_all_fields_and_list_reads(tmp_path, monkeypatch, revision):
    target = str(tmp_path / 'characters.db')
    if revision == 'legacy':
        with closing(sqlite3.connect(target)) as connection:
            connection.executescript(LEGACY_SCHEMA.read_text())
    else:
        upgrade = db.command.upgrade
        with monkeypatch.context() as patch:
            patch.setattr(db.command, 'upgrade', lambda config, _: upgrade(config, revision))
            db.init_db(target)
    rows = [
        (0, '', None, None, 'old timestamp'),
        (
            3,
            '  Saved  ',
            '  keep spaces\nand newline  ',
            '/missing/private/image.png',
            '2001-02-03',
        ),
        (4, 'x' * 121, 'y' * 4001, '["/reference/a.png"]', 'another timestamp'),
        (5, 'Saved', '', 'not JSON [', ''),
        (6, 'Saved', 'same name allowed', '', '2000-01-01 01:02:03'),
    ]
    with closing(sqlite3.connect(target)) as connection:
        connection.executemany('INSERT INTO characters VALUES (?, ?, ?, ?, ?)', rows)
        connection.commit()
    db.init_db(target)
    db.init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.row_factory = sqlite3.Row
        stored = [dict(row) for row in connection.execute('SELECT * FROM characters ORDER BY id')]
        assert [tuple(row.values()) for row in stored] == rows
        assert set(CharacterRecord.model_fields) == {
            row['name'] for row in connection.execute('PRAGMA table_info(characters)')
        }
        assert (
            connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]
            == '0003_fixture_jobs'
        )
    for row in stored:
        assert CharacterRecord.model_validate(row).model_dump() == row
    monkeypatch.setenv('ANIMATION_DB_PATH', target)
    expected = [{key: row[key] for key in Character.model_fields} for row in stored]
    for _ in range(2):
        with TestClient(api.app) as client:
            response = client.get('/characters')
            assert response.status_code == 200
            assert response.json() == expected
            assert all('reference_image_paths' not in row for row in response.json())
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute('SELECT * FROM characters ORDER BY id').fetchall() == rows


def test_character_record_requires_all_columns_preserves_defaults_and_rejects_coercion(tmp_path):
    target = str(tmp_path / 'defaults.db')
    db.init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("INSERT INTO characters (name) VALUES ('Defaults')")
        connection.commit()
        row = dict(connection.execute('SELECT * FROM characters').fetchone())
    record = CharacterRecord.model_validate(row)
    assert record.model_dump() == row
    assert record.description is None
    assert record.reference_image_paths is None
    assert isinstance(record.created_at, str) and record.created_at
    for key in row:
        with pytest.raises(ValidationError):
            CharacterRecord.model_validate(
                {name: value for name, value in row.items() if name != key}
            )
    for patch in (
        {'id': '1'},
        {'name': None},
        {'description': b'bytes'},
        {'reference_image_paths': []},
        {'reference_image_paths': b'bytes'},
        {'created_at': None},
        {'extra': True},
    ):
        with pytest.raises(ValidationError):
            CharacterRecord.model_validate({**row, **patch})
    with pytest.raises(ValidationError):
        record.name = 'Changed'


@pytest.mark.parametrize('description', [None, '', '   ', '  Blue hair\nRed jacket  '])
def test_create_normalizes_strings_and_preserves_exact_response_shape(
    tmp_path, monkeypatch, description
):
    target = str(tmp_path / 'api.db')
    monkeypatch.setenv('ANIMATION_DB_PATH', target)
    with TestClient(api.app) as client:
        response = client.post('/characters', json={'name': '  Airi  ', 'description': description})
        assert response.status_code == 201
        saved = response.json()
        assert set(saved) == {'id', 'name', 'description', 'created_at'}
        assert saved['name'] == 'Airi'
        assert saved['description'] == (
            (description.strip() or None) if description is not None else None
        )
        assert saved['created_at']
        second = client.post('/characters', json={'name': 'Airi'})
        assert second.status_code == 201
        assert second.json()['id'] != saved['id']
        assert second.json()['description'] is None
        assert client.get('/characters').json() == [saved, second.json()]
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute('SELECT reference_image_paths FROM characters').fetchall() == [
            (None,),
            (None,),
        ]


def test_create_limits_apply_after_trimming(tmp_path, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', str(tmp_path / 'limits.db'))
    with TestClient(api.app) as client:
        response = client.post(
            '/characters',
            json={'name': '  ' + 'a' * 120 + '  ', 'description': '\n' + 'b' * 4000 + '\n'},
        )
        assert response.status_code == 201
        assert response.json()['name'] == 'a' * 120
        assert response.json()['description'] == 'b' * 4000


@pytest.mark.parametrize(
    'payload',
    [
        {},
        {'name': None},
        {'name': ' \n\t '},
        {'name': 'a' * 121},
        {'name': 123},
        {'name': 'A', 'description': 'a' * 4001},
        {'name': 'A', 'description': 123},
        {'name': 'A', 'reference_image_paths': '[]'},
        {'name': 'A', 'id': 1},
        {'name': 'A', 'created_at': 'timestamp'},
    ],
)
def test_create_rejects_invalid_or_extra_fields_before_opening_database(
    tmp_path, monkeypatch, payload
):
    target = tmp_path / 'invalid.db'
    monkeypatch.setenv('ANIMATION_DB_PATH', str(target))
    with TestClient(api.app) as client:
        assert client.post('/characters', json=payload).status_code == 422
    assert not target.exists()
