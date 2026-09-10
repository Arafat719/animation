# Phase 1 follow-up — provider outcome persistence

Date: 2026-09-08

Added migration `0002_job_results` and `JobResultRepository`. A job can have one
immutable final result or normalized error, with schema version and creation time.
Validated fixture-provider results retain artifact paths, checksums, durations,
provider/model names and versions, and seed. Identical retries return the stored
record; conflicting writes are rejected. Unknown jobs and invalid input are
rejected. Job states/progress remain untouched by this storage module.

The new migration creates a separate table and preserves old rows. It participates
in the existing transaction and fails on a conflicting existing table. The frozen
`0001_initial.py` and legacy SQL fixture are unchanged. Repository writes enable
foreign keys, use bound parameters and serialize the check/insert transaction.

Verification:

- Baseline: 93 tests passed in 7.71s.
- Focused migration/repository suite: 31 passed in 2.94s.
- Final backend suite: 117 passed in 9.37s, including 24 new cases; two existing
  TestClient deprecation warnings.
- New coverage: success/error reopening, metadata retention, unchanged job rows,
  identical retries, overwrite conflicts, unknown/invalid job IDs, invalid metadata,
  error and branch validation, revalidation of model copies, SQL-like text,
  concurrent retries/conflicts, database constraints, corrupt stored JSON,
  cwd changes, upgrading from 0001, interrupted upgrade rollback/retry and
  preservation of a conflicting existing table.
- Existing legacy migration tests still verify all five original tables' data
  and API reads. Their expected head revision now correctly names 0002.
- Tests used temporary databases, disabled real pipeline, no Python bytecode
  writes and no pytest cache. Full/focused suites ran outside the sandbox because
  the existing API tests have previously stalled inside it.
- git diff --check passed. Hash comparison against
  `/tmp/animation-before-job-results-0jnb7tub/hashes.json` found only the intended
  `tests/test_db.py` edit among 76 pre-existing files. Its original contents were
  copied to that directory; the edit adds the new table/revision expectations.

New files: animation_studio/persistence/migrations/versions/0002_job_results.py,
animation_studio/persistence/job_results.py, tests/test_job_results.py,
docs/job-results.md and this checkpoint. Existing file changed: tests/test_db.py.
Prior uncommitted work was preserved. No dependency install, model download,
GPU use, user database migration or Git commit occurred.

Limitations: metadata storage only, currently validating the fake-provider v1
contract. No file copying/revalidation, worker execution, API result endpoint or
UI preview. Completion/cancellation coordination and retry attempts remain future
integration work. Existing API database initialization will apply the new revision
on next use; follow the documented SQLite backup procedure for valuable data.
Frontend/build/browser checks and remote CI were not rerun; no frontend changes.
Detailed Phase 1 remains partial.

Next proposed action: define one bounded runner integration step, including how
job state and outcome will be committed together; obtain owner approval first.
