"""Project baseline compatibility, migration reads and published schema drift."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from animation_studio.domain.v1.project import Project, ProjectCreate, ProjectRecord
from animation_studio.persistence import db
from apps.api import main as api
from scripts import export_schemas

LEGACY_SCHEMA = Path(__file__).parent / 'fixtures/legacy_schema.sql'


def test_api_uses_versioned_models_and_public_schema_matches_openapi():
    assert api.ProjectCreate is ProjectCreate
    assert api.Project is Project
    assert export_schemas.export(export_schemas.OUTPUT, check=True) == 0
    components = api.app.openapi()['components']['schemas']
    for name in ('project.create.schema.json', 'project.response.schema.json'):
        schema = json.loads((export_schemas.OUTPUT / name).read_text())
        assert schema.pop('$schema') == 'https://json-schema.org/draft/2020-12/schema'
        assert schema.pop('$id').startswith('urn:animation-studio:contracts:v1:')
        # FastAPI omits null default annotations when serializing OpenAPI.
        for field in schema['properties'].values():
            if 'default' in field and field['default'] is None:
                field.pop('default')
        assert schema == components[schema['title']]


def test_schema_check_detects_missing_modified_and_unexpected_files_without_writing(tmp_path):
    output = tmp_path / 'schemas'
    assert export_schemas.export(output, check=True) == 1
    assert not output.exists()
    assert export_schemas.export(output, check=False) == 0
    assert export_schemas.export(output, check=True) == 0
    changed = output / 'project.create.schema.json'
    changed.write_text('{}\n')
    assert export_schemas.export(output, check=True) == 1
    assert changed.read_text() == '{}\n'
    export_schemas.export(output, check=False)
    extra = output / 'unexpected.schema.json'
    extra.write_text('{}\n')
    assert export_schemas.export(output, check=True) == 1
    assert extra.read_text() == '{}\n'


@pytest.mark.parametrize(
    'revision', ['legacy', '0001_initial', '0002_job_results', '0003_fixture_jobs']
)
def test_migration_preserves_full_project_records_and_existing_api_reads(
    tmp_path, monkeypatch, revision
):
    target = str(tmp_path / 'projects.db')
    if revision == 'legacy':
        with closing(sqlite3.connect(target)) as connection:
            connection.executescript(LEGACY_SCHEMA.read_text())
    else:
        upgrade = db.command.upgrade
        with monkeypatch.context() as patch:
            patch.setattr(db.command, 'upgrade', lambda config, _: upgrade(config, revision))
            db.init_db(target)
    rows = [
        (3, '  untouched  ', '2001-02-03 04:05:06', '2002-03-04 05:06:07', '', 900, 'custom'),
        (4, '', 'old timestamp', 'another timestamp', None, -5, ''),
        (5, 'x' * 201, '2000-01-01', '2000-01-02', None, None, 'draft'),
    ]
    with closing(sqlite3.connect(target)) as connection:
        connection.executemany('INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?)', rows)
        connection.commit()
    db.init_db(target)
    db.init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.row_factory = sqlite3.Row
        stored = [dict(row) for row in connection.execute('SELECT * FROM projects ORDER BY id')]
        assert [tuple(row.values()) for row in stored] == rows
        assert set(ProjectRecord.model_fields) == {
            row['name'] for row in connection.execute('PRAGMA table_info(projects)')
        }
        assert (
            connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]
            == '0003_fixture_jobs'
        )
    for row in stored:
        assert ProjectRecord.model_validate(row).model_dump() == row
    monkeypatch.setenv('ANIMATION_DB_PATH', target)
    with TestClient(api.app) as client:
        expected = [{key: row[key] for key in Project.model_fields} for row in stored]
        assert client.get('/projects').json() == expected
        for row in expected:
            response = client.get(f'/projects/{row["id"]}')
            assert response.status_code == 200
            assert response.json() == row
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute('SELECT * FROM projects ORDER BY id').fetchall() == rows


def test_record_keeps_sql_null_status_without_silently_inventing_api_status(tmp_path, monkeypatch):
    target = str(tmp_path / 'nullable.db')
    db.init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("INSERT INTO projects (title, status) VALUES ('Old', NULL)")
        connection.commit()
        row = dict(connection.execute('SELECT * FROM projects').fetchone())
    assert ProjectRecord.model_validate(row).model_dump() == row
    expected = {key: row[key] for key in Project.model_fields}
    assert Project.model_validate(expected).model_dump() == expected
    monkeypatch.setenv('ANIMATION_DB_PATH', target)
    with TestClient(api.app, raise_server_exceptions=False) as client:
        assert client.get('/projects/1').status_code == 200
        assert client.get('/projects/1').json() == expected
        assert client.get('/projects').json() == [expected]
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute('SELECT status FROM projects').fetchone() == (None,)


def test_record_requires_complete_uncoerced_values_and_preserves_sql_defaults(tmp_path):
    target = str(tmp_path / 'defaults.db')
    db.init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("INSERT INTO projects (title) VALUES ('Defaults')")
        connection.commit()
        row = dict(connection.execute('SELECT * FROM projects').fetchone())
    record = ProjectRecord.model_validate(row)
    assert record.model_dump() == row
    assert record.status == 'draft'
    assert record.target_duration_seconds is None
    assert isinstance(record.created_at, str) and record.created_at
    for key in row:
        with pytest.raises(ValidationError):
            ProjectRecord.model_validate(
                {name: value for name, value in row.items() if name != key}
            )
    for patch in ({'id': '1'}, {'target_duration_seconds': 1.5}, {'extra': True}):
        with pytest.raises(ValidationError):
            ProjectRecord.model_validate({**row, **patch})


@pytest.mark.parametrize('duration', [None, 1, 600, '30', True])
def test_api_request_defaults_coercion_trimming_and_wire_shape(tmp_path, monkeypatch, duration):
    monkeypatch.setenv('ANIMATION_DB_PATH', str(tmp_path / 'api.db'))
    with TestClient(api.app) as client:
        response = client.post(
            '/projects',
            json={
                'title': '  Demo  ',
                'target_duration_seconds': duration,
                'ignored_extra': 'value',
            },
        )
        assert response.status_code == 201
        assert response.json() == {
            'id': 1,
            'title': 'Demo',
            'master_prompt': None,
            'target_duration_seconds': None if duration is None else int(duration),
            'status': 'draft',
        }
        omitted = client.post('/projects', json={'title': 'Second', 'status': ''})
        assert omitted.status_code == 201
        assert omitted.json()['target_duration_seconds'] is None
        assert omitted.json()['status'] == ''


@pytest.mark.parametrize(
    'patch',
    [
        {'title': ''},
        {'title': '   '},
        {'title': 'x' * 201},
        {'title': None},
        {'target_duration_seconds': 0},
        {'target_duration_seconds': 601},
        {'target_duration_seconds': 1.5},
        {'status': None},
    ],
)
def test_api_rejects_existing_invalid_inputs(tmp_path, monkeypatch, patch):
    target = tmp_path / 'invalid.db'
    monkeypatch.setenv('ANIMATION_DB_PATH', str(target))
    with TestClient(api.app) as client:
        response = client.post('/projects', json={'title': 'Valid', **patch})
        assert response.status_code == 422
    assert not target.exists()
