# Explicit fixture job runner

`FakeJobRunner` runs one existing, explicitly queued job synchronously. It reads
the saved project's master_prompt, calls an injected fixture-provider interface,
persists progress and commits the final job state and outcome together.

```python
from threading import Event
from animation_studio.observability import pipeline_logging
from animation_studio.pipeline.fake_runner import FakeJobRunner

# The selected database must already contain this queued job and its project.
runner = FakeJobRunner('/absolute/path/to/animation.db')
with pipeline_logging():
    outcome = runner.run(job_id, seed=42, timeout_seconds=10, cancel=Event())
```

The constructor applies existing migrations through RunnerStore. No new schema
revision is needed. `run` executes on the calling thread; it does not create a
background worker, HTTP endpoint or queue manager. The API's fixture dispatcher
runs it off the event loop. Legacy demo jobs start as `running`
and are deliberately not eligible for this queued-job runner.

## State and transaction rules

- Claim uses `BEGIN IMMEDIATE`: only a queued job without a saved outcome becomes
  running, with progress 0. Concurrent callers cannot start its provider twice.
- The prompt is read at claim time. Invalid/missing prompt, seed or timeout saves
  an `invalid_input` outcome and marks the job failed without calling the provider.
- Provider callbacks persist progress below 100. The provider's completed event
  is ignored until the validated result is saved successfully.
- Finalization inserts job_results and updates the job state/current_step in the
  same transaction. Success sets completed/100. Provider errors set failed while
  preserving the last persisted progress; cancellation sets cancelled.
- If either final write fails, both changes roll back. Persistence/state errors
  remain visible to the caller, rather than being converted into successful output
  or a provider error. A progress-write failure similarly propagates.
- Repeating a run on a terminal job with a matching stored outcome returns that
  outcome without another provider call. Terminal jobs lacking outcomes, active
  jobs and inconsistent state/outcome pairs are rejected, not silently repaired.
- Already-cancelled jobs without outcomes acquire a cancellation outcome without
  running the provider. Successful/error outcomes are never overwritten.

## Cancellation, timeouts and failures

A caller-supplied `threading.Event` is passed to the provider, including its delay
and subprocess cancellation checks. The runner also checks for cancellation
before provider invocation and while finalizing. Database cancellation is checked
on progress callbacks and again under the final write lock. A database cancellation
committed before finalization wins over an in-flight successful result.

Database-only cancellation does not signal a provider that is blocked between
callbacks immediately; prompt interruption needs the shared Event. The API
Cancel action now signals that Event as well as updating database state.
If finalization acquires the write lock first, it completes before a later database
cancel, following the existing rule that completed jobs remain completed.

`timeout_seconds` is the provider budget, not a wall-clock limit for SQLite lock
waits or the entire runner. The fixture provider enforces it. Other implementations
of the injected protocol must honor the same contract.

Known `ProviderError` codes/messages are persisted. Unexpected provider exceptions
or invalid output become failed outcomes with the additive `provider_error` code;
the exception type/message is recorded (up to 2000 characters). No provider error
is reported as success. Prompt/progress/result contracts use the current fixture
v1 schemas; this is not a general real-model pipeline yet. These stored errors
remain separate from [structured logs](pipeline-logging.md), which omit raw error
text and provider input/output. Committed state changes, reuse and transaction
failures emit safe context; serializer warnings cannot reveal malformed values.

## Current integration limits

No provider result is copied, served over HTTP or previewed by this runner. It
does not add retries, leases or recovery for an interrupted running job. A process
crash or storage failure can leave a running job without an outcome; re-running
such a job is rejected pending an explicit recovery design. Completed outcomes
remain readable after reopening the database.

Fixture ownership now excludes these jobs from legacy demo ticks. Background
submission/cancellation, read-only polling and sample preview/download are
implemented outside this runner; see [dispatch](fixture-dispatch.md) and the
[current ledger](current-build-status.md).

Focused verification:

```bash
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_fake_runner.py
```
