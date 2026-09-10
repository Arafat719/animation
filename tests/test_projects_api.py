import sqlite3

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api import main as api
from animation_studio.persistence.db import init_db


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / 'projects.db'
    init_db(str(db_path))
    return str(db_path)


def test_project_crud_flow(temp_db, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', temp_db)

    client = TestClient(app)

    create_response = client.post(
        '/projects',
        json={'title': 'Demo Project', 'master_prompt': 'anime girl in neon city', 'target_duration_seconds': 30},
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload['title'] == 'Demo Project'
    assert payload['id'] == 1

    list_response = client.get('/projects')
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1

    detail_response = client.get('/projects/1')
    assert detail_response.status_code == 200
    assert detail_response.json()['id'] == 1


def test_invalid_project_input_returns_422(temp_db, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', temp_db)
    client = TestClient(app)

    response = client.post('/projects', json={'title': '', 'target_duration_seconds': 10})
    assert response.status_code == 422


def test_fake_job_creation_and_progress(temp_db, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', temp_db)
    client = TestClient(app)

    project_response = client.post(
        '/projects',
        json={'title': 'Job Project', 'master_prompt': 'anime city scene', 'target_duration_seconds': 45},
    )
    project_id = project_response.json()['id']

    create_job_response = client.post(f'/projects/{project_id}/jobs', json={'current_step': 'prompting'})
    assert create_job_response.status_code == 201
    job_payload = create_job_response.json()
    assert job_payload['project_id'] == project_id
    assert job_payload['state'] == 'running'
    assert 0 <= job_payload['progress'] <= 100

    jobs_response = client.get('/jobs')
    assert jobs_response.status_code == 200
    assert len(jobs_response.json()) == 1

    tick_response = client.post(f"/jobs/{job_payload['id']}/tick")
    assert tick_response.status_code == 200
    assert tick_response.json()['progress'] >= job_payload['progress']


def test_fake_job_cancel_marks_state_cancelled(temp_db, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', temp_db)
    client = TestClient(app)

    project_response = client.post(
        '/projects',
        json={'title': 'Cancel Project', 'master_prompt': 'anime city lights', 'target_duration_seconds': 40},
    )
    project_id = project_response.json()['id']

    job_response = client.post(f'/projects/{project_id}/jobs', json={'current_step': 'rendering'})
    job_id = job_response.json()['id']

    cancel_response = client.post(f'/jobs/{job_id}/cancel')
    assert cancel_response.status_code == 200
    assert cancel_response.json()['state'] == 'cancelled'
    stopped_progress = cancel_response.json()['progress']

    tick_response = client.post(f'/jobs/{job_id}/tick')
    assert tick_response.status_code == 200
    assert tick_response.json()['state'] == 'cancelled'
    assert tick_response.json()['progress'] == stopped_progress

    repeat = client.post(f'/jobs/{job_id}/cancel')
    assert repeat.json() == cancel_response.json()
    assert TestClient(app).get('/jobs').json()[0]['progress'] == stopped_progress


def test_in_flight_tick_cannot_restart_cancelled_job(temp_db, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', temp_db)
    client = TestClient(app)
    project_id = client.post('/projects', json={'title': 'Race test'}).json()['id']
    job_id = client.post(f'/projects/{project_id}/jobs', json={}).json()['id']
    get_connection = api.get_connection

    class CancelBeforeUpdate(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if 'UPDATE render_jobs' in sql:
                # A second request commits cancellation after tick read the row.
                other = get_connection()
                try:
                    other.execute("UPDATE render_jobs SET state='cancelled' WHERE id=?", (job_id,))
                    other.commit()
                finally:
                    other.close()
            return super().execute(sql, parameters)

    def raced_connection():
        connection = sqlite3.connect(temp_db, factory=CancelBeforeUpdate)
        connection.row_factory = sqlite3.Row
        return connection

    with monkeypatch.context() as patch:
        patch.setattr(api, 'get_connection', raced_connection)
        result = client.post(f'/jobs/{job_id}/tick')
    assert result.status_code == 200
    assert result.json()['state'] == 'cancelled'
    assert result.json()['progress'] == 5


def test_cancel_preserves_completed_job_and_other_job_progress(temp_db, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', temp_db)
    client = TestClient(app)
    project_id = client.post('/projects', json={'title': 'Terminal jobs'}).json()['id']
    first = client.post(f'/projects/{project_id}/jobs', json={}).json()['id']
    second = client.post(f'/projects/{project_id}/jobs', json={}).json()['id']
    for _ in range(7):
        complete = client.post(f'/jobs/{first}/tick')
    assert complete.json()['state'] == 'completed'
    assert client.post(f'/jobs/{first}/cancel').json() == complete.json()
    assert client.post(f'/jobs/{second}/tick').json()['progress'] == 20
    assert client.post('/jobs/99999/cancel').status_code == 404
