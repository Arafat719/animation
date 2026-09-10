# Phase 1 follow-up — Voices page

Date: 2026-09-08

Added `#/voices`, home navigation, and POST/GET `/voices` for simple voice
metadata profiles. Uses the existing SQLite voices table without a schema
change. Existing rows, including custom-type metadata, remain readable without
being rewritten. New profiles use the fixed `built_in` type.

Names are required and trimmed (maximum 120 characters). Language and style
are optional free text (maximum 80 and 400); blank values become null. Extra
request fields, including voice_type and reference_audio_path, are rejected.
SQL uses bound values. Duplicate names are allowed with distinct IDs.

The page handles loading, empty lists, pending saves, success, list retry and
save errors. Save failures retain all input and reload the list before retry.
POST requests are not automatically resubmitted; duplicate clicks are blocked
within the page. Navigation aborts outstanding requests.

Verification:

- Immediately preceding backend baseline: 45 passed in 5.99s.
- Frontend baseline production build and Oxlint passed before edits.
- Final backend suite: 59 passed in 7.51s; two existing TestClient deprecation
  warnings. Tests run with DISABLE_REAL_PIPE=1 and PYTHONDONTWRITEBYTECODE=1,
  using temporary data and no pytest cache.
- API tests cover save/list/reopen, trimmed Unicode and multiline values,
  required/maximum-length/type/extra-field validation, optional fields,
  duplicate names, SQL-like text, and unchanged existing rows.
- Strict TypeScript checking, production build, Oxlint, browser-script syntax
  and git diff --check passed.
- Headless Chrome with an isolated real FastAPI/SQLite passed Voices navigation,
  loading/empty states, saving, duplicate-click guard, language/style persistence,
  refresh and actual API restart, list error/retry, failed save preserving all
  inputs without an extra row, and successful manual retry.
- Previous Characters, Workspace, job progress and cancellation browser
  regressions passed. Three expected navigation-cancelled interceptions were
  recorded; no browser exceptions.

The preceding audit's sandbox run stalled at the first API test; running outside
the sandbox passed. Final API and browser checks used that working environment.
Browser forwarding does not verify CORS. Python 3.11 and remote CI were not run.

Limitations: these profiles are metadata for future built-in speech generation,
not installed TTS voices or verified language/model capabilities. No audio
generation/preview, custom sample upload, cloning, edit/delete, or project
assignment. Full detailed Phase 1 remains incomplete.

Changed files: apps/api/main.py, apps/web/src/VoicesPage.tsx, App.tsx, App.css,
apps/web/README.md, tests/test_voices_api.py, scripts/check_job_progress.mjs,
and this checkpoint. Before editing, copies of the five affected existing
files were saved under /tmp/animation-before-voices-3qbhb9gz. Existing worktree
changes were retained. No dependency install, user-data migration, model
download, GPU usage or Git commit occurred.

Next proposed bounded step: the remaining Settings page, with its exact scope
agreed before implementation. No next-step implementation is authorized here.
