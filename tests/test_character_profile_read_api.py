"""Version-aware read compatibility; reviewed writes remain unavailable over HTTP."""

import json
import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError
from test_character_profile import payload
from test_character_review import build, setup

from animation_studio.persistence.db import init_db
from animation_studio.persistence.reviewed_character_profiles import (
    ReviewedCharacterProfileStore,
    SavedReviewedCharacterProfile,
)
from apps.api.character_profiles import VersionedProfile
from apps.api.main import app

NEW = '/v2/characters/1/profile'
OLD = '/characters/1/profile'


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = str(tmp_path / 'read.db')
    monkeypatch.setenv('ANIMATION_DB_PATH', path)
    init_db(path)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("INSERT INTO characters(id,name) VALUES(1,'আলো')")
    return path


def save_reviewed(path):
    profile = build(setup())
    return ReviewedCharacterProfileStore(path).save(
        profile,
        expected_request=profile.provenance.report.request,
        expected_provider=profile.provenance.report.provider,
    )


def test_manual_response_identical_and_empty_read(database):
    with TestClient(app) as client:
        assert client.get(NEW).status_code == 200
        assert client.get(NEW).json() is None
        created = client.post(OLD, json=payload())
        assert created.status_code == 201
        assert client.get(NEW).json() == created.json() == client.get(OLD).json()
        assert created.json()['schema_version'] == 1
        assert created.json()['profile']['source'] == 'user_provided'
    with TestClient(app) as client:
        assert client.get(NEW).json() == created.json()


def test_reviewed_roundtrip_legacy_conflict_and_no_writes(database):
    saved = save_reviewed(database)
    with closing(sqlite3.connect(database)) as connection:
        before = connection.iterdump()
        snapshot = list(before)
    for _ in range(2):
        with TestClient(app) as client:
            result = client.get(NEW)
            assert result.status_code == 200
            assert result.json() == saved.model_dump(mode='json')
            profile = result.json()['profile']
            assert profile['source'] == 'reviewed_extraction'
            assert profile['provenance']['report']['provider']['is_mock'] is True
            assert profile['provenance']['report']['status'] == 'REVIEW_REQUIRED'
            assert profile['provenance']['review']['confirmed'] is True
            old = client.get(OLD)
            assert old.status_code == 409
            assert old.json() == {'detail': 'Unsupported character profile version'}
            duplicate = client.post(OLD, json=payload())
            assert duplicate.status_code == 409
            assert duplicate.json() == {'detail': 'Character profile already saved'}
    with closing(sqlite3.connect(database)) as connection:
        assert list(connection.iterdump()) == snapshot


@pytest.mark.parametrize('prefix', ['', '/v2'])
def test_missing_character_is_404(database, prefix):
    with TestClient(app) as client:
        response = client.get(f'{prefix}/characters/999/profile')
    assert response.status_code == 404
    assert response.json() == {'detail': 'Character not found'}


@pytest.mark.parametrize('identity', ['0', '-1', str(2**63), 'not-an-id'])
@pytest.mark.parametrize('prefix', ['', '/v2'])
def test_invalid_identity_does_not_open_database(tmp_path, monkeypatch, identity, prefix):
    path = tmp_path / 'absent.db'
    monkeypatch.setenv('ANIMATION_DB_PATH', str(path))
    with TestClient(app) as client:
        assert client.get(f'{prefix}/characters/{identity}/profile').status_code == 422
    assert not path.exists()


@pytest.mark.parametrize('damage', ['json', 'hash', 'schema', 'identity', 'origin', 'duplicate'])
def test_reviewed_corruption_is_sanitized(database, damage):
    data = build(setup()).model_dump(mode='json')
    if damage == 'hash':
        data['provenance']['report_hash'] = '0' * 64
    elif damage == 'schema':
        data['schema_version'] = 99
    elif damage == 'identity':
        data['character_id'] = 2
    elif damage == 'origin':
        data['origins']['hair'] = 'user_replacement'
    encoded = 'private-corrupt' if damage == 'json' else json.dumps(data)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            'INSERT INTO reviewed_character_profiles(character_id,schema_version,reviewed_json) VALUES(1,2,?)',
            (encoded,),
        )
        if damage == 'duplicate':
            connection.execute('DROP TRIGGER character_profiles_single_profile')
            connection.execute(
                'INSERT INTO character_profiles(character_id,schema_version,profile_json) VALUES(1,1,?)',
                (json.dumps(payload()),),
            )
    with TestClient(app) as client:
        response = client.get(NEW)
    assert response.status_code == 500
    assert response.json() == {'detail': 'Stored character profile invalid'}
    assert 'private-corrupt' not in response.text


def test_corrupt_manual_read_is_sanitized_on_both_routes(database):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO character_profiles(character_id,schema_version,profile_json) VALUES(1,1,'private-corrupt')"
        )
    with TestClient(app) as client:
        for route in (OLD, NEW):
            response = client.get(route)
            assert response.status_code == 500
            assert response.json() == {'detail': 'Stored character profile invalid'}


@pytest.mark.parametrize('method', ['post', 'put', 'patch', 'delete'])
def test_versioned_route_is_read_only(database, method):
    with TestClient(app) as client:
        response = getattr(client, method)(NEW)
        assert response.status_code == 405
        assert client.get(NEW).json() is None


def test_openapi_discriminated_versions_and_legacy_shape():
    schema = app.openapi()
    path = schema['paths']['/v2/characters/{character_id}/profile']
    assert set(path) == {'get'}
    response = path['get']['responses']['200']['content']['application/json']['schema']
    union = next(branch for branch in response['anyOf'] if 'oneOf' in branch)
    assert union['discriminator'] == {
        'propertyName': 'schema_version',
        'mapping': {
            '1': '#/components/schemas/SavedCharacterProfile',
            '2': '#/components/schemas/SavedReviewedCharacterProfile',
        },
    }
    legacy = schema['paths']['/characters/{character_id}/profile']['get']
    assert legacy['responses']['200']['content']['application/json']['schema']['anyOf'] == [
        {'$ref': '#/components/schemas/SavedCharacterProfile'},
        {'type': 'null'},
    ]


@pytest.mark.parametrize('version', [True, 2.0, '2', 1, 3])
def test_saved_wrapper_keeps_strict_version_validation(database, version):
    saved = save_reviewed(database)
    with pytest.raises(ValidationError):
        SavedReviewedCharacterProfile.model_validate(
            saved.model_copy(update={'schema_version': version})
        )


def test_versioned_union_json_roundtrip_and_unknown_tags(database):
    saved = save_reviewed(database)
    adapter = TypeAdapter(VersionedProfile)
    assert adapter.validate_json(saved.model_dump_json()) == saved
    for version in (True, 2.0, '2', 3, None):
        data = saved.model_dump(mode='json') | {'schema_version': version}
        with pytest.raises(ValidationError):
            adapter.validate_json(json.dumps(data))
