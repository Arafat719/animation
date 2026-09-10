# Phase 1 follow-up — Project Workspace

Date: 2026-09-08

Added a read-only project workspace at `#/projects/<id>`, linked from Saved
projects. It loads current project details through the existing get-project
API and shows title, ID, status, duration and the saved multiline prompt.
Loading, missing prompt, missing project, request errors/retry and invalid
routes have explicit states. Hash navigation supports refresh and browser
history without a router dependency or server rewrite configuration.

The workspace reuses JobsPanel with a project filter applied before displaying
or advancing jobs. Only the selected project's running jobs are ticked. Home
retains its existing global demo-job panel. Navigation unmounts the old panel,
cancelling outstanding requests and timers. No backend or schema changes.

Verification:

- Frontend baseline build/lint passed.
- Final strict type-check, production build, Oxlint and git diff --check passed.
- Extended scripts/check_job_progress.mjs passed in headless Chrome against a
  real isolated FastAPI process and disposable SQLite database.
- Existing create/progress/cancel/restart/error-recovery regression checks passed.
- Workspace checks passed: loading, saved details, empty job list, project-only
  advancement with another project unchanged, cancellation, URL reload, error
  and retry, saved-project links, browser Back, missing project and invalid URL.
- The first run hit a test proxy error when navigation cancelled a pending
  interception. The helper now recognizes only Chrome's exact invalid-ID error
  after an observed navigation; all other proxy/browser errors still fail.
  Final run recorded one such cancellation and no uncaught browser errors.

Limitations: details are read-only; no editing, shots or real media artifacts.
The existing jobs endpoint returns all jobs, which this private UI filters;
this is not an authorization boundary. Browser API forwarding does not check
CORS. Backend unit tests were not rerun because backend code did not change;
the browser check exercises the actual API. Remote CI was not run.

Files changed: apps/web/src/App.tsx, ProjectWorkspace.tsx, JobsPanel.tsx,
App.css, apps/web/README.md, scripts/check_job_progress.mjs and this checkpoint.
No dependencies, models, user database migrations, paid GPU resources or Git
commits were introduced. Remaining Phase 1 pages start with Characters.
