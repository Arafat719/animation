import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from test_character_preview_api import dump
from test_character_profile import payload
from test_character_review import build, review
from test_character_review import setup as extraction

from animation_studio.domain.v1.character_extraction import build_extraction_report
from animation_studio.persistence.reviewed_character_profiles import ReviewedCharacterProfileStore
from apps.api import character_preview as module
from apps.api.main import app


@pytest.fixture
def setup(tmp_path, monkeypatch):
    path = str(tmp_path / 'preview.db')
    monkeypatch.setenv('ANIMATION_DB_PATH', path)
    with TestClient(app) as client:
        project = client.post(
            '/projects',
            json={
                'title': 'Preview',
                'master_prompt': 'নদীর ধারে',
                'target_duration_seconds': 30,
            },
        ).json()['id']
        for name in ('Reviewed', 'Manual', 'Empty'):
            client.post('/characters', json={'name': name})
        assert client.post('/characters/2/profile', json=payload()).status_code == 201
        yield client, path, f'/projects/{project}/mock-plan'


def save(path, is_mock=True):
    report = extraction()
    provider = report.provider.model_copy(update={'is_mock': is_mock})
    report = build_extraction_report(report.request, report.candidate, provider=provider)
    profile = build(
        report,
        review(
            report,
            hair={'action': 'replace', 'value': 'সাদা চুল'},
            accessories={'action': 'omit'},
            negative_traits={'action': 'omit'},
        ),
    )
    return ReviewedCharacterProfileStore(path).save(
        profile,
        expected_request=report.request,
        expected_provider=provider,
    )


@pytest.mark.parametrize('is_mock', [True, False])
def test_mixed_cast_final_values_origins_and_no_writes(setup, is_mock):
    client, path, url = setup
    saved = save(path, is_mock)
    before = dump(path)
    response = client.post(url, json={'character_ids': [2, 1]})
    assert response.status_code == 200
    body = response.json()
    assert body == client.post(url, json={'character_ids': [2, 1]}).json()
    assert body['is_mock'] is True and body['status'] == 'REVIEW_REQUIRED'
    assert body['profile_origins'] == [
        {'character_id': 2, 'schema_version': 1, 'source': 'user_provided', 'is_mock': None},
        {
            'character_id': 1,
            'schema_version': 2,
            'source': 'reviewed_extraction',
            'is_mock': is_mock,
        },
    ]
    assert [c['id'] for c in body['plan']['characters']] == ['character-2', 'character-1']
    for shot in body['plan']['shots']:
        assert 'আলো [character-1]: face: গোল মুখ; hair: সাদা চুল' in shot['image_prompt']
        assert 'আলো [character-2]' in shot['image_prompt']
        assert 'character-1' not in shot['negative_prompt']
        assert shot['status'] == 'pending'
    assert saved.profile.values.description not in response.text
    assert saved.profile.provenance.report_hash not in response.text
    assert dump(path) == before


def test_only_selected_origins_returned(setup):
    client, path, url = setup
    save(path)
    body = client.post(url, json={'character_ids': [1]}).json()
    assert len(body['profile_origins']) == 1
    assert body['profile_origins'][0]['is_mock'] is True
    assert body['plan']['characters'] == [{'id': 'character-1', 'name': 'আলো'}]


@pytest.mark.parametrize('damage', ['json', 'hash', 'version', 'duplicate'])
def test_corrupt_reviewed_profile_stops_before_planner(setup, monkeypatch, damage):
    client, path, url = setup
    save(path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('DROP TRIGGER reviewed_character_profiles_no_update')
        if damage == 'json':
            db.execute("UPDATE reviewed_character_profiles SET reviewed_json='private-corrupt'")
        elif damage == 'hash':
            db.execute(
                "UPDATE reviewed_character_profiles SET reviewed_json=json_set(reviewed_json,'$.provenance.report_hash',?)",
                ('0' * 64,),
            )
        elif damage == 'version':
            db.execute('PRAGMA ignore_check_constraints=ON')
            db.execute('UPDATE reviewed_character_profiles SET schema_version=99')
        else:
            db.execute('DROP TRIGGER character_profiles_single_profile')
            db.execute(
                'INSERT INTO character_profiles SELECT 1,schema_version,profile_json,created_at FROM character_profiles WHERE character_id=2'
            )

    def forbidden(*args, **kwargs):
        pytest.fail('Planner must not run for corrupt selection')

    monkeypatch.setattr(module.PlannerService, 'plan', forbidden)
    before = dump(path)
    response = client.post(url, json={'character_ids': [2, 1]})
    assert response.status_code == 500
    assert response.json() == {'detail': 'Stored character profile invalid'}
    assert dump(path) == before


@pytest.mark.parametrize('missing,status', [(3, 409), (999, 404)])
def test_mixed_selection_missing_profile_or_character_no_partial_result(
    setup, monkeypatch, missing, status
):
    client, path, url = setup
    save(path)

    def forbidden(*args, **kwargs):
        pytest.fail('Planner must not run for incomplete selection')

    monkeypatch.setattr(module.PlannerService, 'plan', forbidden)
    before = dump(path)
    response = client.post(url, json={'character_ids': [1, missing]})
    assert response.status_code == status
    assert 'plan' not in response.json()
    assert dump(path) == before


def test_origin_cannot_be_overridden_by_client(setup):
    client, path, url = setup
    save(path)
    before = dump(path)
    response = client.post(url, json={'character_ids': [1], 'profile_origins': []})
    assert response.status_code == 422
    assert dump(path) == before
