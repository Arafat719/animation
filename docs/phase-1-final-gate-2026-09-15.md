# Phase 1 final gate — 2026-09-15

**1.17 / local Phase 1: PASS.** This closes the Phase 1 baseline and fake-generation
acceptance gate, not the full V1 product. Phase 2 implementation has not started
in this gate review. Next: Phase 2 existing composer acceptance gaps (2.2/2.4/2.5)
before 2.6 onward, subject to the master's phase authorization rule.

## Requirement audit

| Section 7 requirement | Evidence / outcome |
| --- | --- |
| Repository skeleton/documentation | Existing apps, domain/persistence/provider/pipeline modules, scripts, tests and guides; PASS |
| Health and typed environment settings | API /health, settings models/tests; actual startup health/CORS PASS |
| SQLite migrations and five entity baselines | Actual 0001/0002/0003 revisions, independent legacy fixtures and preservation tests; Project/Character/Voice/Shot/RenderJob v1 records; PASS |
| Required web pages | Projects, New Project, Workspace, Characters, Voices, Settings; browser regression PASS |
| Fake image/silent audio/sample clips | Provider/runner/result/artifact coverage plus actual browser decoding/downloads; PASS |
| Polling and cancellation | Fixture dispatch tests, browser progress/refresh/cancellation; PASS |
| Structured job/project/shot/step logging | Existing lifecycle/context/redaction/rollback/concurrency tests in passing suite; PASS |
| Tests, formatters, one-command startup | Local backend/frontend gates, actual launcher and existing 12 launcher cases; PASS |
| Contract/schema follow-ups 1.17a–f | 17 published schemas; SQL NULL compatibility fixed without rewriting data; PASS |

## Acceptance evidence

1. Prompt creates a fake job: latest browser regression submits a real local
   fixture request, polls progress and reads a saved result.
2. UI progress survives refresh: browser regression PASS, including cancellation
   and job results after reload; no browser exceptions.
3. API restart preserves projects/jobs: latest browser run checks restart; today's
   actual two-service launcher check additionally verifies saved Project equality.
4. Cancellation works: queued/running dispatcher Python coverage and browser
   cancellation/retry/persistence PASS. NULL-progress running jobs also cancel.
5. Automated tests: **339 backend tests PASS**, three existing dependency warnings
   (32.72 seconds), plus frontend lint/typecheck/build and both incremental formatters.
6. Gate verification uses `DISABLE_REAL_PIPE=1`, fixed local fixtures and disposable
   data; no real inference or paid GPU used for this gate.

## Evidence dates and reuse

The immediately preceding [1.17f checkpoint](null-compatibility-checkpoint.md)
contains the full backend and browser runs for the current application code.
No application code changed in this final audit, so those checks were not repeated.
Browser coverage includes actual media playback, byte-exact downloads, error/retry,
mobile layout, refresh/restart, cancellation and new NULL UI cases. Session-local
browser evidence: `/tmp/animation-jobs-ZRfzZh` and `/tmp/check_null_compatibility.mjs`.

New checks in this final gate:

- Actual `scripts/dev.py` invocation from a disposable directory, fresh absolute
  ANIMATION_DB_PATH; API/web readiness does not create the database.
- All **17 schemas** fetched over Vite HTTP and compared as JSON to published files.
- Real API request with web Origin returns matching CORS header.
- Create Project, SIGTERM shutdown, restart and verify exact Project response.
- SIGINT shutdown; ports 8000/5173 reusable after both shutdowns.
- `pip check`, schema drift and both incremental formatter checks PASS.
- Temporary launcher driver `/tmp/phase1_startup_check.py`; services stopped and
  disposable database removed in cleanup.

Actual port conflicts, API crash/sibling cleanup and restart behavior also have
[1.16 evidence](startup-checkpoint.md) and regression coverage in the 339-test suite.

## Limits retained

- Local Linux/Python 3.12 gate; Python 3.11 and remote CI execution not claimed.
- Incremental formatting permits 28 unchanged Python and 11 frontend/helper legacy
  files. Strict whole-repository formatting remains debt, not a full-format PASS.
- The previously reported empty Git object limits Git diff review; no Git repair,
  commit or remote publication performed. Existing dirty worktree preserved.
- Workspace is read-only; character/voice metadata is not project assignment,
  consented cloning, a planning contract or synthesis.
- Fixture output is fixed media, not prompt-specific animation. Saved rows/results
  survive restart; orphan work is not automatically recovered/resumed.
- Future StoryPlan, full planning ShotPlan, profile/provider/cost/retry contracts
  and actual 30–60 second AI output remain in their mapped feature phases.

These explicit scope limits match the Phase 1 baseline defined in Section 5 and
the ledger; none is silently claimed as completed V1 behavior.
