"""RenderJob baseline publication, migration preservation and exposed API gaps."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from animation_studio.domain.v1.render_job import (
    FixtureJobCreate,
    JobCreate,
    RenderJob,
    RenderJobRecord,
)
from animation_studio.persistence import db
from scripts import export_schemas
from apps.api import main as api


def test_versioned_models_and_published_schemas():
    assert api.JobCreate is JobCreate
    assert api.FixtureJobCreate is FixtureJobCreate
    assert api.RenderJob is RenderJob
    assert export_schemas.export(export_schemas.OUTPUT, check=True) == 0
    for name, (model, mode) in export_schemas.CONTRACTS.items():
        if not name.startswith(('render-job.', 'fake-provider.')):
            continue
        schema = json.loads((export_schemas.OUTPUT / f'{name}.schema.json').read_text())
        assert schema.pop('$id') == f'urn:animation-studio:contracts:v1:{name}'
        assert schema.pop('$schema') == 'https://json-schema.org/draft/2020-12/schema'
        assert schema == model.model_json_schema(mode=mode)
    for name in ('render-job.create', 'render-job.fixture-create', 'render-job.response'):
        schema = json.loads((export_schemas.OUTPUT / f'{name}.schema.json').read_text())
        schema.pop('$id')
        schema.pop('$schema')
        for field in schema.get('properties', {}).values():
            if field.get('default', 1) is None:
                field.pop('default')
        assert schema == api.app.openapi()['components']['schemas'][schema['title']]


@pytest.mark.parametrize(
    'revision', ['legacy', '0001_initial', '0002_job_results', '0003_fixture_jobs']
)
def test_migration_and_readonly_api_preserve_jobs(tmp_path, monkeypatch, revision):
    target = str(tmp_path / 'jobs.db')
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
        (1, 999, None, None, 'custom', -10, '', 'old timestamp'),
        (2, -1, '  raw\nstep  ', -3, '', 150, 'created', 'updated'),
        (3, 999, '', 0, 'waiting_for_gpu', 0, 'created', 'updated'),
    ]
    with closing(sqlite3.connect(target)) as connection:
        connection.executemany('INSERT INTO render_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)', rows)
        connection.commit()
    monkeypatch.setenv('ANIMATION_DB_PATH', target)
    for _ in range(2):
        db.init_db(target)
        with closing(sqlite3.connect(target)) as connection:
            connection.row_factory = sqlite3.Row
            stored = [
                dict(row) for row in connection.execute('SELECT * FROM render_jobs ORDER BY id')
            ]
            assert [tuple(row.values()) for row in stored] == rows
            assert set(RenderJobRecord.model_fields) == {
                row['name'] for row in connection.execute('PRAGMA table_info(render_jobs)')
            }
            assert (
                connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]
                == '0003_fixture_jobs'
            )
        expected = []
        for row in stored:
            assert RenderJobRecord.model_validate(row).model_dump() == row
            expected.append({key: row[key] for key in RenderJob.model_fields})
        with TestClient(api.app) as client:
            assert client.get('/jobs').json() == expected
            for row in expected:
                assert client.get(f'/jobs/{row["id"]}').json() == row
        with closing(sqlite3.connect(target)) as connection:
            assert connection.execute('SELECT * FROM render_jobs ORDER BY id').fetchall() == rows


def test_sql_defaults_required_record_and_strictness(tmp_path):
    target = str(tmp_path / 'defaults.db')
    db.init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute('INSERT INTO render_jobs (project_id) VALUES (123)')
        connection.commit()
        row = dict(connection.execute('SELECT * FROM render_jobs').fetchone())
    assert row['state'] == 'queued' and row['progress'] == 0
    assert row['current_step'] is None and row['current_shot'] is None
    assert row['created_at'] and row['updated_at']
    record = RenderJobRecord.model_validate(row)
    assert record.model_dump() == row
    for key in row:
        with pytest.raises(ValidationError):
            RenderJobRecord.model_validate({k: v for k, v in row.items() if k != key})
    for patch in (
        {'id': '1'},
        {'project_id': True},
        {'progress': 1.5},
        {'state': 1},
        {'current_step': b'x'},
        {'created_at': None},
        {'extra': 1},
    ):
        with pytest.raises(ValidationError):
            RenderJobRecord.model_validate({**row, **patch})
    with pytest.raises(ValidationError):
        record.state = 'changed'


@pytest.mark.parametrize('field', ['state', 'progress'])
def test_null_sql_values_remain_readable_in_records_and_api(tmp_path, monkeypatch, field):
    target = str(tmp_path / 'null.db')
    db.init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            'INSERT INTO render_jobs (project_id, state, progress) VALUES (1, ?, ?)',
            (None if field == 'state' else 'queued', None if field == 'progress' else 0),
        )
        connection.commit()
        row = dict(connection.execute('SELECT * FROM render_jobs').fetchone())
    assert RenderJobRecord.model_validate(row).model_dump() == row
    expected = {key: row[key] for key in RenderJob.model_fields}
    assert RenderJob.model_validate(row).model_dump() == expected
    monkeypatch.setenv('ANIMATION_DB_PATH', target)
    with TestClient(api.app, raise_server_exceptions=False) as client:
        assert client.get('/jobs').status_code == 200
        assert client.get('/jobs').json() == [expected]
        assert client.get('/jobs/1').status_code == 200
        assert client.get('/jobs/1').json() == expected
    with closing(sqlite3.connect(target)) as connection:
        connection.row_factory = sqlite3.Row
        assert dict(connection.execute('SELECT * FROM render_jobs').fetchone()) == row


@pytest.mark.parametrize(
    'step, expected', [(None, 'queued'), ('', 'queued'), ('  raw  ', '  raw  ')]
)
def test_legacy_create_normalization_extra_policy_and_response(
    tmp_path, monkeypatch, step, expected
):
    monkeypatch.setenv('ANIMATION_DB_PATH', str(tmp_path / 'create.db'))
    with TestClient(api.app) as client:
        project = client.post('/projects', json={'title': 'Test'}).json()
        response = client.post(
            f'/projects/{project["id"]}/jobs', json={'current_step': step, 'ignored': True}
        )
        assert response.status_code == 201
        row = response.json()
        assert set(row) == set(RenderJob.model_fields)
        assert row['current_step'] == expected
        assert row['state'] == 'running' and row['progress'] == 5
        assert row['current_shot'] is None
        assert (
            client.post(
                f'/projects/{project["id"]}/fixture-jobs', json={'ignored': True}
            ).status_code
            == 422
        )
    assert JobCreate().current_step == 'queued'
    assert RenderJob(id=1, project_id=1).state == 'running'
    assert FixtureJobCreate().model_dump() == {}
