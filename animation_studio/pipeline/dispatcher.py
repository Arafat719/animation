"""Bounded, process-local dispatch of fixed-config fixture jobs."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Event, Lock
from typing import Callable

from animation_studio.observability import emit_event, failure_code
from animation_studio.pipeline.fake_runner import FakeJobRunner
from animation_studio.providers.fake import FakeRequest


class DispatchUnavailable(RuntimeError):
    pass


class ActiveFixtureJob(RuntimeError):
    pass


class UnknownProject(LookupError):
    pass


class FixtureDispatcher:
    def __init__(self, *, capacity: int = 16,
                 runner_factory: Callable[[str], FakeJobRunner] = FakeJobRunner):
        if capacity < 1:
            raise ValueError('Capacity must be positive')
        self.capacity = capacity
        self.runner_factory = runner_factory
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='fixture-job')
        self._lock = Lock()
        self._active: dict[tuple[str, int], Event] = {}
        self._closed = False

    def create(self, db_path: str, project_id: int) -> dict:
        runner = self.runner_factory(db_path)
        path = runner.store.db_path
        # Serializes queue admission with cancellation/shutdown. SQLite also
        # serializes duplicate-project checks across API processes.
        with self._lock:
            if self._closed or len(self._active) >= self.capacity:
                raise DispatchUnavailable('Fixture queue is unavailable or full')
            with closing(runner.store._connect()) as connection:
                with connection:
                    connection.execute('BEGIN IMMEDIATE')
                    project = connection.execute(
                        'SELECT master_prompt FROM projects WHERE id = ?', (project_id,),
                    ).fetchone()
                    if project is None:
                        raise UnknownProject('Project not found')
                    FakeRequest(prompt=project['master_prompt'])
                    if connection.execute('''
                        SELECT 1 FROM render_jobs j JOIN fixture_jobs f ON f.job_id = j.id
                        WHERE j.project_id = ? AND j.state IN ('queued', 'running', 'waiting_for_gpu')
                    ''', (project_id,)).fetchone():
                        raise ActiveFixtureJob('Project already has an active fixture job')
                    job_id = connection.execute('''
                        INSERT INTO render_jobs (project_id, current_step, state, progress)
                        VALUES (?, 'queued', 'queued', 0)
                    ''', (project_id,)).lastrowid
                    connection.execute('INSERT INTO fixture_jobs (job_id) VALUES (?)', (job_id,))
                    row = dict(connection.execute('SELECT * FROM render_jobs WHERE id = ?', (job_id,)).fetchone())
                    key = (path, job_id)
                    cancel, ready = Event(), Event()
                    self._active[key] = cancel
                    committed = False

                    def execute():
                        ready.wait()
                        try:
                            if committed:
                                runner.run(job_id, cancel=cancel)
                        except Exception as error:
                            # A storage/state failure must not disappear inside a Future.
                            # Provider errors are already persisted by FakeJobRunner.
                            emit_event('job_worker_error', job_id=job_id, project_id=project_id,
                                       shot_id=row['current_shot'], step='dispatch', error_code=failure_code(error))
                        finally:
                            with self._lock:
                                if self._active.get(key) is cancel:
                                    self._active.pop(key, None)

                    try:
                        self._executor.submit(execute)
                        connection.commit()
                        emit_event('job_queued', job_id=job_id, project_id=project_id,
                                   shot_id=row['current_shot'], step='queued', state='queued', progress=0)
                        committed = True
                    except Exception as error:
                        self._active.pop(key, None)
                        emit_event('job_dispatch_error', job_id=job_id, project_id=project_id,
                                   shot_id=row['current_shot'], step='dispatch', error_code=failure_code(error))
                        raise
                    finally:
                        # A rejected submission/failed commit never runs the provider.
                        ready.set()
                    return row

    def cancel(self, db_path: str, job_id: int):
        with self._lock:
            event = self._active.get((str(Path(db_path).absolute()), job_id))
            if event is not None:
                event.set()

    def close(self):
        with self._lock:
            self._closed = True
            for event in self._active.values():
                event.set()
        # Queued calls still run to persist cancellation without invoking media.
        self._executor.shutdown(wait=True)
