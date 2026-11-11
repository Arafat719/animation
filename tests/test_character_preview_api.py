import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from test_character_profile import payload

from apps.api import character_preview as module
from apps.api.main import app


@pytest.fixture
def setup(tmp_path, monkeypatch):
    path = tmp_path / 'preview.db'
    monkeypatch.setenv('ANIMATION_DB_PATH', str(path))
    client = TestClient(app)
    project = client.post(
        '/projects',
        json={'title': 'Preview', 'master_prompt': 'নদীর ধারে', 'target_duration_seconds': 30},
    ).json()['id']
    ids = []
    for name in ['First', 'Second']:
        identity = client.post('/characters', json={'name': name}).json()['id']
        assert client.post(f'/characters/{identity}/profile', json=payload()).status_code == 201
        ids.append(identity)
    return client, path, f'/projects/{project}/mock-plan', ids


def dump(path):
    with closing(sqlite3.connect(path)) as db:
        return list(db.iterdump())


def test_selected_order_unicode_determinism_and_no_writes(setup):
    client, path, url, ids = setup
    old = client.get(url).json()
    before = dump(path)
    response = client.post(url, json={'character_ids': ids[::-1]})
    assert response.status_code == 200
    assert response.json() == client.post(url, json={'character_ids': ids[::-1]}).json()
    body = response.json()
    assert body['is_mock'] is True and body['status'] == 'REVIEW_REQUIRED'
    assert [c['id'] for c in body['plan']['characters']] == [f'character-{i}' for i in ids[::-1]]
    for shot in body['plan']['shots']:
        assert 'hair: কালো চুল' in shot['image_prompt']
        assert 'লাল পোশাক' in shot['negative_prompt']
        assert shot['status'] == 'pending'
    assert client.get(url).json() == old
    assert dump(path) == before


def test_only_selected_snapshot_is_used_with_default_duration(setup):
    client, path, url, ids = setup
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('UPDATE projects SET target_duration_seconds=NULL')
        db.execute('UPDATE characters SET name=?', ('Changed legacy name',))
    before = dump(path)
    response = client.post(url, json={'character_ids': [ids[1]]})
    assert response.status_code == 200
    plan = response.json()['plan']
    assert plan['characters'] == [{'id': f'character-{ids[1]}', 'name': 'আলো'}]
    assert plan['estimated_total_duration_seconds'] == 30
    for shot in plan['shots']:
        assert shot['visible_character_ids'] == [f'character-{ids[1]}']
        assert f'character-{ids[0]}' not in shot['image_prompt']
        assert 'Changed legacy name' not in shot['image_prompt']
    assert dump(path) == before


@pytest.mark.parametrize(
    'body',
    [
        {},
        {'character_ids': []},
        {'character_ids': [1, 1]},
        {'character_ids': [True]},
        {'character_ids': ['1']},
        {'character_ids': [0]},
        {'character_ids': [2**63]},
        {'character_ids': list(range(1, 102))},
        {'character_ids': [1], 'extra': True},
    ],
)
def test_invalid_selection_before_database(tmp_path, monkeypatch, body):
    path = tmp_path / 'absent.db'
    monkeypatch.setenv('ANIMATION_DB_PATH', str(path))
    assert TestClient(app).post('/projects/1/mock-plan', json=body).status_code == 422
    assert not path.exists()


def test_missing_inputs_do_not_call_planner(setup, monkeypatch):
    client, path, url, ids = setup

    def forbidden(*args, **kwargs):
        pytest.fail('Planner must not run')

    monkeypatch.setattr(module.PlannerService, 'plan', forbidden)
    before = dump(path)
    assert client.post('/projects/999/mock-plan', json={'character_ids': ids}).status_code == 404
    assert client.post(url, json={'character_ids': [999]}).status_code == 404
    assert client.post(url, json={'character_ids': [ids[0], 999]}).status_code == 404
    assert dump(path) == before
    identity = client.post('/characters', json={'name': 'No profile'}).json()['id']
    before = dump(path)
    assert client.post(url, json={'character_ids': [identity]}).status_code == 409
    assert dump(path) == before


def test_prompt_overflow_rejected_without_write_or_retry(setup, monkeypatch):
    client, path, url, ids = setup
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('UPDATE projects SET master_prompt=?', ('x' * 4000,))
    before = dump(path)
    calls = []
    original = module.MockDraftProvider.generate

    def generate(self, request):
        calls.append(1)
        return original(self, request)

    monkeypatch.setattr(module.MockDraftProvider, 'generate', generate)
    response = client.post(url, json={'character_ids': ids})
    assert response.status_code == 422 and calls == [1]
    assert response.json()['detail']['code'] == 'PLANNER_OUTPUT_INVALID'
    assert dump(path) == before


def test_corrupt_profile_sanitized(setup):
    client, path, url, ids = setup
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('DROP TRIGGER character_profiles_no_update')
        db.execute(
            "UPDATE character_profiles SET profile_json='private-corrupt' WHERE character_id=?",
            (ids[0],),
        )
    before = dump(path)
    response = client.post(url, json={'character_ids': ids})
    assert response.status_code == 500
    assert 'private-corrupt' not in response.text
    assert dump(path) == before


@pytest.mark.parametrize('prompt,duration', [(None, 30), (' ', 30), ('River', 20)])
def test_invalid_project_values_reject_without_write(setup, prompt, duration):
    client, path, url, ids = setup
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(
            'UPDATE projects SET master_prompt=?,target_duration_seconds=?', (prompt, duration)
        )
    before = dump(path)
    assert client.post(url, json={'character_ids': ids}).status_code == 422
    assert dump(path) == before
