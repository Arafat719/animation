# Phase 1 follow-up — explicit fixture job runner

Date: 2026-09-08

Added FakeJobRunner and RunnerStore. The synchronous runner claims an existing
queued job, reads its saved project prompt, invokes an injected fixture provider,
persists progress and commits final state plus outcome in one SQLite transaction.
No new schema revision or API/UI wiring was added.

Only queued jobs without outcomes can start. Concurrent starts cannot invoke the
provider twice. A consistent terminal outcome is returned on repeat calls without
regeneration. The provider's completed event does not set job progress to 100;
only successful final result storage does. Final write failures roll back both
state and outcome. Provider timeout/failure and cancellation preserve the last
persisted progress. Database cancellation committed before finalization wins
over an in-flight success. Caller Events interrupt the real fixture provider.

Unexpected provider exceptions/invalid output become visible failed outcomes
using the additive `provider_error` code with exception type/message. Persistence
and state-conflict exceptions propagate rather than being hidden. Existing
provider behavior and existing storage-only repository methods remain unchanged.

Verification:

- Baseline backend suite: 117 passed in 10.28s.
- Focused runner suite: 25 passed in 3.48s.
- Final full backend suite: 142 passed in 23.35s; two existing TestClient
  deprecation warnings. An earlier full-run session result became unavailable;
  the final reported result is from the completed rerun.
- Coverage includes real fixture-provider success, stored prompt/seed, progress,
  no premature 100%, reopening/idempotency, known/unexpected failures, invalid
  output/prompt, real timeout/Event cancellation, database cancellation during
  callbacks and before finalization, already-cancelled jobs, rejected demo/terminal
  jobs, unknown IDs, concurrent claim, final transaction rollback and visible
  progress-storage failure. Other jobs remain unchanged.
- Tests use temporary databases and disabled real pipeline, without Python
  bytecode or pytest cache writes. Full API regression ran outside the sandbox;
  focused runner tests passed inside it.
- git diff --check passed. A temporary hash comparison after implementation
  confirmed the only changed pre-existing file was providers/fake.py, for the
  additive error code. Existing uncommitted work was preserved. Temporary
  snapshots are verification aids, not durable recovery backups.

New files: animation_studio/persistence/runner_store.py,
animation_studio/pipeline/__init__.py, animation_studio/pipeline/fake_runner.py,
tests/test_fake_runner.py, docs/fake-runner.md and this checkpoint.
Existing file changed: animation_studio/providers/fake.py.

Limitations: explicit synchronous invocation only, not a background worker or
web feature. Existing browser demo jobs start as running and are not eligible.
Future API integration must replace/gate browser ticks and connect cancellation
to the runner Event. Database-only cancellation is noticed at progress/final
checks, not immediately while a provider is blocked. The timeout is the provider
budget, not a SQLite lock-wait deadline. Crash/storage-error recovery for a job
left running is not implemented; automatic reruns are rejected. No artifact
serving, copied media or browser preview is added. Details: docs/fake-runner.md.

No dependencies, user database migration, model download, GPU usage or Git commit.
No preview server was intentionally stopped or reconfigured. Frontend/browser
checks, Python 3.11 and remote CI were not rerun. Detailed Phase 1 remains partial.

Next proposed action: define one bounded API integration step with queued job
creation, runner dispatch and read-only progress polling; obtain owner approval.
