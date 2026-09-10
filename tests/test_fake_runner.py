import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Event, Timer

import pytest

from animation_studio.persistence.job_results import JobResultRepository, UnknownJobError
from animation_studio.persistence.runner_store import JobNotRunnableError
from animation_studio.pipeline.fake_runner import FakeJobRunner
from animation_studio.providers.fake import FakeConfig, FakeProvider, FakeRequest, ProgressEvent, ProviderError


@pytest.fixture(scope='module')
def result():
    return FakeProvider(FakeConfig(delay_seconds=0)).generate(FakeRequest(prompt='fixture', seed=7))


@pytest.fixture
def path(tmp_path):
    target = str(tmp_path / 'runner.db')
    JobResultRepository(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.execute("INSERT INTO projects (id, title, master_prompt) VALUES (1, 'Scene', 'Quiet rooftop')")
        for job_id in (1, 2):
            connection.execute("INSERT INTO render_jobs (id, project_id, state, progress) VALUES (?, 1, 'queued', 0)", (job_id,))
        connection.commit()
    return target


def sql(path, statement, args=()):
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            return connection.execute(statement, args).fetchall()


def state(path, job_id=1):
    return sql(path, 'SELECT state, progress, current_step FROM render_jobs WHERE id = ?', (job_id,))[0]


class StubProvider:
    def __init__(self, action):
        self.action = action
        self.calls = 0

    def generate(self, request, *, cancel, on_progress):
        self.calls += 1
        return self.action(request, cancel, on_progress)


def test_real_provider_success_persists_and_reopen_does_not_rerun(path):
    runner = FakeJobRunner(path, FakeProvider(FakeConfig(delay_seconds=0)))
    saved = runner.run(1, seed=12)
    assert saved.result.seed == 12
    assert state(path) == ('completed', 100, 'completed')
    assert state(path, 2) == ('queued', 0, None)
    never = StubProvider(lambda *_: pytest.fail('Completed job must not rerun'))
    assert FakeJobRunner(path, never).run(1) == saved
    assert never.calls == 0


def test_saved_prompt_progress_and_no_early_completion(path, result):
    def action(request, cancel, progress):
        assert request.prompt == 'Quiet rooftop'
        assert request.seed == 7
        assert state(path) == ('running', 0, 'started')
        progress(ProgressEvent(step='image', progress=30))
        assert state(path) == ('running', 30, 'image')
        progress(ProgressEvent(step='audio', progress=60))
        progress(ProgressEvent(step='completed', progress=100))
        assert state(path) == ('running', 60, 'audio')
        assert sql(path, 'SELECT * FROM job_results') == []
        return result

    FakeJobRunner(path, StubProvider(action)).run(1, seed=7)
    assert state(path)[0:2] == ('completed', 100)


@pytest.mark.parametrize('code', ['fixture_invalid', 'fixture_missing', 'timeout', 'cancelled'])
def test_provider_failure_stores_matching_terminal_state(path, code):
    def action(request, cancel, progress):
        progress(ProgressEvent(step='image', progress=30))
        raise ProviderError(code, 'Controlled failure')

    saved = FakeJobRunner(path, StubProvider(action)).run(1)
    assert saved.error.code == code
    assert saved.error.message == 'Controlled failure'
    assert state(path)[0:2] == ('cancelled' if code == 'cancelled' else 'failed', 30)
    assert FakeJobRunner(path).run(1) == saved


@pytest.mark.parametrize('invalid_output', [False, True])
def test_unexpected_exception_and_invalid_output_are_visible_failures(path, result, invalid_output):
    def action(*_):
        if invalid_output:
            return result.model_copy(update={'seed': -1})
        raise RuntimeError('Intentional provider crash')

    saved = FakeJobRunner(path, StubProvider(action)).run(1)
    assert saved.error.code == 'provider_error'
    assert ('ValidationError' if invalid_output else 'Intentional provider crash') in saved.error.message
    assert state(path)[0] == 'failed'


@pytest.mark.parametrize('pre_cancelled', [False, True])
def test_event_cancellation_with_real_provider(path, pre_cancelled):
    cancel = Event()
    timer = Timer(0.02, cancel.set)
    if pre_cancelled:
        cancel.set()
    else:
        timer.start()
    try:
        saved = FakeJobRunner(path, FakeProvider(FakeConfig(delay_seconds=0.2))).run(1, cancel=cancel)
    finally:
        if not pre_cancelled:
            timer.join()
    assert saved.error.code == 'cancelled'
    assert state(path)[0] == 'cancelled'


def test_real_timeout(path):
    saved = FakeJobRunner(path, FakeProvider(FakeConfig(delay_seconds=0.1))).run(1, timeout_seconds=0.02)
    assert saved.error.code == 'timeout'
    assert state(path)[0:2] == ('failed', 0)


@pytest.mark.parametrize('during_callback', [True, False])
def test_database_cancel_wins_over_inflight_success(path, result, during_callback):
    def action(request, cancel, progress):
        progress(ProgressEvent(step='image', progress=30))
        sql(path, "UPDATE render_jobs SET state='cancelled' WHERE id=1")
        if during_callback:
            progress(ProgressEvent(step='audio', progress=60))
        return result

    saved = FakeJobRunner(path, StubProvider(action)).run(1)
    assert saved.result is None
    assert saved.error.code == 'cancelled'
    assert state(path)[0:2] == ('cancelled', 30)


def test_already_cancelled_job_does_not_call_provider(path):
    sql(path, "UPDATE render_jobs SET state='cancelled', progress=25 WHERE id=1")
    provider = StubProvider(lambda *_: pytest.fail('Cancelled job must not run'))
    saved = FakeJobRunner(path, provider).run(1)
    assert saved.error.code == 'cancelled'
    assert state(path)[0:2] == ('cancelled', 25)
    assert provider.calls == 0


@pytest.mark.parametrize('prompt', [None, '   ', 'x' * 4001])
def test_invalid_saved_prompt_becomes_failure_without_calling_provider(path, prompt):
    sql(path, 'UPDATE projects SET master_prompt=? WHERE id=1', (prompt,))
    provider = StubProvider(lambda *_: pytest.fail('Invalid prompt must not run'))
    assert FakeJobRunner(path, provider).run(1).error.code == 'invalid_input'
    assert state(path)[0] == 'failed'
    assert provider.calls == 0


@pytest.mark.parametrize('job_state', ['running', 'completed', 'failed'])
def test_existing_demo_or_terminal_without_outcome_is_not_rerun(path, job_state):
    sql(path, 'UPDATE render_jobs SET state=? WHERE id=1', (job_state,))
    provider = StubProvider(lambda *_: pytest.fail('Unclaimed job must not run'))
    with pytest.raises(JobNotRunnableError):
        FakeJobRunner(path, provider).run(1)
    assert state(path)[0] == job_state
    assert provider.calls == 0


def test_unknown_job_is_rejected(path):
    with pytest.raises(UnknownJobError):
        FakeJobRunner(path).run(999)


def test_concurrent_runners_claim_once(path, result):
    entered, release = Event(), Event()

    def action(*_):
        entered.set()
        assert release.wait(5)
        return result

    provider = StubProvider(action)
    first, second = FakeJobRunner(path, provider), FakeJobRunner(path, provider)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(first.run, 1)
        try:
            assert entered.wait(5)
            with pytest.raises(JobNotRunnableError):
                second.run(1)
        finally:
            release.set()
        assert future.result().result == result
    assert provider.calls == 1


@pytest.mark.parametrize('block_insert', [False, True])
def test_final_transaction_rolls_back_on_write_failure(path, result, block_insert):
    trigger = ("BEFORE INSERT ON job_results" if block_insert else
               "BEFORE UPDATE ON render_jobs WHEN NEW.state='completed'")
    sql(path, f"CREATE TRIGGER reject_final {trigger} BEGIN SELECT RAISE(ABORT, 'Final write interrupted'); END")
    with pytest.raises(sqlite3.IntegrityError, match='Final write interrupted'):
        FakeJobRunner(path, StubProvider(lambda *_: result)).run(1)
    assert state(path)[0:2] == ('running', 0)
    assert sql(path, 'SELECT * FROM job_results') == []


def test_progress_storage_failure_is_not_hidden_as_provider_failure(path, result):
    sql(path, "CREATE TRIGGER reject_progress BEFORE UPDATE ON render_jobs WHEN NEW.current_step='image' BEGIN SELECT RAISE(ABORT, 'Progress write interrupted'); END")

    def action(request, cancel, progress):
        progress(ProgressEvent(step='image', progress=30))
        return result

    with pytest.raises(sqlite3.IntegrityError, match='Progress write interrupted'):
        FakeJobRunner(path, StubProvider(action)).run(1)
    assert state(path)[0:2] == ('running', 0)
    assert sql(path, 'SELECT * FROM job_results') == []
