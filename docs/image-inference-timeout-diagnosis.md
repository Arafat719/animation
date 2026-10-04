# 5.4 — Inference timeout: read-only diagnosis

2026-09-30। Owner next-work instruction authorized diagnosis of existing
attempt-1. No model execution, retry, package change or source edit performed.

## Established findings

- Saved result reports supervisor `timeout` after 300.8881s, returncode -9,
  sampled peak RSS ~7.557 GiB. It does not report RSS or host-memory termination.
  Sampling does not prove absence of transient memory pressure or paging.
- `scripts/image_inference.py:44` records `denoising` before the entire pipeline
  call. Installed `diffusers/pipelines/stable_diffusion_xl/pipeline_stable_diffusion_xl.py`
  calls `encode_prompt` at line 1081, prepares timesteps/latents, then invokes
  UNet at line 1212 and scheduler.step before the step-end callback. Thus the
  final stage cannot distinguish tokenization, either text encoder, preparation,
  UNet, scheduler or pipeline return. It is not proof that UNet was reached.
- `decoding` is recorded only after pipeline return and the finite-latent check.
  Its absence gives no evidence that VAE decode started; the finite check itself
  also lies within the last recorded stage.
- Parent timing starts before child launch. Import, weight loading, pipeline
  assembly and inference all share 300s. Attempt-5's 64.66s load is a different
  run and cannot be subtracted to obtain attempt-1 inference duration.
- `record()` atomically replaces stage.json; it retains neither stage history
  nor elapsed/CPU timestamps. Child stdout/stderr are discarded. No per-stage
  timings, utilization or stack sample survive in attempt-1.
- Parent checks timeout before its next RSS/exit check. Its finally block kills
  a still-running child and waits; -9 is consistent with that cleanup, but the
  saved evidence does not independently establish the signal sender. Child also
  has 300s CPU and real-time guards. No separate CPU-consumption measurement was
  saved, so CPU-bound computation versus waiting cannot be determined.

## Conclusion and proposed bounded change

The demonstrated failure is exhaustion of the shared wall-time budget, with
insufficient stage evidence to identify the bottleneck. FP16 CPU slowness,
thread contention and paging are possible explanations, not established causes.
Earlier tiny synthetic dtype timings are not an SDXL performance comparison.

Next proposed micro-step: add diagnostic stage timing to the existing harness
and test it using synthetic/stub modules only. Preserve stage.json compatibility
and maintain a small append-only event log with monotonic elapsed and process
CPU times (no tensors or prompt payloads). Mark pipeline entry, each text encoder
forward entry/exit, UNet forward entry/exit, pipeline return/latent validation,
and VAE decode. Temporary PyTorch module hooks must return no replacement values
and be removed in finally. Keep event count bounded and preserve offline mode,
prompt, seed, dtypes, resolution and all resource limits. A step-end callback
alone cannot identify a stall before the first step completes.

Validate stage ordering, timing fields, event bounds, hook cleanup on exceptions,
unchanged outputs and existing parent/timeout behavior. Do not load full weights
or retry inference in that instrumentation step. A later owner-directed bounded
run can use the resulting evidence; no timeout/dtype/thread/resolution change
is justified by current evidence alone.

## Checks and scope

Read saved result/stage, local harness/tests, and installed pipeline source.
Prior 104-test evidence reused; no application test rerun for read-only diagnosis.
Documentation links, plan excerpt drift, whitespace and RESUME length checked.
No requirements changed. Phase 5.4 image acceptance remains incomplete; Phase
5.5 and paid resources remain outside this step.
