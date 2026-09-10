import io
import json
import logging
import sqlite3
import warnings
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
from threading import Barrier, Event

import pytest
from fastapi.testclient import TestClient

from apps.api import main as api
from animation_studio.observability import emit_event, logger, pipeline_logging
from animation_studio.persistence.job_results import JobResultRepository
from animation_studio.pipeline.dispatcher import FixtureDispatcher
from animation_studio.pipeline.fake_runner import FakeJobRunner
from animation_studio.providers.fake import FakeConfig, FakeProvider, FakeRequest, ProgressEvent, ProviderError


SECRET = 'PRIVATE-PROMPT Authorization: Bearer secret-token /private/voice.wav\napi_key=private-key'


@pytest.fixture(scope='module')
def result():
    return FakeProvider(FakeConfig(delay_seconds=0)).generate(FakeRequest(prompt='Fixture'))


@pytest.fixture
def database(tmp_path):
    path = str(tmp_path / 'jobs.db')
    JobResultRepository(path)
    with closing(sqlite3.connect(path)) as connection:
        connection.executemany('INSERT INTO projects (id, title, master_prompt) VALUES (?, ?, ?)',
                               [(1, 'First', SECRET), (2, 'Second', SECRET)])
        connection.executemany('''
            INSERT INTO render_jobs (id, project_id, current_shot, state, progress)
            VALUES (?, ?, ?, 'queued', 0)
        ''', [(1, 1, 7), (2, 2, 8)])
        connection.commit()
    return path


@pytest.fixture
def output():
    stream = io.StringIO()
    with pipeline_logging(stream):
        yield stream
    for private in ['PRIVATE-PROMPT', 'secret-token', '/private/', 'private-key']:
        assert private not in stream.getvalue()


def records(output):
    values = [json.loads(line) for line in output.getvalue().splitlines()]
    for record in values:
        assert set(record) == {
            'event', 'job_id', 'project_id', 'shot_id', 'step', 'state', 'progress',
            'error_code', 'schema_version', 'timestamp', 'level',
        }
        assert record['schema_version'] == 1
        assert datetime.fromisoformat(record['timestamp']).utcoffset().total_seconds() == 0
    return values


def sql(database, query, args=()):
    with closing(sqlite3.connect(database)) as connection:
        with connection:
            return connection.execute(query, args).fetchall()


class Provider:
    def __init__(self, action):
        self.action = action

    def generate(self, request, *, cancel, on_progress):
        return self.action(request, cancel, on_progress)


def test_real_provider_emits_committed_lifecycle_and_reuse(database, output):
    observed = []

    class InspectCommitted(logging.Handler):
        def emit(self, record):
            if record.job_id == 1:
                state, progress = sql(database, 'SELECT state, progress FROM render_jobs WHERE id=1')[0]
                saved = JobResultRepository(database).get(1)
                observed.append((record.event, state, progress, saved is not None))

    handler = InspectCommitted()
    logger.addHandler(handler)
    try:
        runner = FakeJobRunner(database, FakeProvider(FakeConfig(delay_seconds=0)))
        saved = runner.run(1)
        assert runner.run(1) == saved
    finally:
        logger.removeHandler(handler)
    values = records(output)
    assert [row['event'] for row in values] == [
        'job_started', 'job_progress', 'job_progress', 'job_progress', 'job_completed', 'job_reused',
    ]
    assert [row['step'] for row in values] == ['started', 'image', 'audio', 'video', 'completed', 'completed']
    assert [row['progress'] for row in values] == [0, 30, 60, 90, 100, 100]
    assert observed == [
        (row['event'], row['state'], row['progress'], row['event'] in ('job_completed', 'job_reused'))
        for row in values
    ]
    assert all((row['job_id'], row['project_id'], row['shot_id']) == (1, 1, 7) for row in values)
    assert all(row['error_code'] is None for row in values)


def test_progress_logs_committed_max_and_never_provider_completion(database, output, result):
    def action(request, cancel, report):
        report(ProgressEvent(step='image', progress=100))
        report(ProgressEvent(step='audio', progress=5))
        report(ProgressEvent(step='completed', progress=100))
        assert [row['progress'] for row in records(output)] == [0, 99, 99]
        assert sql(database, 'SELECT * FROM job_results') == []
        return result

    saved = FakeJobRunner(database, Provider(action)).run(1)
    assert saved.result is not None
    assert [row['progress'] for row in records(output)] == [0, 99, 99, 100]


