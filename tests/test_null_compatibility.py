"""Nullable legacy jobs remain readable across no-op and cancellation actions."""

import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from animation_studio.persistence import db
from apps.api.main import app


@pytest.mark.parametrize(
    'state,progress', [(None, None), (None, 0), ('running', None), ('completed', None)]
)
def test_null_jobs_tick_cancel_and_reopen(tmp_path, monkeypatch, state, progress):
    target = str(tmp_path / 'jobs.db')
    db.init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.execute(
            'INSERT INTO render_jobs (project_id, state, progress) VALUES (1, ?, ?)',
            (state, progress),
        )
        connection.commit()
    monkeypatch.setenv('ANIMATION_DB_PATH', target)
    with TestClient(app) as client:
        tick = client.post('/jobs/1/tick')
        assert tick.status_code == 200
        assert tick.json()['state'] == state
        assert tick.json()['progress'] == progress
        cancelled = client.post('/jobs/1/cancel')
        assert cancelled.status_code == 200
        expected_state = 'cancelled' if state == 'running' else state
        assert cancelled.json()['state'] == expected_state
        assert cancelled.json()['progress'] == progress
    with TestClient(app) as reopened:
        assert reopened.get('/jobs/1').json() == cancelled.json()
        assert reopened.get('/jobs').json() == [cancelled.json()]
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute('SELECT state, progress FROM render_jobs').fetchone() == (
            expected_state,
            progress,
        )
