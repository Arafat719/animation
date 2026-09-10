# Phase 1 verification — micro-step 1.11

Date: 2026-09-08

**Micro-step 1.11 test gate: PASS. Full detailed Phase 1 scope: PARTIAL.**

The implemented project/job slice passes its checks. This does not mark all
Section 7 Phase 1 tasks complete or authorize moving to Phase 2.

## Current verification

Environment: Linux, Python 3.12.3, Node 22.22.3, npm 10.9.8.

| Check | Result |
| --- | --- |
| `DISABLE_REAL_PIPE=1 python -m pytest -q -p no:cacheprovider` | 25 passed in 4.63s; two existing TestClient deprecation warnings |
| `python -m pip check` | No broken requirements |
| `npm run build` in apps/web | Strict TypeScript check and production build passed |
| `npm run lint` in apps/web | Passed |
| `node scripts/check_job_progress.mjs` | Full browser regression passed after correcting test synchronization |
| API CORS smoke check | localhost and 127.0.0.1 port 5173: health and POST preflight passed; unrelated origin rejected |
| `git diff --check` | Passed |
| Frontend generated-file ignores | apps/web/.gitignore excludes node_modules and dist |

Browser verification uses Chrome, a real local FastAPI process and disposable
SQLite data. API requests are forwarded to the isolated process; controlled
HTTP failures are injected for error states. CORS was checked separately through
TestClient, not an unmodified browser-to-default-port connection.

Verified flows: project creation; jobs loading/empty state; single job creation;
5% initial progress and advancement; browser refresh; actual API process restart;
polling error/recovery; completion; failed cancellation/retry; duplicate-click
protection; persisted cancellation with no further ticks; another job continuing.

The first browser run timed out in the cancellation-error scenario. Its script
waited only for the Cancel button to exist, while creation temporarily disables
that button pending a jobs refresh. The script now waits for an enabled button.
The complete rerun passed; no product code changed in this verification step.

## Phase 1 requirements audit

| Requirement | Evidence / remaining work |
| --- | --- |
| Repository skeleton and documentation | Present; existing user changes remain uncommitted |
| Health API and typed environment settings | Health passes; centralized typed settings are missing |
| SQLite migrations | Initial migration, legacy-data preservation and rollback tests pass; schemas are minimal, not complete canonical profiles |
| Projects and New Project UI | Implemented together on the existing page |
| Project Workspace, Characters, Voices, Settings pages | Missing |
| Fake provider returning images, silent audio and sample clips | Missing; fixture files exist, but jobs only simulate stored progress |
| Polling and refresh-safe progress | Pass; browser-driven ticks, not a background worker |
| Cancellation and restart persistence | Pass |
| Prompt creates a fake job | Assisted two-action flow exists (save project, start demo); the optional prompt is stored but does not drive provider artifacts |
| Structured logging with job/project/shot/step context | Missing in the new backend |
| Unit/API tests | Pass |
| Formatters | No project formatter configured; Oxlint is a linter |
| One-command local startup | Missing; frontend/backend are started separately |
| No real AI or paid GPU during checks | Satisfied |

## Next bounded work

First close the typed-settings gap in the existing health/backend requirement:
centralize environment settings and use one consistent database-path default.
The API currently derives its default from the working directory while the
persistence module derives it from the repository path. Add validation and
focused tests without changing the database schema or adding other features.
Ask the owner before beginning that implementation step.

Other Phase 1 gaps should be handled separately before claiming the detailed
phase complete. Python 3.11, remote GitHub CI and a fresh install were not rerun
in this gate; earlier clean Python 3.12 setup is recorded in prior checkpoints.

Changed files in this step: scripts/check_job_progress.mjs (one wait condition)
and this report. User runtime databases were not modified. No installs, model
downloads, GPU charges or commits were performed.
