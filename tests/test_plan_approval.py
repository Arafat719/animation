import sqlite3

from fastapi.testclient import TestClient

from apps.api.main import app
from animation_studio.persistence.db import init_db
from animation_studio.persistence.plan_store import PlanStore


def setup(tmp_path, monkeypatch):
    path = str(tmp_path / 'approval.db')
    init_db(path)
    monkeypatch.setenv('ANIMATION_DB_PATH', path)
    api = TestClient(app)
    project = api.post('/projects', json={'title': 'Plan', 'master_prompt': 'River'}).json()
    return api, f'/projects/{project["id"]}/plan', path


def test_edit_approve_render_and_invalidation(tmp_path, monkeypatch):
    api, url, path = setup(tmp_path, monkeypatch)
    draft = api.get(url).json()
    assert draft['revision'] == 0 and not draft['approved']
    assert api.post(url + '/mock-render', json={'revision': 0}).status_code == 409
    assert api.post(url + '/approve', json={'revision': 0}).status_code == 409
    draft['plan']['shots'][0]['image_prompt'] = 'নীল আকাশ'
    saved = api.put(url, json={'revision': 0, 'plan': draft['plan']}).json()
    assert saved['revision'] == 1 and not saved['approved']
    assert api.post(url + '/mock-render', json={'revision': 1}).status_code == 409
    assert api.post(url + '/approve', json={'revision': 1}).status_code == 200
    assert PlanStore(path).read(1).approved
    rendered = api.post(url + '/mock-render', json={'revision': 1}).json()
    assert all(s['status'] == 'completed' for s in rendered['result']['shots'])
    assert rendered['result']['shots'][0]['image_prompt'] == 'নীল আকাশ'
    assert api.post(url + '/mock-render', json={'revision': 1}).json() == rendered
    edited = api.put(url, json={'revision': 1, 'plan': saved['plan']}).json()
    assert edited['revision'] == 2 and not edited['approved'] and edited['result'] is None
    for action in ['approve', 'mock-render']:
        assert api.post(url + '/' + action, json={'revision': 1}).status_code == 409
    assert api.post(url + '/mock-render', json={'revision': 2}).status_code == 409
    assert api.get(url).json() == edited


def test_invalid_edits_and_stale_saves_preserve_saved_plan(tmp_path, monkeypatch):
    api, url, _ = setup(tmp_path, monkeypatch)
    plan = api.get(url).json()['plan']
    saved = api.put(url, json={'revision': 0, 'plan': plan}).json()
    assert api.put(url, json={'revision': 0, 'plan': plan}).status_code == 409
    plan['shots'][0]['image_prompt'] = ''
    assert api.put(url, json={'revision': 1, 'plan': plan}).status_code == 422
    plan['shots'][0]['image_prompt'] = 'River'
    plan['shots'][0]['status'] = 'completed'
    assert api.put(url, json={'revision': 1, 'plan': plan}).status_code == 409
    assert api.get(url).json() == saved
    assert api.post(url + '/approve', json={'revision': True}).status_code == 422


def test_migration_preserves_existing_project(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine
    from pathlib import Path

    path = str(tmp_path / 'old.db')
    config = Config()
    config.set_main_option(
        'script_location', str(Path('animation_studio/persistence/migrations').resolve())
    )
    engine = create_engine('sqlite:///' + path)
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, '0003_fixture_jobs')
    engine.dispose()
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO projects(title,master_prompt,target_duration_seconds) VALUES('Old','River',30)"
        )
        before = db.execute('SELECT * FROM projects').fetchall()
    init_db(path)
    init_db(path)
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT * FROM projects').fetchall() == before
        assert db.execute('SELECT * FROM project_plans').fetchall() == []
    monkeypatch.setenv('ANIMATION_DB_PATH', path)
    assert TestClient(app).get('/projects/1/plan').json()['revision'] == 0


def test_server_gate_prevents_executor_calls(tmp_path, monkeypatch):
    from animation_studio.pipeline.mock_shot_runner import MockShotExecutor

    api, url, _ = setup(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(MockShotExecutor, 'execute', lambda self, shot: calls.append(shot.id))
    plan = api.get(url).json()['plan']
    api.put(url, json={'revision': 0, 'plan': plan})
    assert api.post(url + '/mock-render', json={'revision': 1}).status_code == 409
    assert calls == []
    api.post(url + '/approve', json={'revision': 1})
    assert api.post(url + '/mock-render', json={'revision': 1}).status_code == 200
    assert len(calls) == 6
    api.post(url + '/mock-render', json={'revision': 1})
    assert len(calls) == 6


def test_concurrent_saves_only_one_revision_wins(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from animation_studio.persistence.plan_store import PlanConflict
    from animation_studio.domain.v1.story_plan import StoryPlan

    api, url, path = setup(tmp_path, monkeypatch)
    plan = StoryPlan.model_validate(api.get(url).json()['plan'])

    def save():
        try:
            return PlanStore(path).update(1, 0, 'save', plan).revision
        except PlanConflict:
            return 'conflict'

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: save(), range(2)))
    assert results.count(1) == 1 and results.count('conflict') == 1
