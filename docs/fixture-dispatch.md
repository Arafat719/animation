# Background fixture jobs

The local FastAPI lifespan owns one fixture worker thread and admits at most
16 unfinished calls (running plus queued). Run the API with one process:

```bash
.venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Startup and `/health` still do not open a database. Graceful shutdown signals all
pending calls and drains the queue so the cooperative runner saves cancellation.
Request disconnection alone does not cancel an accepted job.

## HTTP flow

1. Save a project with a nonblank `master_prompt` of at most 4000 characters.
2. POST `/projects/{project_id}/fixture-jobs` with JSON `{}`. HTTP 202 returns the
   committed queued snapshot at progress 0; the worker may advance before the
   response arrives. Unknown projects return 404, invalid IDs/prompts/bodies 422,
   an already active fixture job on that project 409, unavailable/full queues 503.
   Extra body fields are rejected.
3. GET `/jobs/{job_id}` or `/jobs` to poll stored progress without ticking.
4. GET `/jobs/{job_id}/result` for success/error; null means no saved outcome.
5. POST `/jobs/{job_id}/cancel` to persist cancellation and signal the provider's
   local Event. Terminal states are preserved. Queued cancellation skips media.

Configuration is fixed: fixture provider, seed 0, 10-second provider timeout.
The project prompt is validated at submission and read again at runner claim.
Media is the existing shared fixture set, not prompt-specific animation, and
does not honor project target duration. Artifact metadata retains paths/hashes;
the [artifact API](artifact-serving.md) serves verified saved files by job/kind.

## Transactions and lifecycle

Migration `0003_fixture_jobs` adds an ownership table without rewriting old job
rows or results. No historical ownership is guessed. Creation inserts the queued
job and ownership atomically; explicit runner claims also record ownership.
The demo tick UPDATE excludes owned jobs, including when claim races with a tick.
Existing demo job creation/ticking retains its behavior.

Workers wait for insertion to commit. Executor rejection/commit failure rolls
back job and ownership without invoking the provider. Concurrent duplicate-project
checks are serialized in SQLite. This blocks overlapping active jobs, but is not
durable request idempotency: retrying after completion can create another job.
Inspect the job list after an ambiguous POST response.

Provider failures become stored failed outcomes. Unexpected worker storage/state
exceptions are logged with job/project/shot/step context and may leave a
nonterminal job without an outcome. Abrupt process termination and storage errors
do not automatically resume. Inspect logs/database before manual recovery.
Cancel can mark an orphan cancelled but cannot finalize it without a worker.
No leases, automatic startup dispatch, retry or orphan reconciliation are added.

Use one API process for immediate Event cancellation and the stated queue limit.
In multiple processes Events/capacity are local; database cancellation remains
visible on progress/finalization. Shutdown depends on provider cooperation and
SQLite lock waits, not a hard kill timer. Completed outcomes survive reopening.

Web Generate now submits fixture jobs and polls stored progress/results without
calling demo ticks. Queued and running jobs can be cancelled. The UI displays
saved outcomes and retries read failures. The artifact API serves saved samples;
browser image/audio/video preview, download and per-file retry controls are now
available. Media remains fixed fixture output.
No real AI, model download or GPU is used here.