@pytest.mark.parametrize('failure', ['fixture_missing', 'timeout', 'cancelled', 'unexpected', 'invalid-result', 'invalid-progress'])
def test_provider_errors_are_codes_only_without_changing_saved_error(database, output, result, failure):
    def action(request, cancel, report):
        assert request.prompt == SECRET
        report(ProgressEvent(step='image', progress=30))
        if failure == 'unexpected':
            raise RuntimeError(SECRET)
        if failure == 'invalid-result':
            return result.model_copy(update={'seed': SECRET})
        if failure == 'invalid-progress':
            report(ProgressEvent.model_construct(step='audio', progress=SECRET))
        raise ProviderError(failure, SECRET)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        saved = FakeJobRunner(database, Provider(action)).run(1)
    assert caught == []
    expected = 'cancelled' if failure == 'cancelled' else 'failed'
    final = records(output)[-1]
    assert final['event'] == f'job_{expected}'
    assert final['state'] == final['step'] == expected
    assert final['error_code'] == saved.error.code
    assert final['level'] == ('INFO' if failure == 'cancelled' else 'ERROR')
    assert final['progress'] == 30
    assert 'PRIVATE-PROMPT' in saved.error.message


def test_invalid_prompt_logs_only_code(database, output):
    sql(database, 'UPDATE projects SET master_prompt=? WHERE id=1', (SECRET * 100,))
    saved = FakeJobRunner(database, Provider(lambda *_: pytest.fail('Invalid prompt must not run'))).run(1)
    assert saved.error.code == 'invalid_input'
    assert records(output)[-1]['error_code'] == 'invalid_input'


@pytest.mark.parametrize('when', ['pre-event', 'pre-database', 'during-event', 'during-database'])
def test_cancellation_has_one_terminal_event_and_no_false_failure(database, output, result, when):
    cancel = Event()
    if when == 'pre-event':
        cancel.set()
    if when == 'pre-database':
        sql(database, "UPDATE render_jobs SET state='cancelled', progress=25 WHERE id=1")

    def action(request, event, report):
        assert when.startswith('during')
        report(ProgressEvent(step='image', progress=30))
        if when == 'during-event':
            event.set()
        else:
            sql(database, "UPDATE render_jobs SET state='cancelled' WHERE id=1")
            report(ProgressEvent(step='audio', progress=60))
        return result

    assert FakeJobRunner(database, Provider(action)).run(1, cancel=cancel).error.code == 'cancelled'
    values = records(output)
    assert sum(row['event'] == 'job_cancelled' for row in values) == 1
    assert all(row['level'] == 'INFO' for row in values)
    assert values[-1]['progress'] == (25 if when == 'pre-database' else 0 if when == 'pre-event' else 30)
    if when == 'pre-database':
        assert len(values) == 1


@pytest.mark.parametrize(('fail_at', 'step', 'expected_state'), [
    (1, 'claim', ('queued', 0)), (2, 'image', ('running', 0)), (3, 'finish', ('running', 30)),
])
def test_commit_failures_log_error_after_rollback_without_false_transition(
        database, output, result, monkeypatch, fail_at, step, expected_state):
    def action(request, cancel, report):
        report(ProgressEvent(step='image', progress=30))
        return result

    runner = FakeJobRunner(database, Provider(action))
    opened = 0

    class BrokenCommit(sqlite3.Connection):
        def __exit__(self, *exception):
            if exception[0] is None:
                self.rollback()
                raise sqlite3.OperationalError(SECRET)
            return super().__exit__(*exception)

    def connect():
        nonlocal opened
        opened += 1
        connection = sqlite3.connect(database, factory=BrokenCommit if opened == fail_at else sqlite3.Connection)
        connection.row_factory = sqlite3.Row
        return connection

    monkeypatch.setattr(runner.store, '_connect', connect)
    with pytest.raises(sqlite3.OperationalError, match='PRIVATE-PROMPT'):
        runner.run(1)
    assert sql(database, 'SELECT state, progress FROM render_jobs WHERE id=1')[0] == expected_state
    assert sql(database, 'SELECT * FROM job_results') == []
    values = records(output)
    assert len(values) == fail_at
    assert values[-1]['event'] == 'job_transition_error'
    assert values[-1]['step'] == step
    assert values[-1]['error_code'] == 'storage_error'
    assert values[-1]['state'] is None
    assert not any(row['event'] in ('job_completed', 'job_failed') for row in values)


def test_two_concurrent_projects_keep_independent_context(database, output, result):
    barrier = Barrier(2)

    def action(request, cancel, report):
        barrier.wait(timeout=5)
        report(ProgressEvent(step='video', progress=90))
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(FakeJobRunner(database, Provider(action)).run, job_id) for job_id in (1, 2)]
        assert all(future.result(timeout=10).result is not None for future in futures)
    for job_id, shot_id in [(1, 7), (2, 8)]:
        values = [row for row in records(output) if row['job_id'] == job_id]
        assert [row['event'] for row in values] == ['job_started', 'job_progress', 'job_completed']
        assert all((row['project_id'], row['shot_id']) == (job_id, shot_id) for row in values)


