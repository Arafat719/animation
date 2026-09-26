import sqlite3

import pytest
from fastapi.testclient import TestClient

from animation_studio.domain.v1.story_plan import StoryPlan
from animation_studio.persistence.db import init_db
from apps.api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / 'preview.db'
    init_db(str(path))
    monkeypatch.setenv('ANIMATION_DB_PATH', str(path))
    return TestClient(app), path


@pytest.mark.parametrize('duration', [30, 45, 60])
def test_read_only_deterministic_preview(client, duration):
    api, path = client
    project = api.post(
        '/projects',
        json={'title': 'Preview', 'master_prompt': 'নদীর ধারে', 'target_duration_seconds': duration},
    ).json()
    with sqlite3.connect(path) as db:
        before = list(db.iterdump())
    url = f'/projects/{project["id"]}/mock-plan'
    response = api.get(url)
    assert response.status_code == 200
    assert response.json() == api.get(url).json()
    plan = StoryPlan.model_validate_json(response.text)
    assert plan.estimated_total_duration_seconds == duration
    assert all(s.image_prompt == 'নদীর ধারে' for s in plan.shots)
    with sqlite3.connect(path) as db:
        assert list(db.iterdump()) == before


def test_missing_project_and_empty_prompt(client):
    api, _ = client
    assert api.get('/projects/999/mock-plan').status_code == 404
    project = api.post('/projects', json={'title': 'Empty'}).json()
    response = api.get(f'/projects/{project["id"]}/mock-plan')
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.parametrize(
    ('duration', 'prompt', 'status'),
    [(None, 'River', 200), (20, 'River', 422), (30, 'x' * 4001, 422)],
)
def test_legacy_values(client, duration, prompt, status):
    api, path = client
    project = api.post('/projects', json={'title': 'Legacy'}).json()
    with sqlite3.connect(path) as db:
        db.execute(
            'UPDATE projects SET master_prompt=?, target_duration_seconds=? WHERE id=?',
            (prompt, duration, project['id']),
        )
    response = api.get(f'/projects/{project["id"]}/mock-plan')
    assert response.status_code == status
    if status == 200:
        assert response.json()['estimated_total_duration_seconds'] == 30


def test_api_uses_bounded_repair_service(client, monkeypatch):
    from animation_studio.providers.planner import MockPlanner
    from animation_studio.providers.planner_service import MockDraftProvider

    calls = []

    def generate(self, request):
        calls.append('generate')
        return '{'

    def repair(self, request, previous_output, issues):
        calls.append('repair')
        assert previous_output == '{' and issues[0].code == 'INVALID_JSON'
        return MockPlanner().base_plan(request).model_dump_json()

    monkeypatch.setattr(MockDraftProvider, 'generate', generate)
    monkeypatch.setattr(MockDraftProvider, 'repair', repair)
    api, path = client
    project = api.post('/projects', json={'title': 'Repair', 'master_prompt': 'River'}).json()
    with sqlite3.connect(path) as db:
        before = list(db.iterdump())
    response = api.get(f'/projects/{project["id"]}/mock-plan')
    assert response.status_code == 200 and calls == ['generate', 'repair']
    with sqlite3.connect(path) as db:
        assert list(db.iterdump()) == before


def test_api_exhaustion_is_422_without_persisting(client, monkeypatch):
    from animation_studio.providers.planner_service import MockDraftProvider

    calls = []

    def invalid(self, request):
        calls.append(1)
        return '{'

    monkeypatch.setattr(MockDraftProvider, 'generate', invalid)
    api, path = client
    project = api.post('/projects', json={'title': 'Invalid', 'master_prompt': 'River'}).json()
    with sqlite3.connect(path) as db:
        before = list(db.iterdump())
    response = api.get(f'/projects/{project["id"]}/plan')
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'PLANNER_OUTPUT_INVALID'
    assert response.json()['detail']['attempts'] == len(calls) == 2
    with sqlite3.connect(path) as db:
        assert list(db.iterdump()) == before
