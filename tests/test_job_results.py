import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from animation_studio.persistence import db
from animation_studio.persistence.job_results import (
    JobResultConflictError, JobResultRepository, Outcome, StoredError, UnknownJobError,
)
from animation_studio.providers.fake import FakeConfig, FakeProvider, FakeRequest


@pytest.fixture(scope='module')
def result():
    return FakeProvider(FakeConfig(delay_seconds=0)).generate(FakeRequest(prompt='Test scene', seed=42))


def seed_jobs(path):
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("INSERT INTO projects (id, title) VALUES (1, 'Keep project')")
        connection.execute("INSERT INTO render_jobs (id, project_id, state, progress) VALUES (1, 1, 'running', 35)")
        connection.execute("INSERT INTO render_jobs (id, project_id, state, progress) VALUES (2, 1, 'failed', 60)")
        connection.commit()


@pytest.fixture
def repository(tmp_path):
    repository = JobResultRepository(str(tmp_path / 'results.db'))
    seed_jobs(repository.db_path)
    return repository


def snapshot_jobs(path):
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute('SELECT * FROM render_jobs ORDER BY id').fetchall()


def test_success_and_error_survive_reopen_without_changing_jobs(repository, result):
    before = snapshot_jobs(repository.db_path)
    assert repository.get(1) is None
    saved = repository.save_success(1, result)
    failure = repository.save_error(2, StoredError(code='fixture_invalid', message='Cannot decode sample'))
    reopened = JobResultRepository(repository.db_path)
    assert reopened.get(1) == saved
    assert saved.result == result
    assert saved.schema_version == 1
    assert saved.created_at
    assert reopened.get(2) == failure
    assert failure.error.code == 'fixture_invalid'
    assert snapshot_jobs(repository.db_path) == before


def test_identical_retries_preserve_record_and_different_writes_conflict(repository, result):
    original = repository.save_success(1, result)
    assert repository.save_success(1, result.model_dump(mode='json')) == original
    with pytest.raises(JobResultConflictError):
        repository.save_success(1, result.model_copy(update={'seed': 43}))
    with pytest.raises(JobResultConflictError):
        repository.save_error(1, StoredError(code='timeout', message='Too late'))
    assert repository.get(1) == original
    error = StoredError(code='timeout', message='Deadline exceeded')
    failed = repository.save_error(2, error)
    assert repository.save_error(2, error) == failed
    with pytest.raises(JobResultConflictError):
        repository.save_success(2, result)
    assert repository.get(2) == failed


def test_unknown_jobs_rejected_without_inserting(repository, result):
    for operation in (
        lambda: repository.get(999), lambda: repository.save_success(999, result),
        lambda: repository.save_error(999, {'code': 'timeout', 'message': 'Expired'}),
    ):
        with pytest.raises(UnknownJobError):
            operation()
    with closing(sqlite3.connect(repository.db_path)) as connection:
        assert connection.execute('SELECT * FROM job_results').fetchall() == []


@pytest.mark.parametrize('job_id', [0, -1, True, '1'])
def test_invalid_job_id_rejected(repository, result, job_id):
    with pytest.raises(ValueError):
        repository.save_success(job_id, result)
    assert repository.get(1) is None


@pytest.mark.parametrize('invalid', ['missing', 'checksum', 'kind', 'relative_path', 'duration', 'seed', 'extra'])
def test_invalid_result_rejected(repository, result, invalid):
    payload = result.model_dump(mode='json')
    if invalid == 'missing':
        del payload['video']
    elif invalid == 'checksum':
        payload['image']['sha256'] = 'bad'
    elif invalid == 'kind':
        payload['image']['kind'] = 'audio'
    elif invalid == 'relative_path':
        payload['image']['path'] = 'relative.png'
    elif invalid == 'duration':
        payload['audio']['duration_seconds'] = None
    elif invalid == 'seed':
        payload['seed'] = -1
    else:
        payload['unexpected'] = 'value'
    with pytest.raises(ValidationError):
        repository.save_success(1, payload)
    assert repository.get(1) is None


def test_unvalidated_model_copy_is_revalidated(repository, result):
    with pytest.raises(ValidationError):
        repository.save_success(1, result.model_copy(update={'seed': -1}))
    assert repository.get(1) is None


def test_invalid_error_and_ambiguous_outcome_rejected(repository, result):
    for error in ({'code': 'unknown', 'message': 'Failed'}, {'code': 'timeout', 'message': '   '}):
        with pytest.raises(ValidationError):
            repository.save_error(1, error)
    with pytest.raises(ValidationError):
        Outcome()
    with pytest.raises(ValidationError):
        Outcome(result=result, error=StoredError(code='timeout', message='Failed'))
    assert repository.get(1) is None