def test_submission_rejection_logs_no_queued_or_started_job(database, output, monkeypatch):
    dispatcher = FixtureDispatcher()

    def reject(*args, **kwargs):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(dispatcher._executor, 'submit', reject)
    try:
        with pytest.raises(RuntimeError, match='PRIVATE-PROMPT'):
            dispatcher.create(database, 1)
    finally:
        dispatcher.close()
    assert [row['event'] for row in records(output)] == ['job_dispatch_error']
    assert sql(database, 'SELECT id FROM render_jobs ORDER BY id') == [(1,), (2,)]
    assert sql(database, 'SELECT * FROM fixture_jobs') == []


def test_api_shutdown_emits_cancellation_before_restoring_logging(tmp_path, output, monkeypatch):
    path = str(tmp_path / 'api.db')
    monkeypatch.setenv('ANIMATION_DB_PATH', path)
    entered = Event()

    def action(request, cancel, report):
        report(ProgressEvent(step='image', progress=30))
        entered.set()
        assert cancel.wait(5)
        raise ProviderError('cancelled', SECRET)

    monkeypatch.setattr(api, 'FixtureDispatcher', lambda: FixtureDispatcher(
        runner_factory=lambda db: FakeJobRunner(db, Provider(action)),
    ))
    with TestClient(api.app) as client:
        assert client.post('/projects', json={'title': 'Scene', 'master_prompt': SECRET}).status_code == 201
        assert client.post('/projects/1/fixture-jobs', json={}).status_code == 202
        assert entered.wait(5)
    values = records(output)
    assert [row['event'] for row in values] == ['job_queued', 'job_started', 'job_progress', 'job_cancelled']
    assert all((row['job_id'], row['project_id'], row['shot_id']) == (1, 1, None) for row in values)
    assert JobResultRepository(path).get(1).error.code == 'cancelled'


def test_formatter_excludes_raw_messages_exceptions_and_unknown_fields(output):
    try:
        raise RuntimeError(SECRET)
    except RuntimeError:
        logger.exception(SECRET, extra={'prompt': SECRET, 'path': SECRET, 'job_id': SECRET})
    value = records(output)[0]
    assert value['event'] == 'unstructured_log'
    assert value['job_id'] is None
    assert value['step'] == 'unknown'


def test_bad_logging_fields_and_broken_sink_cannot_fail_a_job(database, output, result):
    emit_event('job_started', job_id=SECRET, project_id=1, shot_id=None, step='started')
    assert records(output) == []

    class BrokenSink(logging.Handler):
        def emit(self, record):
            raise RuntimeError(SECRET)

    handler = BrokenSink()
    logger.addHandler(handler)
    try:
        saved = FakeJobRunner(database, Provider(lambda *_: result)).run(1)
    finally:
        logger.removeHandler(handler)
    assert saved.result is not None
    assert sql(database, 'SELECT state, progress FROM render_jobs WHERE id=1') == [('completed', 100)]


def test_configuration_is_nested_repeatable_and_preserves_other_loggers():
    root = logging.getLogger()
    before = (logger.level, logger.propagate, list(logger.handlers), root.level, list(root.handlers))
    for _ in range(2):
        output = io.StringIO()
        with pipeline_logging(output):
            with pipeline_logging(output):
                emit_event('job_queued', job_id=1, project_id=2, shot_id=None, step='queued', state='queued', progress=0)
                assert len(logger.handlers) == len(before[2]) + 1
            assert len(records(output)) == 1
        assert (logger.level, logger.propagate, list(logger.handlers), root.level, list(root.handlers)) == before


def test_default_sink_failure_does_not_dump_a_raw_exception(capsys):
    class BrokenStream:
        def write(self, message):
            raise RuntimeError(SECRET)

    with pipeline_logging(BrokenStream()):
        emit_event('job_started', job_id=1, project_id=1, shot_id=None, step='started')
    assert capsys.readouterr().err == ''


def test_api_cancel_without_worker_is_logged_once_and_terminal_noops_are_quiet(database, output, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', database)
    sql(database, 'INSERT INTO fixture_jobs (job_id) VALUES (1)')
    sql(database, "UPDATE render_jobs SET state='completed', progress=100 WHERE id=2")
    with TestClient(api.app) as client:
        for _ in range(2):
            assert client.post('/jobs/1/cancel').json()['state'] == 'cancelled'
        assert client.post('/jobs/2/cancel').json()['state'] == 'completed'
    values = records(output)
    assert [row['event'] for row in values] == ['job_cancel_requested']
    assert (values[0]['job_id'], values[0]['project_id'], values[0]['shot_id']) == (1, 1, 7)
    assert values[0]['state'] == 'cancelled'
    assert JobResultRepository(database).get(1) is None
