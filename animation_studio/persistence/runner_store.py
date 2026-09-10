"""Transactional job claims, progress and terminal fixture outcomes."""

from contextlib import closing, contextmanager
from threading import Event

from animation_studio.observability import emit_event, failure_code
from animation_studio.persistence.job_results import (
    JobResultConflictError, JobResultRepository, Outcome, SavedOutcome, StoredError,
)
from animation_studio.providers.fake import ProgressEvent, ProviderError


class JobNotRunnableError(RuntimeError):
    pass


def cancelled_outcome() -> Outcome:
    return Outcome(error=StoredError(code='cancelled', message='Job was cancelled'))


def terminal_state(outcome: Outcome) -> str:
    if outcome.result is not None:
        return 'completed'
    return 'cancelled' if outcome.error.code == 'cancelled' else 'failed'


class RunnerStore(JobResultRepository):
    @staticmethod
    def _context(job):
        return {'job_id': job['id'], 'project_id': job['project_id'], 'shot_id': job['current_shot']}

    @contextmanager
    def _transition(self, job_id, step):
        context = {'job_id': job_id, 'project_id': None, 'shot_id': None}
        try:
            with closing(self._connect()) as connection:
                with connection:
                    connection.execute('BEGIN IMMEDIATE')
                    job = self._job(connection, job_id)
                    context = self._context(job)
                    yield connection, job
        except ProviderError:
            # Observing a persisted cancellation is normal control flow; finish
            # records the actual cancelled outcome, not an infrastructure error.
            raise
        except Exception as error:
            code = 'state_error' if isinstance(error, (JobNotRunnableError, JobResultConflictError)) else failure_code(error)
            emit_event('job_transition_error', **context, step=step, error_code=code)
            raise

    def _job(self, connection, job_id):
        self._require_job(connection, job_id)
        return connection.execute('SELECT * FROM render_jobs WHERE id = ?', (job_id,)).fetchone()

    def _write_final(self, connection, job_id: int, outcome: Outcome) -> SavedOutcome:
        if self._read(connection, job_id) is not None:
            raise JobResultConflictError(f'Job {job_id} already has a final outcome')
        state = terminal_state(outcome)
        connection.execute('''
            INSERT INTO job_results (job_id, result_json, error_code, error_message)
            VALUES (?, ?, ?, ?)
        ''', (job_id, outcome.result.model_dump_json() if outcome.result is not None else None,
              outcome.error.code if outcome.error is not None else None,
              outcome.error.message if outcome.error is not None else None))
        connection.execute('''
            UPDATE render_jobs SET state = ?, current_step = ?,
                progress = CASE WHEN ? = 'completed' THEN 100 ELSE progress END,
                updated_at = CURRENT_TIMESTAMP WHERE id = ?
        ''', (state, state, state, job_id))
        saved = self._read(connection, job_id)
        if saved is None:
            raise RuntimeError('Final outcome could not be read')
        return saved

    def claim(self, job_id: int) -> str | None | SavedOutcome:
        job_id = self._validate_id(job_id)
        with self._transition(job_id, 'claim') as (connection, job):
            saved = self._read(connection, job_id)
            if saved is not None:
                if job['state'] != terminal_state(saved):
                    raise JobNotRunnableError('Stored outcome does not match the job state')
                value, event, state, progress = saved, 'job_reused', job['state'], job['progress']
            elif job['state'] == 'cancelled':
                value = self._write_final(connection, job_id, cancelled_outcome())
                event, state, progress = 'job_cancelled', 'cancelled', job['progress']
            elif job['state'] == 'queued':
                connection.execute('INSERT OR IGNORE INTO fixture_jobs (job_id) VALUES (?)', (job_id,))
                project = connection.execute(
                    'SELECT master_prompt FROM projects WHERE id = ?', (job['project_id'],),
                ).fetchone()
                connection.execute('''
                    UPDATE render_jobs SET state = 'running', current_step = 'started',
                        progress = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?
                ''', (job_id,))
                value = project['master_prompt'] if project is not None else None
                event, state, progress = 'job_started', 'running', 0
            else:
                raise JobNotRunnableError('Only queued jobs without outcomes can start')
        emit_event(event, **self._context(job), step='started' if state == 'running' else state,
                   state=state, progress=progress,
                   error_code=value.error.code if isinstance(value, SavedOutcome) and value.error else None)
        return value

    def progress(self, job_id: int, event: ProgressEvent):
        with self._transition(job_id, event.step) as (connection, job):
            if job['state'] == 'cancelled':
                raise ProviderError('cancelled', 'Job was cancelled')
            if job['state'] != 'running':
                raise JobNotRunnableError('Job stopped running during generation')
            # A provider's 100% event is not a committed result yet.
            if event.step == 'completed':
                return
            progress = max(job['progress'], min(event.progress, 99))
            connection.execute('''
                UPDATE render_jobs SET current_step = ?, progress = MAX(progress, ?),
                    updated_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (event.step, min(event.progress, 99), job_id))
        if job['current_step'] != event.step or job['progress'] != progress:
            emit_event('job_progress', **self._context(job), step=event.step,
                       state='running', progress=progress)

    def finish(self, job_id: int, outcome: Outcome, cancel: Event) -> SavedOutcome:
        # Revalidate input even if a caller constructed an unchecked model copy.
        outcome = Outcome.model_validate(outcome.model_dump(warnings=False))
        with self._transition(job_id, 'finish') as (connection, job):
            if job['state'] not in ('running', 'cancelled'):
                raise JobNotRunnableError('Job cannot finalize from its current state')
            if job['state'] == 'cancelled' or cancel.is_set():
                outcome = cancelled_outcome()
            saved = self._write_final(connection, job_id, outcome)
        state = terminal_state(saved)
        emit_event(f'job_{state}', **self._context(job), step=state, state=state,
                   progress=100 if state == 'completed' else job['progress'],
                   error_code=saved.error.code if saved.error else None)
        return saved