def test_sql_like_error_text_round_trips(repository):
    error = StoredError(code='io_error', message="Couldn't read 'sample'); DROP TABLE render_jobs; --")
    assert repository.save_error(1, error).error == error
    assert len(snapshot_jobs(repository.db_path)) == 2


def test_concurrent_retries_and_conflicts_keep_one_outcome(repository, result):
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda _: repository.save_success(1, result), range(4)))
    assert all(record == records[0] for record in records)

    def attempt(seed):
        try:
            repository.save_success(2, result.model_copy(update={'seed': seed}))
            return 'saved'
        except JobResultConflictError:
            return 'conflict'

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, [10, 20])) == ['conflict', 'saved']
    with closing(sqlite3.connect(repository.db_path)) as connection:
        assert connection.execute('SELECT count(*) FROM job_results').fetchone() == (2,)


def test_database_constraints_reject_orphans_and_ambiguous_rows(repository):
    with closing(sqlite3.connect(repository.db_path)) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        for job_id, result_json, code, message in (
            (999, None, 'timeout', 'Failed'), (1, None, None, None),
            (1, '{}', 'timeout', 'Failed'), (1, None, '', ''),
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute('INSERT INTO job_results (job_id, result_json, error_code, error_message) VALUES (?, ?, ?, ?)',
                                   (job_id, result_json, code, message))
        assert connection.execute('SELECT count(*) FROM job_results').fetchone() == (0,)


def test_corrupt_stored_json_is_reported_and_not_overwritten(repository, result):
    with closing(sqlite3.connect(repository.db_path)) as connection:
        connection.execute("INSERT INTO job_results (job_id, result_json) VALUES (1, 'broken json')")
        connection.commit()
    with pytest.raises(ValidationError):
        repository.get(1)
    with pytest.raises(ValidationError):
        repository.save_success(1, result)


def test_repository_keeps_its_database_after_cwd_change(tmp_path, monkeypatch, result):
    monkeypatch.chdir(tmp_path)
    repository = JobResultRepository('relative.db')
    seed_jobs(repository.db_path)
    other = tmp_path / 'other'
    other.mkdir()
    monkeypatch.chdir(other)
    assert repository.save_success(1, result).result == result
    assert list(other.iterdir()) == []


@pytest.fixture
def old_database(tmp_path, monkeypatch):
    path = str(tmp_path / 'old.db')
    upgrade = db.command.upgrade
    with monkeypatch.context() as patch:
        patch.setattr(db.command, 'upgrade', lambda config, _: upgrade(config, '0001_initial'))
        db.init_db(path)
    seed_jobs(path)
    return path


def test_upgrade_from_0001_preserves_jobs_and_is_repeatable(old_database, result):
    before = snapshot_jobs(old_database)
    repository = JobResultRepository(old_database)
    assert snapshot_jobs(old_database) == before
    assert repository.get(1) is None
    saved = repository.save_success(1, result)
    db.init_db(old_database)
    assert JobResultRepository(old_database).get(1) == saved


def test_interrupted_upgrade_rolls_back_and_can_retry(old_database, monkeypatch):
    before = snapshot_jobs(old_database)
    upgrade = db.command.upgrade

    def interrupted(config, revision):
        upgrade(config, revision)
        raise RuntimeError('Interrupted after new migration')

    with monkeypatch.context() as patch:
        patch.setattr(db.command, 'upgrade', interrupted)
        with pytest.raises(RuntimeError, match='Interrupted'):
            db.init_db(old_database)
    with closing(sqlite3.connect(old_database)) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone() == ('0001_initial',)
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='job_results'").fetchone() is None
    assert snapshot_jobs(old_database) == before
    assert JobResultRepository(old_database).get(1) is None


def test_conflicting_table_is_not_adopted_or_overwritten(old_database):
    with closing(sqlite3.connect(old_database)) as connection:
        connection.execute('CREATE TABLE job_results (note TEXT)')
        connection.execute("INSERT INTO job_results VALUES ('Keep me')")
        connection.commit()
    with pytest.raises(OperationalError, match='already exists'):
        db.init_db(old_database)
    with closing(sqlite3.connect(old_database)) as connection:
        assert connection.execute('SELECT * FROM job_results').fetchall() == [('Keep me',)]
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone() == ('0001_initial',)
