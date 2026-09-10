import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Event

import pytest
from fastapi.testclient import TestClient

from apps.api import main as api
from animation_studio.observability import logger
from animation_studio.persistence import db
from animation_studio.pipeline.dispatcher import FixtureDispatcher
from animation_studio.pipeline.fake_runner import FakeJobRunner
from animation_studio.providers.fake import FakeConfig, FakeProvider, ProgressEvent, ProviderError


class ControlledProvider:
    def __init__(self):
        self.started = Event()
        self.release = Event()
        self.cancelled = Event()
        self.calls = 0

    def generate(self, request, *, cancel, on_progress):
        self.calls += 1
        on_progress(ProgressEvent(step='image', progress=30))
        self.started.set()
        deadline = time.monotonic() + 5
        while not self.release.is_set():
            if cancel.wait(0.01):
                self.cancelled.set()
                raise ProviderError('cancelled', 'Stopped by cancellation Event')
            if time.monotonic() >= deadline:
                raise ProviderError('timeout', 'Controlled provider was not released')
        return FakeProvider(FakeConfig(delay_seconds=0)).generate(request, cancel=cancel, on_progress=on_progress)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    path = str(tmp_path / 'dispatch.db')
    monkeypatch.setenv('ANIMATION_DB_PATH', path)
    provider = ControlledProvider()
    monkeypatch.setattr(api, 'FixtureDispatcher', lambda: FixtureDispatcher(
        capacity=2, runner_factory=lambda path: FakeJobRunner(path, provider),
    ))
    with TestClient(api.app) as client:
        for title in ('First', 'Second', 'Third'):
            assert client.post('/projects', json={'title': title, 'master_prompt': 'রাতের শহর'}).status_code == 201
        yield client, provider, path


def create(client, project_id=1):
    response = client.post(f'/projects/{project_id}/fixture-jobs', json={})
    assert response.status_code == 202, response.text
    assert response.json()['state'] == 'queued'
    assert response.json()['progress'] == 0
    return response.json()['id']


def wait_result(client, job_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(f'/jobs/{job_id}/result')
        assert response.status_code == 200
        if response.json() is not None:
            return response.json()
        time.sleep(0.01)
    pytest.fail('Background job did not persist an outcome')


def test_background_progress_without_ticks_and_result_survives_client_reopen(setup):
    client, provider, path = setup
    job_id = create(client)
    assert provider.started.wait(2)
    first = client.get(f'/jobs/{job_id}').json()
    assert first['state'] == 'running'
    assert first['progress'] == 30
    assert client.get('/health').status_code == 200
    assert client.post(f'/jobs/{job_id}/tick').json() == first
    assert client.get(f'/jobs/{job_id}/result').json() is None
    provider.release.set()
    result = wait_result(client, job_id)
    assert result['result']['model_name'] == 'fixture-media'
    assert result['result']['seed'] == 0
    assert result['error'] is None
    completed = client.get(f'/jobs/{job_id}').json()
    assert (completed['state'], completed['progress']) == ('completed', 100)
    assert client.post(f'/jobs/{job_id}/cancel').json() == completed
    reopened = TestClient(api.app)
    assert reopened.get(f'/jobs/{job_id}/result').json() == result
    assert reopened.post(f'/jobs/{job_id}/tick').json() == completed
    assert provider.calls == 1


def test_active_and_queued_cancellation_signal_provider(setup):
    client, provider, _ = setup
    first = create(client)
    assert provider.started.wait(2)
    queued = create(client, 2)
    assert client.get(f'/jobs/{queued}').json()['state'] == 'queued'
    assert client.post(f'/jobs/{queued}/cancel').json()['state'] == 'cancelled'
    stopped = client.post(f'/jobs/{first}/cancel').json()
    assert stopped['state'] == 'cancelled'
    assert stopped['progress'] == 30
    assert provider.cancelled.wait(2)
    for job_id in (first, queued):
        assert wait_result(client, job_id)['error']['code'] == 'cancelled'
        assert client.post(f'/jobs/{job_id}/tick').json()['state'] == 'cancelled'
    assert provider.calls == 1


def test_duplicate_project_and_capacity_rejections_leave_no_extra_jobs(setup):
    client, provider, _ = setup
    create(client)
    assert provider.started.wait(2)
    assert client.post('/projects/1/fixture-jobs', json={}).status_code == 409
    create(client, 2)
    assert client.post('/projects/3/fixture-jobs', json={}).status_code == 503
    assert len(client.get('/jobs').json()) == 2


def test_concurrent_requests_dispatch_only_once(setup):
    client, provider, _ = setup
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post('/projects/1/fixture-jobs', json={}), range(2)))
    assert sorted(response.status_code for response in responses) == [202, 409]
    assert provider.started.wait(2)
    assert provider.calls == 1
    assert len(client.get('/jobs').json()) == 1


