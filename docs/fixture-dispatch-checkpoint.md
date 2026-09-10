# Phase 1 follow-up — background fixture dispatch

Date: 2026-09-08. Feature: PASS. Full Phase 1: PARTIAL.

Added queued fixture-job creation, bounded background dispatch, read-only job
detail polling, cancellation Event routing and graceful shutdown/draining.
Migration 0003 records ownership so demo ticks cannot advance runner jobs.

Validation:

- Baseline: 154 backend tests passed in 15.27s.
- Initial focused API/runner/migration/demo checks: 52 passed in 9.05s.
- Final full backend: 172 passed in 21.10s; two existing TestClient warnings.
- Command: `PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider`.
- Tests used temporary databases outside the sandbox due to the established
  TestClient socket limitation. No user runtime database was opened.
- Coverage: real fixture success, async progress, provider failure, running/queued
  cancellation, concurrent duplicate requests, capacity, invalid prompts/bodies,
  demo isolation, submission/commit rollback, logged storage failures, lifespan
  shutdown/reopen, 0002 upgrade/backward reads and interrupted migration rollback.
- git diff --check passed before documentation; final check follows.
- Frontend source did not change; browser/build checks, Python 3.11 and remote CI
  were not rerun in this backend step.

Implementation: apps/api/main.py, animation_studio/pipeline/dispatcher.py,
animation_studio/persistence/runner_store.py and migrations/versions/0003_fixture_jobs.py.
Tests: tests/test_fixture_dispatch_api.py; tests/test_db.py (expected head only).
Docs: fixture-dispatch.md, this checkpoint, current-build-status.md,
fake-runner.md, job-results.md and migrations.md.

Limits: single-process queue, fixed fixture config, no automatic crash/storage
recovery, durable request idempotency, browser integration or media serving.
Prior uncommitted work retained; no installs, model downloads, GPU time/cost or
Git commit. Next feature: web generation and read-only polling integration.
