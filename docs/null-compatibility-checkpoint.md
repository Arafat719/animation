# NULL compatibility checkpoint — 1.17f

Date: 2026-09-15. **1.17f complete; full Phase 1 gate remains PARTIAL.**
Next bounded task: complete the full 1.17 audit/regression gate.

## Behavior

Legacy SQL NULL Project status and RenderJob state/progress now return JSON null
with HTTP 200 in list/detail reads. Response types and generated schemas widen
these three fields; create-request validation and omitted-field defaults stay
unchanged. No database values are rewritten or migrations introduced.

Frontend types accept null and display `Unknown` / `Progress unknown`. The native
progress element has no numeric value for unknown progress. A null job state is
not treated as queued/running and does not invent a cancellable active job.
Actual running jobs with null progress still cancel correctly while retaining
unknown progress. Tick/cancel behavior for other existing states is preserved.

## Verification

- **339 backend tests PASS**, three existing dependency warnings, 32.72 seconds.
- Converted three old expected-500 contract cases to successful NULL round trips;
  four additional cases cover tick/cancel/reopen combinations and persisted values.
- Full command: `DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -o faulthandler_timeout=30`.
- Frontend lint/typecheck/build, both incremental formatters and 17-schema drift
  check PASS. Three edited TSX files were formatted and their old exact-content
  exemptions removed; remaining frontend formatting debt is 11 files.
- Existing browser regression ran with a temporary extension that inserted one
  Project and RenderJob with NULL fields into its disposable SQLite database.
  Home/job display and Project workspace showed unknown values; the progress
  element had no numeric value. No browser exceptions.
- Browser regression also passed preview playback, byte-exact downloads, retry,
  cancellation, refresh/restart, workspace, metadata pages and settings checks.
  Evidence directory: `/tmp/animation-jobs-ZRfzZh`; temporary runner:
  `/tmp/check_null_compatibility.mjs` (session-local evidence).

Checks used approved sandbox escalation for existing TestClient/local browser
limitations. No user runtime database was opened. OpenAPI intentionally changes
only nullable response field definitions; the previous extraction's claim of
unchanged OpenAPI does not apply to this compatibility fix.

This is not a claim that all Phase 1 acceptance requirements have been re-audited.
Final schema publication/startup/phase reconciliation checks still belong to 1.17.
Automatic job recovery and real AI generation remain later features.
