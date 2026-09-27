"""Invalid job URLs must be rejected before reaching SQLite."""

import pytest
from fastapi.testclient import TestClient

from animation_studio.persistence.db import init_db
from apps.api import main as api


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / 'jobs.db'
    init_db(str(path))
    monkeypatch.setenv('ANIMATION_DB_PATH', str(path))
    return TestClient(api.app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    'method,suffix', [('get', ''), ('get', '/result'), ('post', '/tick'), ('post', '/cancel')]
)
@pytest.mark.parametrize('job_id', [0, -1, 2**63, 10**40])
def test_invalid_job_id_returns_validation_error(client, method, suffix, job_id):
    response = getattr(client, method)(f'/jobs/{job_id}{suffix}')
    assert response.status_code == 422
    assert response.json()['detail'][0]['loc'] == ['path', 'job_id']


@pytest.mark.parametrize(
    'method,suffix', [('get', ''), ('get', '/result'), ('post', '/tick'), ('post', '/cancel')]
)
def test_largest_sqlite_id_remains_valid_but_not_found(client, method, suffix):
    assert getattr(client, method)(f'/jobs/{2**63 - 1}{suffix}').status_code == 404
