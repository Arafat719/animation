# 5.4 — Bounded load failure diagnostics

2026-09-29। Owner next-work instruction authorized this diagnostic change only.

`scripts/image_load_probe.py` now saves `failed_stage`, `error_message` (maximum
2048 characters), and the last 12 traceback frames (file/function maximum 256
characters each, plus line number). Frame locals and source lines are excluded.
Existing error_type/stage and nonzero failure behavior remain; TypeError joins
the explicit handled exception types. Snapshot checking, runtime configuration
and pipeline validation now have explicit stage markers. Component loader stage
callbacks are preserved. Parent copies child evidence into result.json as before.

No resource-limit/offline/retry changes; no full model run, install or download.
Uncaught exception types, native crashes and hard kills may still have only the
last saved stage. Diagnostics require the child to remain able to write files.
Messages are bounded, not universally secret-redacted; keep runtime evidence
local/ignored. These diagnostics cannot recover attempt-2's discarded details.

Verification: 80 relevant tests PASS (19 probe, 10 streaming, 22 image, 29
workflow); final exception-scope edit initially gave 18 PASS / 1 FAIL, then 19 PASS on
one unchanged rerun. Failure was synthetic-error reporting monitor_error:ValueError
instead of child_failed; a transient RSS/status observation is suspected, not
proven. This intermittent monitor issue remains unresolved. Added
real synthetic subprocess evidence checks, bounded deep traceback/long-message
check, and stubbed component RuntimeError/TypeError cases without SDXL loading.
Ruff lint/format, plan drift, whitespace, document links/RESUME length PASS.

Next proposed step: investigate the intermittent RSS/status monitor failure
with synthetic evidence and a focused regression test, under owner next-work
authorization. Defer attempt-3 until that issue is resolved; no model retry. 5.4 real image remains incomplete;
5.5, inference and paid resources are not authorized by this diagnostic step.
