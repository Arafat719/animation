"""Voice schema publication and lossless reads across every migration entry point."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from animation_studio.domain.v1.voice import Voice, VoiceCreate, VoiceRecord
from animation_studio.persistence import db
from apps.api import main as api
from scripts import export_schemas


def test_published_voice_schemas_match_api():
    assert api.Voice is Voice
    assert api.VoiceCreate is VoiceCreate
    assert export_schemas.export(export_schemas.OUTPUT, check=True) == 0
    for suffix, model, mode in (
        ('create', VoiceCreate, 'validation'),
        ('response', Voice, 'serialization'),
        ('record', VoiceRecord, 'validation'),
    ):
        schema = json.loads((export_schemas.OUTPUT / f'voice.{suffix}.schema.json').read_text())
        assert schema.pop('$id') == f'urn:animation-studio:contracts:v1:voice.{suffix}'
        assert schema.pop('$schema') == 'https://json-schema.org/draft/2020-12/schema'
        assert schema == model.model_json_schema(mode=mode)
        if suffix != 'record':
            for field in schema['properties'].values():
                if field.get('default', 1) is None:
                    field.pop('default')
            assert schema == api.app.openapi()['components']['schemas'][model.__name__]


@pytest.mark.parametrize(
    'revision', ['legacy', '0001_initial', '0002_job_results', '0003_fixture_jobs']
)
def test_migration_and_reopened_api_preserve_voice_text(tmp_path, monkeypatch, revision):
    target = str(tmp_path / 'voices.db')
    if revision == 'legacy':
        with closing(sqlite3.connect(target)) as connection:
            connection.executescript(
                (Path(__file__).parent / 'fixtures/legacy_schema.sql').read_text()
            )
    else:
        upgrade = db.command.upgrade
        with monkeypatch.context() as patch:
            patch.setattr(db.command, 'upgrade', lambda config, _: upgrade(config, revision))
            db.init_db(target)
    rows = [
        (0, '', '', None, None, ''),
        (2, '  Saved  ', 'custom', ' বাংলা ', '  calm\nwarm  ', 'old timestamp'),
        (3, 'x' * 121, 'unknown future type', 'y' * 81, 'z' * 401, '2001-02-03'),
        (4, 'Saved', 'built_in', '', '', 'timestamp'),
        (5, 'Saved', '  custom  ', None, '', 'timestamp'),
    ]
    with closing(sqlite3.connect(target)) as connection:
        connection.executemany('INSERT INTO voices VALUES (?, ?, ?, ?, ?, ?)', rows)
        connection.commit()
    db.init_db(target)
    db.init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.row_factory = sqlite3.Row
        stored = [dict(row) for row in connection.execute('SELECT * FROM voices ORDER BY id')]
        assert [tuple(row.values()) for row in stored] == rows
        assert set(VoiceRecord.model_fields) == {
            row['name'] for row in connection.execute('PRAGMA table_info(voices)')
        }
        assert (
            connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]
            == '0003_fixture_jobs'
        )
    for row in stored:
        assert VoiceRecord.model_validate(row).model_dump() == row
    monkeypatch.setenv('ANIMATION_DB_PATH', target)
    for _ in range(2):
        with TestClient(api.app) as client:
            response = client.get('/voices')
            assert response.status_code == 200
            assert response.json() == stored
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute('SELECT * FROM voices ORDER BY id').fetchall() == rows


def test_record_defaults_required_fields_and_strict_validation(tmp_path):
    target = str(tmp_path / 'defaults.db')
    db.init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.row_factory = sqlite3.Row
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO voices (name) VALUES ('No type')")
        connection.execute("INSERT INTO voices (name, voice_type) VALUES ('Default', 'built_in')")
        connection.commit()
        row = dict(connection.execute('SELECT * FROM voices').fetchone())
    record = VoiceRecord.model_validate(row)
    assert record.model_dump() == row
    assert record.language is None and record.style is None
    assert record.created_at
    for key in row:
        with pytest.raises(ValidationError):
            VoiceRecord.model_validate({k: v for k, v in row.items() if k != key})
    for patch in (
        {'id': '1'},
        {'voice_type': None},
        {'name': None},
        {'language': b'bytes'},
        {'style': []},
        {'created_at': None},
        {'extra': True},
    ):
        with pytest.raises(ValidationError):
            VoiceRecord.model_validate({**row, **patch})
    with pytest.raises(ValidationError):
        record.name = 'Changed'


@pytest.mark.parametrize(
    'payload',
    [
        {'name': 'A', 'type': 'custom'},
        {'name': 'A', 'consent': True},
        {'name': 'A', 'provider': 'test'},
        {'name': 'A', 'id': 1},
        {'name': 'A', 'created_at': 'text'},
    ],
)
def test_future_fields_rejected_without_database_creation(tmp_path, monkeypatch, payload):
    target = tmp_path / 'invalid.db'
    monkeypatch.setenv('ANIMATION_DB_PATH', str(target))
    with TestClient(api.app) as client:
        assert client.post('/voices', json=payload).status_code == 422
    assert not target.exists()
