# Micro-step 1.16 — one-command local startup

Date: 2026-09-14. Step 1.16 PASS; full Phase 1 remains PARTIAL.

`python3 scripts/dev.py` now launches the existing API and Vite together on Linux.
The launcher selects repository `.venv/bin/python` and local Vite, checks both
fixed loopback ports and prerequisites, waits for HTTP readiness, and supervises
both services. Ctrl+C/SIGTERM stops both owned process groups; unexpected service
exit, partial startup or readiness failure also cleans up the sibling. Shutdown
allows five seconds before forcing remaining owned processes to exit.

Implementation:

- `scripts/dev.py` — dependency/settings and port prechecks; direct Uvicorn/Vite
  launch with one API worker and Vite strict port; HTTP readiness; signal handling,
  bounded shutdown, process-group ownership and nonzero failure status.
- `tests/test_dev_launcher.py` — 12 regression cases for occupied/released ports,
  missing dependencies, preflight ordering, normal stop, unrelated process
  preservation, service exit 0/nonzero, second-spawn failure, readiness timeout,
  stop before launch, stubborn-child termination and descendant group signaling.
- Root/web READMEs and `docs/local-development.md` — command, prerequisites,
  fixed addresses, database working-directory behavior, stop and troubleshooting.
- Master plan/current build ledger — completion evidence and next-step position.

Checks performed:

- Full backend suite, Python 3.12.3: **253 passed**, two existing dependency
  deprecation warnings, in 31.72 seconds. Includes the 12 new launcher cases.
- Backend incremental formatter: PASS, 15 checked; the previous 29 legacy
  allowances are unchanged. Frontend formatter: PASS, 6 checked and 14 unchanged
  legacy allowances. `git diff --check`: PASS.
- Actual launcher invoked by absolute path from a disposable directory, without
  virtual-environment activation: API `/health`, web `/`, and transformed
  `/src/main.tsx` returned HTTP 200. The launcher reported ready with deliberately
  unusable HTTP/HTTPS proxy environment values, confirming local probe bypass.
- Real API/Vite integration: web-origin API requests returned the matching CORS
  header. A project created in disposable SQLite remained readable after restart.
  Health/web readiness requests alone did not create that database.
- Real occupied-port checks for **8000 and 5173**: exit 1 with the named port,
  no database creation, and the existing listener preserved. Invalid database
  settings also failed before servers started; both ports remained available.
- Separate actual runs received foreground-group SIGINT and SIGTERM: launcher
  exit 0, both direct child PIDs reaped, both ports immediately reusable.
- An actual run had its API child killed: launcher exit 1, web sibling stopped,
  both child PIDs gone and both ports reusable. Subsequent startup worked.
- CLI `--help` ran without starting services.

Full suite command:

```bash
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
```

Socket/process tests and actual API/Vite smoke used automatically approved local
execution outside the sandbox. The actual smoke driver was temporary and used an
absolute disposable `ANIMATION_DB_PATH`; servers were stopped and temporary data
removed. No user runtime database was opened or migrated. An initial test's
listener fixture needed `SO_REUSEADDR` to test immediate rebind after a connection;
that fixture was corrected before the passing full suite.

No dependencies, application source, user UI edits, models, GPU resources or
formatter debt hashes changed. Frontend lint/typecheck/build were last run in
1.15 and were not repeated for this Python launcher/documentation change. Actual
Vite startup and source transformation were checked here; browser visual/playback
checks, remote CI and Python 3.11 were not run.

Limits: Linux foreground development only, fixed 8000/5173, API restart required
after Python source edits, no daemon/recovery behavior. A hard kill of the launcher
or machine shutdown cannot guarantee cleanup. No commit was made in the existing
dirty worktree. See the [startup guide](local-development.md).

Next: **1.17 — detailed Phase 1 audit and regression gate**. Current authorization
allows continuing this phase without asking again. The persisted/API baseline
contract and matching JSON Schema gaps must be resolved in bounded 1.17a/1.17b
sub-steps as needed; this startup PASS does not complete those contracts or
authorize Phase 2 before its prerequisites and phase approval.