@pytest.mark.parametrize('prompt', [None, '', '   ', 'x' * 4001])
def test_invalid_saved_prompt_rejected_before_job_creation(setup, prompt):
    client, provider, _ = setup
    project_id = client.post('/projects', json={'title': 'Invalid', 'master_prompt': prompt}).json()['id']
    assert client.post(f'/projects/{project_id}/fixture-jobs', json={}).status_code == 422
    assert client.get('/jobs').json() == []
    assert provider.calls == 0


def test_invalid_request_and_unknown_project(setup):
    client, provider, _ = setup
    assert client.post('/projects/999/fixture-jobs', json={}).status_code == 404
    assert client.post('/projects/0/fixture-jobs', json={}).status_code == 422
    assert client.post('/projects/1/fixture-jobs', json={'current_step': 'completed'}).status_code == 422
    assert client.get('/jobs/999').status_code == 404
    assert client.get('/jobs/0').status_code == 422
    assert client.get('/jobs').json() == []
    assert provider.calls == 0


def test_legacy_demo_still_ticks_while_fixture_job_is_running(setup):
    client, provider, _ = setup
    fixture = create(client)
    assert provider.started.wait(2)
    demo = client.post('/projects/2/jobs', json={'current_step': 'demo'}).json()['id']
    assert client.post(f'/jobs/{demo}/tick').json()['progress'] == 20
    assert client.post(f'/jobs/{fixture}/tick').json()['progress'] == 30


def test_shutdown_cancels_running_and_queued_and_drains_worker(setup):
    client, provider, path = setup
    first = create(client)
    assert provider.started.wait(2)
    second = create(client, 2)
    api.app.state.fixture_dispatcher.close()
    assert provider.cancelled.is_set()
    assert provider.calls == 1
    for job_id in (first, second):
        assert wait_result(client, job_id)['error']['code'] == 'cancelled'
    assert client.post('/projects/3/fixture-jobs', json={}).status_code == 503


def test_provider_failure_becomes_visible_failed_job(setup, monkeypatch):
    client, provider, _ = setup

    def fail(*args, **kwargs):
        raise ProviderError('fixture_missing', 'Fixture unavailable')

    monkeypatch.setattr(provider, 'generate', fail)
    job_id = create(client)
    assert wait_result(client, job_id)['error']['code'] == 'fixture_missing'
    assert client.get(f'/jobs/{job_id}').json()['state'] == 'failed'


def test_submission_failure_rolls_back_job_and_ownership(setup, monkeypatch):
    client, provider, path = setup
    dispatcher = api.app.state.fixture_dispatcher

    def reject(*args, **kwargs):
        raise RuntimeError('Executor rejected submission')

    monkeypatch.setattr(dispatcher._executor, 'submit', reject)
    with pytest.raises(RuntimeError, match='Executor rejected'):
        client.post('/projects/1/fixture-jobs', json={})
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute('SELECT * FROM fixture_jobs').fetchall() == []
        assert connection.execute('SELECT * FROM render_jobs').fetchall() == []
    assert provider.calls == 0
    assert dispatcher._active == {}


