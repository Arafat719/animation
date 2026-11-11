"""V2 storage, lossless migration and cross-version immutable single-profile guards."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime
from importlib import import_module
from threading import Barrier

import pytest
from pydantic import ValidationError
from test_character_profile import payload
from test_character_review import build, setup

from animation_studio.domain.v1.character_profile import CharacterProfileDraft
from animation_studio.persistence import db as database_module
from animation_studio.persistence.character_profiles import (
    CharacterProfileStore,
    InvalidStoredProfile,
    ProfileConflict,
    SavedCharacterProfile,
    UnsupportedProfileVersion,
)
from animation_studio.persistence.db import init_db
from animation_studio.persistence.reviewed_character_profiles import (
    ReviewedCharacterProfileStore,
    SavedReviewedCharacterProfile,
)

HEAD = '0006_reviewed_profiles'
PREVIOUS = '0005_character_profiles'


def migrate_to(path, revision, monkeypatch):
    upgrade = database_module.command.upgrade
    with monkeypatch.context() as patch:
        patch.setattr(
            database_module.command, 'upgrade', lambda config, _: upgrade(config, revision)
        )
        init_db(str(path))


@pytest.fixture
def database(tmp_path):
    path = str(tmp_path / 'profiles.db')
    init_db(path)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executemany(
            'INSERT INTO characters(id,name) VALUES(?,?)', [(1, 'আলো'), (2, 'Other')]
        )
    return path


def save(path, profile=None):
    profile = profile if profile is not None else build(setup())
    return ReviewedCharacterProfileStore(path).save(
        profile,
        expected_request=profile.provenance.report.request,
        expected_provider=profile.provenance.report.provider,
    )


def manual_save(path):
    return CharacterProfileStore(path).save(1, CharacterProfileDraft.model_validate(payload()))


def rows(path, table):
    assert table in ('character_profiles', 'reviewed_character_profiles', 'characters')
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()


def test_save_server_timestamps_reopen_and_authoritative_read(database):
    before = datetime.now(UTC)
    profile = build(setup())
    saved = save(database, profile)
    after = datetime.now(UTC)
    assert saved.schema_version == 2 and saved.character_id == 1
    assert saved.profile == profile and saved.profile.provenance.report.provider.is_mock
    assert saved.created_at == saved.reviewed_at
    # SQLite milliseconds truncate, so compare at the same precision.
    assert (
        before.replace(microsecond=(before.microsecond // 1000) * 1000)
        <= datetime.fromisoformat(saved.created_at)
        <= after
    )
    assert SavedReviewedCharacterProfile.model_validate_json(saved.model_dump_json()) == saved
    with pytest.raises(ValidationError):
        saved.reviewed_at = 'changed'
    init_db(database)
    assert ReviewedCharacterProfileStore(database).read(1) == saved
    assert ReviewedCharacterProfileStore(database).read(2) is None
    assert rows(database, 'character_profiles') == []
    with pytest.raises(ProfileConflict):
        save(database)
    assert ReviewedCharacterProfileStore(database).read(1) == saved


def test_manual_snapshot_backward_read_and_both_save_orders(database):
    saved = manual_save(database)
    before = rows(database, 'character_profiles')
    assert isinstance(saved, SavedCharacterProfile)
    assert ReviewedCharacterProfileStore(database).read(1) == saved
    with pytest.raises(ProfileConflict):
        save(database)
    assert rows(database, 'character_profiles') == before
    assert rows(database, 'reviewed_character_profiles') == []


def test_reviewed_prevents_manual_save_and_v1_null_read(database):
    saved = save(database)
    with pytest.raises(ProfileConflict):
        manual_save(database)
    with pytest.raises(UnsupportedProfileVersion, match='Unsupported character profile version'):
        CharacterProfileStore(database).read(1)
    assert ReviewedCharacterProfileStore(database).read(1) == saved
    assert rows(database, 'character_profiles') == []


@pytest.mark.parametrize('reviewed_first', [True, False])
@pytest.mark.parametrize('replace', [True, False])
def test_sql_guard_blocks_old_writers_both_directions(database, reviewed_first, replace):
    save(database) if reviewed_first else manual_save(database)
    table = 'character_profiles' if reviewed_first else 'reviewed_character_profiles'
    column = 'profile_json' if reviewed_first else 'reviewed_json'
    version = 1 if reviewed_first else 2
    existing_table = 'reviewed_character_profiles' if reviewed_first else 'character_profiles'
    before = rows(database, existing_table)
    with (
        closing(sqlite3.connect(database)) as connection,
        connection,
        pytest.raises(sqlite3.IntegrityError, match='already saved'),
    ):
        connection.execute(
            f'INSERT {"OR REPLACE " if replace else ""}INTO {table}'
            f'(character_id,schema_version,{column}) VALUES(1,?,?)',
            (version, '{}'),
        )
    assert rows(database, table) == []
    assert rows(database, existing_table) == before


@pytest.mark.parametrize('table', ['character_profiles', 'reviewed_character_profiles'])
def test_sql_same_table_replace_cannot_overwrite(database, table):
    save(database) if table == 'reviewed_character_profiles' else manual_save(database)
    before = rows(database, table)
    column = 'profile_json' if table == 'character_profiles' else 'reviewed_json'
    version = 1 if table == 'character_profiles' else 2
    with (
        closing(sqlite3.connect(database)) as connection,
        connection,
        pytest.raises(sqlite3.IntegrityError, match='already saved'),
    ):
        connection.execute(
            f'INSERT OR REPLACE INTO {table}(character_id,schema_version,{column}) VALUES(1,?,?)',
            (version, '{}'),
        )
    assert rows(database, table) == before


@pytest.mark.parametrize(
    'column,value',
    [
        ('reviewed_json', '{}'),
        ('character_id', 2),
        ('schema_version', 1),
        ('created_at', 'changed'),
        ('reviewed_at', 'changed'),
    ],
)
def test_sql_updates_rejected(database, column, value):
    saved = save(database)
    with (
        closing(sqlite3.connect(database)) as connection,
        connection,
        pytest.raises(sqlite3.IntegrityError, match='immutable'),
    ):
        connection.execute(
            f'UPDATE reviewed_character_profiles SET {column}=? WHERE character_id=1', (value,)
        )
    assert ReviewedCharacterProfileStore(database).read(1) == saved


@pytest.mark.parametrize('kinds', [('manual', 'reviewed'), ('reviewed', 'reviewed')])
def test_concurrent_saves_have_exactly_one_winner(database, kinds):
    barrier = Barrier(2)

    def attempt(kind):
        barrier.wait(timeout=10)
        try:
            return manual_save(database) if kind == 'manual' else save(database)
        except ProfileConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, kinds))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    assert ReviewedCharacterProfileStore(database).read(1) == winners[0]
    assert (
        len(rows(database, 'character_profiles'))
        + len(rows(database, 'reviewed_character_profiles'))
        == 1
    )


def test_missing_character_no_write(database):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute('DELETE FROM characters WHERE id=1')
    with pytest.raises(LookupError, match='Character not found'):
        save(database)
    with pytest.raises(LookupError, match='Character not found'):
        ReviewedCharacterProfileStore(database).read(1)
    assert rows(database, 'reviewed_character_profiles') == []


@pytest.mark.parametrize('identity', [True, 0, -1, 2**63, '1'])
def test_read_invalid_id_before_database_open(tmp_path, identity):
    path = tmp_path / 'absent.db'
    with pytest.raises(ValueError):
        ReviewedCharacterProfileStore(str(path)).read(identity)
    assert not path.exists()


@pytest.mark.parametrize('change', ['profile', 'request', 'provider', 'timestamp'])
def test_save_revalidates_before_database_open(tmp_path, change):
    path = tmp_path / 'absent.db'
    profile = build(setup())
    req = profile.provenance.report.request
    provider = profile.provenance.report.provider
    if change == 'profile':
        profile = profile.model_copy(
            update={'values': profile.values.model_copy(update={'name': 'tampered'})}
        )
    elif change == 'request':
        req = req.model_copy(update={'character_id': 2})
    elif change == 'provider':
        provider = provider.model_copy(update={'is_mock': False})
    else:
        profile = profile.model_copy(update={'created_at': 'caller time'})
    with pytest.raises(ValueError):
        ReviewedCharacterProfileStore(str(path)).save(
            profile, expected_request=req, expected_provider=provider
        )
    assert not path.exists()


@pytest.mark.parametrize(
    'damage', ['json', 'hash', 'identity', 'schema', 'origin', 'timestamp', 'sql_schema']
)
def test_corrupt_stored_data_is_sanitized_not_null(database, damage):
    profile = build(setup()).model_dump(mode='json')
    timestamp = '2026-10-12T00:00:00Z'
    version = 2
    if damage == 'hash':
        profile['provenance']['report_hash'] = '0' * 64
    elif damage == 'identity':
        # Valid envelope for character 1 stored under character 2.
        pass
    elif damage == 'schema':
        profile['schema_version'] = 3
    elif damage == 'origin':
        profile['origins']['hair'] = 'user_replacement'
    elif damage == 'timestamp':
        timestamp = 'private-corrupt-time'
    elif damage == 'sql_schema':
        version = 3
    encoded = 'private-corrupt-json' if damage == 'json' else json.dumps(profile)
    identity = 2 if damage == 'identity' else 1
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute('PRAGMA ignore_check_constraints=ON')
        connection.execute(
            'INSERT INTO reviewed_character_profiles VALUES(?,?,?,?,?)',
            (identity, version, encoded, timestamp, timestamp),
        )
    with pytest.raises(InvalidStoredProfile) as error:
        ReviewedCharacterProfileStore(database).read(identity)
    assert str(error.value) == 'Stored character profile invalid'


def test_corrupt_manual_or_duplicate_rows_do_not_fallback(database):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO character_profiles(character_id,schema_version,profile_json) VALUES(1,1,'private-corrupt')"
        )
    with pytest.raises(InvalidStoredProfile):
        ReviewedCharacterProfileStore(database).read(1)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute('DROP TRIGGER reviewed_character_profiles_single_profile')
        connection.execute(
            'INSERT INTO reviewed_character_profiles(character_id,schema_version,reviewed_json) VALUES(1,2,?)',
            (build(setup()).model_dump_json(),),
        )
    with pytest.raises(InvalidStoredProfile):
        ReviewedCharacterProfileStore(database).read(1)


def test_failed_save_rolls_back_and_can_retry(database, monkeypatch):
    def fail(_):
        raise RuntimeError('Simulated failure after insert before commit')

    with monkeypatch.context() as patch:
        patch.setattr(ReviewedCharacterProfileStore, '_view', staticmethod(fail))
        with pytest.raises(RuntimeError, match='Simulated failure'):
            save(database)
    assert rows(database, 'reviewed_character_profiles') == []
    saved = save(database)
    assert ReviewedCharacterProfileStore(database).read(1) == saved


def test_unrelated_integrity_failure_is_not_profile_conflict(database):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "CREATE TRIGGER fail_reviewed BEFORE INSERT ON reviewed_character_profiles BEGIN SELECT RAISE(ABORT, 'other constraint'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match='other constraint'):
        save(database)
    assert rows(database, 'reviewed_character_profiles') == []


def test_foreign_key_and_version_constraints(database):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute('PRAGMA foreign_keys=ON')
        with pytest.raises(sqlite3.IntegrityError, match='FOREIGN KEY'):
            connection.execute(
                "INSERT INTO reviewed_character_profiles(character_id,schema_version,reviewed_json) VALUES(999,2,'{}')"
            )
        with pytest.raises(sqlite3.IntegrityError, match='CHECK'):
            connection.execute(
                "INSERT INTO reviewed_character_profiles(character_id,schema_version,reviewed_json) VALUES(1,1,'{}')"
            )


def test_migration_preserves_v1_bytes_and_downgrade_forbidden(tmp_path, monkeypatch):
    path = str(tmp_path / 'old.db')
    migrate_to(path, PREVIOUS, monkeypatch)
    encoded = json.dumps(payload(), ensure_ascii=False, indent=3)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            "INSERT INTO characters(id,name,description) VALUES(1,' Legacy ',' untouched ')"
        )
        connection.execute(
            'INSERT INTO character_profiles VALUES(1,1,?,?)', (encoded, 'old timestamp')
        )
    before = rows(path, 'character_profiles')
    characters = rows(path, 'characters')
    init_db(path)
    init_db(path)
    assert rows(path, 'character_profiles') == before
    assert rows(path, 'characters') == characters
    assert rows(path, 'reviewed_character_profiles') == []
    assert ReviewedCharacterProfileStore(path).read(1) == CharacterProfileStore(path).read(1)
    with pytest.raises(RuntimeError, match='Destructive downgrade'):
        import_module(
            'animation_studio.persistence.migrations.versions.0006_reviewed_profiles'
        ).downgrade()
    assert rows(path, 'character_profiles') == before


def test_v2_migration_failure_rolls_back_schema_and_retries(tmp_path, monkeypatch):
    path = str(tmp_path / 'rollback.db')
    migrate_to(path, PREVIOUS, monkeypatch)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("INSERT INTO characters(id,name) VALUES(1,'Keep')")
    upgrade = database_module.command.upgrade

    def fail(config, revision):
        upgrade(config, revision)
        raise RuntimeError('Interrupted migration')

    with monkeypatch.context() as patch:
        patch.setattr(database_module.command, 'upgrade', fail)
        with pytest.raises(RuntimeError, match='Interrupted migration'):
            init_db(path)
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone() == (
            PREVIOUS,
        )
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name LIKE '%reviewed%' OR name LIKE '%single_profile%'"
            ).fetchall()
            == []
        )
    init_db(path)
    assert save(path).profile.provenance.report.provider.is_mock
