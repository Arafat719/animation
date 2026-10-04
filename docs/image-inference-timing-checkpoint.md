# 5.4 — Bounded component timing

2026-09-30। Owner next-work instruction authorized instrumentation and synthetic
tests. No full model loading or inference run in this step.

## Change

`scripts/image_load_probe.py` now records stage.json with additive monotonic
elapsed and process CPU seconds. Existing stage/error payloads and parent
success checks remain compatible. A fresh exclusive events.jsonl retains up to
128 entries, each containing only a stage name (maximum 64 characters) and two
timings; arbitrary stage payloads are excluded. Each append closes the file,
so completed entries survive child termination. Existing evidence is preserved;
overflow fails closed. No fsync/power-loss durability guarantee; an interrupted
write can leave an incomplete last entry. Timing starts after child guards are
installed, before imports/loading, not at parent launch.

`scripts/image_inference.py` marks pipeline entry/return, finite-latent validation
completion and VAE decode entry/return. Temporary forward pre/post hooks mark
both text encoders and UNet. Hooks return None, retain no tensors, and are removed
in finally, including partial registration or forward failure. Failed forwards
leave an entry without a successful exit. VAE decode is marked explicitly because
the pipeline calls decode directly, not VAE.forward.

Resource limits, offline guards, prompt/seed/resolution/steps/guidance/dtypes and
artifact validation are unchanged. The old broad denoising stage is replaced by
specific stages; historical attempt-1 evidence is untouched. Process CPU time
includes process threads and can exceed elapsed time. Top-level events cannot
identify an individual slow operator or distinguish every pipeline preparation
operation; they provide component-level evidence for a future bounded run.

## Verification and next

109 relevant tests PASS: inference, guarded probe, streaming loader, ImageProvider
and workflow suites. New checks cover ordered hook events, tensor identity,
exception/partial-registration cleanup, monotonic timing fields, payload-free
bounded history, existing-log preservation and history surviving timeout/reap.
Existing fixed inference argument/PNG/metadata and memory/offline guards pass.
Ruff lint/format, plan drift, whitespace, documentation links and RESUME checks
PASS. No install/download, paid resources, model mutation or commit.

Next proposed owner-directed micro-step: fresh readiness check followed by one
bounded instrumented inference in a fresh ignored attempt-2 directory, preserving
attempt-1 and all existing limits. Stop/report on failure; no automatic retry or
budget increase. This step does not execute or approve that run. Phase 5.4 real
image acceptance remains incomplete and 5.5 has not started.
