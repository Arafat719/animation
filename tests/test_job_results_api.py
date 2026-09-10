import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from animation_studio.persistence.job_results import JobResultRepository
from animation_studio.pipeline.fake_runner import FakeJobRunner
from animation_studio.providers.fake import FakeConfig, FakeProvider, ProviderError


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = str(tmp_path / 'api-results.db')
    JobResultRepository(path)
    monkeypatch.setenv('ANIMATION_DB_PATH', path)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("INSERT INTO projects (id, title, master_prompt) VALUES (1, 'Scene', 'রাতের শহর')")
        connection.executemany(
            'INSERT INTO render_jobs (id, project_id, state, progress) VALUES (?, 1, ?, ?)',
            [(1, 'queued', 0), (2, 'running', 35), (3, 'completed', 100)],
        )
        connection.commit()
    return path


def snapshot(path):
    with closing(sqlite3.connect(path)) as connection:
        return (connection.execute('SELECT * FROM render_jobs ORDER BY id').fetchall(),
                connection.execute('SELECT * FROM job_results ORDER BY job_id').fetchall())


def test_completed_runner_result_round_trips_after_client_reopen(database):
    saved = FakeJobRunner(database, FakeProvider(FakeConfig(delay_seconds=0))).run(1, seed=42)
    before = snapshot(database)
    for _ in range(2):
        with TestClient(app) as client:
            response = client.get('/jobs/1/result')
            assert response.status_code == 200
            assert response.json() == saved.model_dump(mode='json')
    assert snapshot(database) == before


@pytest.mark.parametrize('code', ['timeout', 'fixture_invalid', 'cancelled'])
def test_runner_errors_are_returned_as_stored_outcomes(database, code):
    class FailedProvider:
        def generate(self, request, *, cancel, on_progress):
            raise ProviderError(code, 'পরীক্ষার জন্য ব্যর্থতা')

    saved = FakeJobRunner(database, FailedProvider()).run(1)
    before = snapshot(database)
    with TestClient(app) as client:
        response = client.get('/jobs/1/result')
    assert response.status_code == 200
    assert response.json() == saved.model_dump(mode='json')
    assert response.json()['result'] is None
    assert response.json()['error']['code'] == code
    assert snapshot(database) == before


def test_missing_outcome_is_null_even_for_legacy_completed_demo(database):
    before = snapshot(database)
    with TestClient(app) as client:
        for job_id in (1, 2, 3):
            response = client.get(f'/jobs/{job_id}/result')
            assert response.status_code == 200
            assert response.json() is None
    assert snapshot(database) == before


@pytest.mark.parametrize(('job_id', 'status'), [('999', 404), ('0', 422), ('-1', 422), ('abc', 422), ('1.5', 422)])
def test_unknown_and_invalid_ids(database, job_id, status):
    before = snapshot(database)
    with TestClient(app) as client:
        assert client.get(f'/jobs/{job_id}/result').status_code == status
    assert snapshot(database) == before


@pytest.mark.parametrize('stored_json', ['broken json', '{}'])
def test_corrupt_result_returns_clear_error_without_overwriting(database, stored_json):
    with closing(sqlite3.connect(database)) as connection:
        connection.execute('INSERT INTO job_results (job_id, result_json) VALUES (1, ?)', (stored_json,))
        connection.commit()
    before = snapshot(database)
    with TestClient(app) as client:
        response = client.get('/jobs/1/result')
    assert response.status_code == 500
    assert response.json() == {'detail': 'সংরক্ষিত job result পড়া যাচ্ছে না।'}
    assert snapshot(database) == before
