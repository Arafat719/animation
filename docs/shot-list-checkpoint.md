# 3.7 — read-only mock shot list

2026-09-19: bounded step PASS.

ProjectWorkspace now mounts ShotList. It fetches the saved project's deterministic
mock preview and displays ordered shot numbers, per-shot duration, image prompt,
shot count and total duration. The preview is explicitly labelled mock/read-only.
Loading, no-prompt empty, success, network/HTTP/invalid-response error and retry
states are provided. Requests have a ten-second timeout and abort on navigation;
project-keyed mounting prevents carrying the previous project's preview forward.
Prompt text is rendered as React text, wraps on mobile and preserves line breaks.

`GET /projects/{project_id}/mock-plan` uses the existing MockPlanner/StoryPlan
contract. Missing projects return 404; absent/blank prompts return JSON null;
unset duration defaults to 30 seconds; invalid planner inputs return 422.
It creates no jobs and changes no database rows. No new schema or migration.
This is a stateless preview, not the saved execution checkpoint from 3.6.
Character selection, plan persistence/editing/approval and rendering are deferred.

Files: `apps/api/main.py`, `apps/web/src/ProjectWorkspace.tsx`, new
`apps/web/src/ShotList.tsx`, `ShotList.css`, `tests/test_mock_plan_api.py` and
`scripts/check_shot_list.mjs`, plus RESUME/ledger/checkpoint documentation.

Validation:
- Reused recent unchanged planner/schema baseline evidence from 3.6.
- 53 targeted tests PASS: `PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_mock_plan_api.py tests/test_projects_api.py tests/test_mock_planner.py tests/test_story_plan.py`.
- Includes seven new API cases: 30/45/60s deterministic previews, unchanged database
  dump, missing project, empty prompt, legacy null duration and invalid inputs.
- `npm run build` in apps/web PASS (includes typecheck).
- `node scripts/check_shot_list.mjs` PASS with local Chromium and controlled API
  responses using a real MockPlanner fixture: loading, empty, success, HTTP error,
  malformed response, retry, ordered numbers/durations/Unicode prompts, 390px
  layout without panel overflow, zero render requests. Browser test does not
  replace the separate real API tests.
- Scoped oxlint: no errors; one `react(set-state-in-effect)` warning for request-state reset, following the existing workspace fetch pattern.
- Python formatting, frontend Prettier, 19 schema snapshots and plan excerpt
  drift checks PASS. Two existing TestClient dependency deprecation warnings.
- Sandbox TestClient stalled and browser spawn hit EPERM; verification passed
  outside the sandbox using a disposable database/browser profile. Stalled test
  process was stopped. No production database or paid services used.

No full regression; no blocker; existing dirty edits preserved, no commit.
Next authorized micro-step: 3.8 mock plan edit/approve flow.
