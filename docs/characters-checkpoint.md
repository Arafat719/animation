# Phase 1 follow-up — Characters page

Date: 2026-09-08

Added `#/characters` and a home navigation link. The page saves and lists simple
name/description profiles through new POST/GET `/characters` API endpoints.
Existing SQLite character rows are readable. No schema change was necessary.

Names are trimmed and required (maximum 120 characters); descriptions are
optional (maximum 4000). Extra request fields are rejected. SQL uses bound
parameters. Reference-image paths are not returned by these endpoints.
Duplicate names are permitted; profiles have distinct database IDs.

The UI handles loading, empty lists, pending saves, success, failures and list
retry. Duplicate clicks are blocked within the page. Failed saves retain input
and reload the list without automatically resubmitting an ambiguous request.
Navigation aborts outstanding requests.

Validation:

- Baseline backend suite: 36 passed.
- Final suite: 45 passed in 8.90s, two existing TestClient warnings.
- API coverage includes save/list/reopen, blank/oversized/extra-field rejection,
  optional descriptions, SQL-like text, and existing character rows.
- Strict TypeScript checking, production build, Oxlint, browser-script syntax
  and git diff --check passed.
- Headless Chrome with real isolated FastAPI/SQLite passed Characters navigation,
  loading/empty states, saving, duplicate-click guard, multiline description,
  refresh and actual API restart persistence, list retry and failed save with
  preserved input and no extra database row.
- Previous job/cancel/workspace browser regressions also passed. The helper
  recorded two expected navigation-cancelled interceptions, no browser exceptions.

Limitations: profiles are not yet assigned to projects. No reference uploads,
AI generation, edit/delete or legacy characters.json import was added. Browser
API forwarding does not verify CORS; remote CI was not run.

Files changed: apps/api/main.py, apps/web/src/CharactersPage.tsx, App.tsx,
App.css, apps/web/README.md, tests/test_characters_api.py,
scripts/check_job_progress.mjs and this checkpoint. No dependency install,
user-data migration, model download, GPU usage or Git commit occurred.
Next remaining Phase 1 page: Voices, as a separate approved step.
