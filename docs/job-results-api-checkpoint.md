# Phase 1 follow-up — persisted result read API

Date: 2026-09-08. Status: PASS for this bounded feature; full Phase 1 remains partial.

Added GET /jobs/{job_id}/result using the existing repository and SavedOutcome
schema. No new dependency or database revision. Successful/failed runner outcomes
are readable; absent outcomes remain null, unknown IDs return 404, invalid IDs
return 422, and corrupt stored data returns an explicit Bangla HTTP 500 error.
No provider dispatch, artifact serving or UI change is included.

Files changed: apps/api/main.py, docs/job-results.md.
Files added: tests/test_job_results_api.py, docs/current-build-status.md,
and this checkpoint. Prior uncommitted work was retained; no commit was made.

Validation:

- Baseline backend: 142 passed, two existing TestClient deprecation warnings.
- Final backend: 154 passed in 18.78s, the same two warnings.
- Command: `PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider`.
- Tests used temporary databases outside the sandbox because previous verified
  runs established a sandbox TestClient socket limitation.
- New cases cover actual fixture runner output, seed/metadata serialization,
  reopening the API client, timeout/invalid-fixture/cancelled outcomes,
  queued/running/legacy-completed jobs without outcomes, invalid/unknown IDs,
  malformed JSON/schema, and unchanged job/result rows after reads.
- Frontend production build (including strict TypeScript) and Oxlint passed.
  Frontend source was not changed. Browser regression was not rerun.
- `git diff --check` passed before final documentation; final check follows.

No model download, paid GPU, dependency install or user runtime database access.
GPU time and cost: zero. Python 3.11 and remote CI were not run.

Next bounded feature: queued fixture job API/background dispatch with cancellation
and isolation from demo ticks, followed by web polling/result integration.
