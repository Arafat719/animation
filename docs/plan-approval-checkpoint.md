# 3.8 — saved mock plan editing and approval

2026-09-19: bounded step PASS.

The project shot list now edits image prompts and offers Save, Approve, Mock
render and Reload saved plan. Edits disable approval/render until saved. Failed
saves retain local edits. Requests are bounded by a timeout and aborted on
unmount. Status and errors distinguish unsaved, draft, approved and mock-complete.
This is local dry-run execution with no generated media or paid provider.

New project-scoped API:
- GET `/projects/{id}/plan`: saved envelope, or revision-zero mock preview.
- PUT `/projects/{id}/plan`: strict `{revision, plan}` saves a validated pending
  StoryPlan, increments revision and clears approval/result.
- POST `/projects/{id}/plan/approve`: approves the supplied current saved revision.
- POST `/projects/{id}/plan/mock-render`: requires that revision's approval before
  invoking MockShotExecutor. Repeated calls reuse the saved result.

`PlanStore` uses SQLite BEGIN IMMEDIATE to serialize save/approve/run operations.
Stale revisions, unsaved approval, executed-plan edits and unapproved runs return
409. Invalid schemas return 422. Read/write response envelopes are exposed in
FastAPI OpenAPI; the 19 existing static v1 schemas remain unchanged.
Migration `0004_plan_approval` adds a separate project_plans table storing the
revision, original plan JSON, approval flag and result JSON. No existing rows or
StoryPlan fields are rewritten. Migration tests cover a 0003 database upgrade,
repeat initialization and legacy API reads; old expected-head tests now use 0004.

Only the plan-specific mock-render path is approval-gated. Existing sample export
and legacy fixture/demo jobs remain separate workflows. Mock execution finishes
inside one transaction; unexpected failure rolls back, not partial-stage resume.
The separate 3.6 checkpoint runner still demonstrates failed-shot recovery.
Real provider concurrency, asynchronous execution, real-media verification and
cross-stage crash recovery are not implemented by this bounded step.

Changed: plan_store.py, migration 0004, API main.py, ShotList.tsx/CSS,
test_plan_approval.py, migration-head assertions in test_db.py,
check_shot_list.mjs, RESUME, ledger and this checkpoint. No unrelated edits removed.

Checks:
- Reused unchanged 3.7 baseline evidence before adding the feature.
- Final 68 targeted tests PASS: `PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_plan_approval.py tests/test_mock_plan_api.py tests/test_db.py tests/test_pipeline_state.py tests/test_mock_shot_runner.py`.
- New tests: revision invalidation, direct backend gate with executor call count,
  repeated run reuse, stale saves/approval, malformed edits, concurrent save winner,
  migration/backward reads. First run had four old-head assertion failures;
  expected revision updated and all passed. Two existing dependency warnings.
- `npm run build` in apps/web PASS, including typecheck.
- `node scripts/check_shot_list.mjs` PASS: prior UI states/mobile plus edited prompt,
  failed-save preservation/retry, approval, reload, mock execution and invalidation.
  Browser uses controlled responses; real server enforcement is covered by API tests.
- Python/Prettier formatting, 19 static schema snapshots, plan excerpt drift and
  git diff whitespace checks PASS. Browser/TestClient ran outside sandbox locally.

No full regression or real model run. No blocker, no commit, no production database
opened. Next authorized task is 3.9 proposal only. Download/run needs explicit
owner approval; 3.10 adapter implementation has not been authorized.