def test_commit_failure_does_not_run_provider_or_leave_job(setup, monkeypatch):
    client, provider, path = setup
    dispatcher = api.app.state.fixture_dispatcher
    runner = FakeJobRunner(path, provider)

    class FailedCommit(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError('Simulated commit failure')

    def connect():
        connection = sqlite3.connect(path, factory=FailedCommit)
        connection.row_factory = sqlite3.Row
        return connection

    monkeypatch.setattr(runner.store, '_connect', connect)
    monkeypatch.setattr(dispatcher, 'runner_factory', lambda _: runner)
    with pytest.raises(sqlite3.OperationalError, match='Simulated commit failure'):
        client.post('/projects/1/fixture-jobs', json={})
    dispatcher.close()
    assert provider.calls == 0
    assert dispatcher._active == {}
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute('SELECT * FROM render_jobs').fetchall() == []
        assert connection.execute('SELECT * FROM fixture_jobs').fetchall() == []


def test_worker_storage_failure_is_logged_with_job_context(setup, monkeypatch, caplog):
    client, provider, _ = setup
    dispatcher = api.app.state.fixture_dispatcher
    factory = dispatcher.runner_factory

    def failing_runner(path):
        runner = factory(path)

        def fail(*args, **kwargs):
            raise sqlite3.OperationalError('Simulated storage failure')

        monkeypatch.setattr(runner, 'run', fail)
        return runner

    monkeypatch.setattr(dispatcher, 'runner_factory', failing_runner)
    logger.addHandler(caplog.handler)
    try:
        job_id = create(client)
        dispatcher.close()
    finally:
        logger.removeHandler(caplog.handler)
    record = next(record for record in caplog.records if record.event == 'job_worker_error')
    assert record.job_id == job_id
    assert record.project_id == 1
    assert record.step == 'dispatch'
    assert record.shot_id is None
    assert record.error_code == 'storage_error'
    assert record.exc_info is None
    assert 'Simulated storage failure' not in caplog.text
    assert client.get(f'/jobs/{job_id}/result').json() is None
    assert provider.calls == 0


def test_lifespan_shutdown_and_reopen_preserves_cancelled_job(tmp_path, monkeypatch):
    path = str(tmp_path / 'lifecycle.db')
    monkeypatch.setenv('ANIMATION_DB_PATH', path)
    provider = ControlledProvider()
    monkeypatch.setattr(api, 'FixtureDispatcher', lambda: FixtureDispatcher(
        runner_factory=lambda path: FakeJobRunner(path, provider),
    ))
    with TestClient(api.app) as client:
        client.post('/projects', json={'title': 'Lifecycle', 'master_prompt': 'Scene'})
        job_id = create(client)
        assert provider.started.wait(2)
    assert provider.cancelled.is_set()
    with TestClient(api.app) as reopened:
        assert reopened.get(f'/jobs/{job_id}').json()['state'] == 'cancelled'
        result = reopened.get(f'/jobs/{job_id}/result').json()
        assert result['error']['code'] == 'cancelled'
        assert reopened.post(f'/jobs/{job_id}/tick').json()['state'] == 'cancelled'
    assert provider.calls == 1


def test_migration_from_0002_preserves_rows_and_reads_demo(tmp_path, monkeypatch):
    path = str(tmp_path / 'old.db')
    upgrade = db.command.upgrade
    with monkeypatch.context() as patch:
        patch.setattr(db.command, 'upgrade', lambda config, _: upgrade(config, '0002_job_results'))
        db.init_db(path)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("INSERT INTO projects (id, title) VALUES (1, 'Keep')")
        connection.execute("INSERT INTO render_jobs (id, project_id, state, progress) VALUES (1, 1, 'running', 35)")
        connection.commit()
        before = connection.execute('SELECT * FROM render_jobs').fetchall()
    db.init_db(path)
    db.init_db(path)
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute('SELECT * FROM render_jobs').fetchall() == before
        assert connection.execute('SELECT * FROM fixture_jobs').fetchall() == []
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone() == ('0003_fixture_jobs',)
    monkeypatch.setenv('ANIMATION_DB_PATH', path)
    with TestClient(api.app) as client:
        assert client.get('/jobs/1').json()['progress'] == 35
        assert client.post('/jobs/1/tick').json()['progress'] == 50


def test_interrupted_0003_upgrade_rolls_back_ownership_and_revision(tmp_path, monkeypatch):
    path = str(tmp_path / 'interrupted.db')
    upgrade = db.command.upgrade
    with monkeypatch.context() as patch:
        patch.setattr(db.command, 'upgrade', lambda config, _: upgrade(config, '0002_job_results'))
        db.init_db(path)

    def interrupt(config, revision):
        upgrade(config, revision)
        raise RuntimeError('Interrupted migration')

    with monkeypatch.context() as patch:
        patch.setattr(db.command, 'upgrade', interrupt)
        with pytest.raises(RuntimeError, match='Interrupted migration'):
            db.init_db(path)
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone() == ('0002_job_results',)
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='fixture_jobs'").fetchone() is None
    db.init_db(path)
