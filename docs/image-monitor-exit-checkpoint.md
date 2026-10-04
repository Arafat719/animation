# 5.4 — RSS monitor exit race fix

2026-09-29। Owner next-work authorization: diagnose/fix the intermittent synthetic
monitor failure only. No model load or inference in this step.

## Evidence and fix

A bounded local probe spawning a Python `pass` child captured, on its first
iteration, `/proc/<pid>/status` with `State: R (running)` and no `VmRSS`.
The old reader raises ValueError for this snapshot, matching the previously
observed monitor_error:ValueError classification. The original failing run did
not retain its status snapshot, so exact attribution of that old run is limited.

`resident_memory` now returns None for missing RSS without a zombie marker.
The supervisor requires confirmed child exit with wait(timeout <= 50ms), also
bounded by the remaining parent deadline. Confirmed exit uses the ordinary
return-code/stage classification; a still-live child raises monitor ValueError
and is killed/reaped. Missing RSS is never counted as a zero-RSS sample on this
path. Existing RSS/zombie/missing-file behavior, resource limits and offline
settings otherwise remain unchanged. No unbounded sampling retry or model retry.

## Checks

Deterministic running-without-RSS regression failed before the fix. Both
confirmed-exit and still-live cases pass after it, including classification,
bounded wait and cleanup. Positive RSS and zombie reads also covered.
84 relevant tests PASS: 23 probe + 10 streaming + 22 image + 29 workflow.
Final test-fixture lint correction rechecked with the two focused cases PASS.
30 additional real synthetic subprocess runs (15 success, 15 injected failure)
all had expected classification/return codes and absent child /proc after reap.
Ruff lint/format, plan drift, whitespace, doc links and RESUME length PASS.

## Limits and next

Sampling still cannot enforce a hard RSS allocation ceiling; missing-RSS grace
is at most 50ms. A child that has not exited within this grace fails closed.
Attempt-2's RuntimeError is still undiagnosed; this monitor fix does not fix it.
Next proposed owner-directed micro-step: fresh memory check and one diagnostic
load-only attempt-3 in a new ignored directory, same limits and no automatic
retry. No model run is authorized by this monitor-only step. Phase 5.4 real image
acceptance remains incomplete; no install/download/paid resource/commit.
