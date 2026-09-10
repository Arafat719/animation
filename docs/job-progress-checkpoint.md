# Micro-step 1.9 — fake job progress checkpoint

Date: 2026-09-08

Added `apps/web/src/JobsPanel.tsx`, connected it from App.tsx and added matching
styles in App.css. The panel uses the existing job create, list and tick APIs.
No backend/schema changes or dependency additions were required.

The first job read restores stored progress without advancing it. Subsequent
poll cycles tick only running jobs and display server-returned progress.
Requests are timed out; polling is serialized and cancelled on unmount.
Create requests are guarded against duplicate clicks in the same panel and
are not automatically retried. Errors preserve last-known job information.

Validation:

- Backend baseline: 23 tests passed, two existing deprecation warnings.
- Strict TypeScript check, production build, Oxlint and diff whitespace check passed.
- `node scripts/check_job_progress.mjs` passed in headless Chrome with a real
  isolated FastAPI process and disposable SQLite database.
- Browser checks: loading/empty states, single creation and starting button,
  initial 5% and advancement, refresh without duplicate creation, actual API
  process restart with persisted identity/progress, polling error/recovery,
  100% completion without further ticks, and create error/button recovery.
- No uncaught browser exceptions. Controlled HTTP failures were injected;
  normal job operations were forwarded to the real test API. This forwarding
  does not test the production CORS configuration.

Limitations: demo progress advances only while a browser panel is open;
multiple tabs may advance it faster. This is not a background worker or a
real video render. Cancel UI remains step 1.10. Remote CI was not executed.

Files changed: JobsPanel.tsx, App.tsx, App.css, apps/web/README.md,
scripts/check_job_progress.mjs, and this checkpoint. Existing user changes
were preserved; no commit, model download or paid GPU action occurred.
