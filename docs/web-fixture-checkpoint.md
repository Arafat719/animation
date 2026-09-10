# Web fixture integration — 2026-09-09

Completed the next bounded step from current-build-status.md:

- Generate sample posts an empty body to the background fixture endpoint.
- Polling only reads jobs/results; it never calls demo ticks.
- Queued/running jobs disable duplicate submission and support cancellation.
- Saved results show availability and video duration; provider errors and result
  read errors are visible. Failed reads retry without automatic POST retries.
- Starting/cancelling aborts stale polling responses. Project filtering remains.
- UI explains fixed sample media and unavailable preview/download.

Validation: 172 backend tests passed (two existing dependency deprecation
warnings); frontend typecheck, production build and lint passed. Headless Chrome
regression passed against a disposable SQLite database and local API, including
real fixture submission/result persistence across refresh/restart, zero tick
requests, result error/recovery, provider error display, cancellation and existing
workspace/Characters/Voices/Settings flows. Browser cancellation cases use manual
legacy jobs to avoid racing the fast fixture worker; backend fixture cancellation
remains covered by the Python suite. Browser error cases inject HTTP failures.
Initial sandbox runs could not complete local-server checks; verification passed
with approved local execution. No dependency or database schema changes.

Remaining: artifact serving/download and preview, crash recovery, other Phase 1
logging/startup/formatter gaps, and later media/AI phases. Full Phase 1 is partial.
