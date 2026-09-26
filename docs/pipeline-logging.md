# Structured pipeline logging — step 1.14

The FastAPI lifespan enables JSON events on stderr for the
`animation_studio.pipeline` logger. Start the API normally; no new configuration,
dependency, log directory or database migration is required. Uvicorn's own server
and access messages retain their existing format.

Each pipeline line has `schema_version: 1`, a UTC ISO timestamp, level, event,
`job_id`, `project_id`, `shot_id`, `step`, `state`, `progress`, and `error_code`.
For example (illustrative):

```json
{"event":"job_progress","job_id":1,"project_id":1,"shot_id":null,"step":"image","state":"running","progress":30,"error_code":null,"schema_version":1,"timestamp":"2026-09-11T00:00:00.000+00:00","level":"INFO"}
```

IDs come from the job row, not provider output. `shot_id` carries the existing
`current_shot` marker; ordinary fixture jobs have no shot and use null. This does
not introduce a full ShotPlan contract. If a storage failure prevents reading the
row, project/shot context is null; the attempted job ID and operation remain.

| Event | Meaning |
| --- | --- |
| `job_queued` | Job/ownership insertion committed; emitted before releasing the worker |
| `job_started` | The runner's queued-to-running claim committed |
| `job_progress` | A changed step/progress committed; progress is the persisted monotonic value, below 100 |
| `job_completed` | Success outcome and completed/100 state committed together |
| `job_failed` | A provider or input failure outcome committed; safe error code only |
| `job_cancel_requested` | The Cancel API committed a state change; this does not promise a saved outcome |
| `job_cancelled` | A cancellation outcome committed, including pre-cancelled or shutdown cases |
| `job_reused` | Runner returned an existing matching outcome without generating again |
| `job_transition_error` | Claim/progress/finalization failed; no successful transition is claimed |
| `job_dispatch_error` | Submission/commit failed; a reserved job ID may have rolled back and need not exist |
| `job_worker_error` | An exception escaped the runner into the background worker boundary |
| `unstructured_log` | An unexpected conventional log was replaced with a fixed safe marker |

Failure/infrastructure events use ERROR; normal progress, reuse and cancellation
use INFO. A transition failure may also produce a worker-boundary event; these
describe two boundaries, not two terminal outcomes. A provider's `completed`
callback is not logged as success before persistence. Repeated terminal Cancel
requests are quiet. An orphan can emit `job_cancel_requested` without ever emitting
`job_cancelled`, because no worker is available to save its outcome.

## Privacy and operational limits

Events use strictly validated, allowlisted identifiers, states, steps and error
codes. They omit prompts, API keys/tokens, request bodies, media paths/hashes,
voice data, arbitrary extras, raw exception messages and tracebacks. The JSON
formatter does not call exception formatting. Malformed provider output/progress
is still validated and rejected; its serialization no longer emits warnings that
would reveal raw field values. A broken default sink does not print a raw logging
exception back to stderr.

Stored provider error messages and result metadata keep their existing API/DB
behavior; this is not redaction of stored outcomes. The logging contract covers
the current pipeline's emitted events/default sink, not all third-party output,
Uvicorn logs, user-added handlers or the legacy renderer. Future adapters and GPU
credentials require their own phase-specific integration and checks.

Events are best-effort diagnostic observations, not a durable audit/outbox or
crash-recovery mechanism. An unavailable sink or malformed diagnostic fields may
drop an event without changing the job outcome. Database commit and logging are
not atomic: a crash between them can lose an event, and concurrent threads can
emit committed observations in a different order. Use the database/result API
as the source of current state. No log rotation or retention service is added.

## Embedded runner use

Imports alone do not configure logging. To get the same JSON output when running
an already queued job directly, wrap the runner in `pipeline_logging`:

```python
from animation_studio.observability import pipeline_logging
from animation_studio.pipeline.fake_runner import FakeJobRunner

with pipeline_logging():
    outcome = FakeJobRunner('/absolute/path/to/animation.db').run(job_id)
```

The API configures this scope automatically and keeps it active until worker
shutdown completes. Nested/concurrent scopes share one default handler; the first
active caller chooses the stream, stderr by default. The last scope removes that
handler and restores the logger's level/propagation. Existing handlers and
root/Uvicorn configuration are preserved. The configuration creates no log files.

Evidence: [logging checkpoint](pipeline-logging-checkpoint.md).
