import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

import pytest
from alembic.util.exc import CommandError
from fastapi.testclient import TestClient

from animation_studio.persistence import db
from animation_studio.persistence.db import init_db
from apps.api.main import app


LEGACY_SCHEMA = Path(__file__).parent / 'fixtures' / 'legacy_schema.sql'


def test_init_db_creates_expected_tables(tmp_path):
    db_path = tmp_path / 'test_animation.db'

    init_db(str(db_path))

    assert os.path.exists(db_path)

    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        ).fetchall()
        names = {row[0] for row in tables}
        assert 'projects' in names
        assert 'characters' in names
        assert 'voices' in names
        assert 'shots' in names
        assert 'render_jobs' in names
        assert 'job_results' in names
        assert conn.execute('SELECT version_num FROM alembic_version').fetchall() == [('0003_fixture_jobs',)]
    finally:
        conn.close()


def test_legacy_migration_preserves_all_rows_and_api_reads(tmp_path, monkeypatch):
    target = str(tmp_path / 'legacy.db')
    with closing(sqlite3.connect(target)) as connection:
        connection.executescript(LEGACY_SCHEMA.read_text())
        connection.execute("INSERT INTO projects (id, title, master_prompt, target_duration_seconds) VALUES (7, 'Saved project', 'City', 45)")
        connection.execute("INSERT INTO characters (name, description) VALUES ('Airi', 'Blue hair')")
        connection.execute("INSERT INTO voices (name, voice_type) VALUES ('Voice', 'built_in')")
        connection.execute("INSERT INTO shots (project_id, order_index, duration_seconds, prompt) VALUES (7, 0, 5, 'City shot')")
        connection.execute("INSERT INTO render_jobs (id, project_id, state, progress) VALUES (9, 7, 'cancelled', 35)")
        connection.commit()
        tables = ['projects', 'characters', 'voices', 'shots', 'render_jobs']
        before = {name: connection.execute(f'SELECT * FROM {name}').fetchall() for name in tables}

    init_db(target)
    init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        after = {name: connection.execute(f'SELECT * FROM {name}').fetchall() for name in tables}
        assert after == before
        assert connection.execute('SELECT version_num FROM alembic_version').fetchall() == [('0003_fixture_jobs',)]

    monkeypatch.setenv('ANIMATION_DB_PATH', target)
    with TestClient(app) as client:
        project = client.get('/projects/7')
        assert project.status_code == 200
        assert project.json()['title'] == 'Saved project'
        assert project.json()['target_duration_seconds'] == 45
        jobs = client.get('/jobs')
        assert jobs.status_code == 200
        assert jobs.json()[0]['progress'] == 35
        assert jobs.json()[0]['state'] == 'cancelled'
        created = client.post('/projects', json={'title': 'Next project'})
        assert created.status_code == 201
        assert created.json()['id'] == 8


def test_incompatible_legacy_schema_rolls_back_created_tables(tmp_path):
    target = str(tmp_path / 'incompatible.db')
    with closing(sqlite3.connect(target)) as connection:
        connection.execute('CREATE TABLE characters (id INTEGER PRIMARY KEY, name TEXT)')
        connection.execute("INSERT INTO characters (name) VALUES ('Keep me')")
        connection.commit()

    with pytest.raises(RuntimeError, match='Incompatible legacy table: characters'):
        init_db(target)

    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [('characters',)]
        assert connection.execute('SELECT name FROM characters').fetchone() == ('Keep me',)


def test_failed_migration_rolls_back_version_and_can_retry(tmp_path, monkeypatch):
    target = str(tmp_path / 'failed.db')
    original = db.command.upgrade

    def fail_after_upgrade(config, revision):
        original(config, revision)
        raise RuntimeError('Simulated interruption before commit')

    with monkeypatch.context() as patch:
        patch.setattr(db.command, 'upgrade', fail_after_upgrade)
        with pytest.raises(RuntimeError, match='Simulated interruption'):
            init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []

    init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone() == ('0003_fixture_jobs',)


def test_unknown_database_revision_is_not_overwritten(tmp_path):
    target = str(tmp_path / 'future.db')
    with closing(sqlite3.connect(target)) as connection:
        connection.execute('CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY NOT NULL)')
        connection.execute("INSERT INTO alembic_version VALUES ('future_revision')")
        connection.commit()
    with pytest.raises(CommandError, match='future_revision'):
        init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone() == ('future_revision',)
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='projects'").fetchone() is None


def test_parallel_initialization_is_repeatable(tmp_path):
    target = str(tmp_path / 'parallel.db')
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(init_db, [target] * 4)) == [target] * 4
    with closing(sqlite3.connect(target)) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchall() == [('0003_fixture_jobs',)]


def test_database_path_with_spaces_and_url_characters(tmp_path):
    target = str(tmp_path / 'nested folder' / 'scene #%?.db')
    assert init_db(target) == target
    assert Path(target).is_file()
