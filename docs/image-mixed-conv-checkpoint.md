# 5.4 — Synthetic FP16 storage / F32 convolution comparison

2026-09-30। Owner authorized one bounded synthetic comparison plus tests.
No full model load/inference, weight mutation, package install or download.

## Implementation and validation

Added mixed_conv in scripts/image_operator_probe.py: validate FP16 inputs/weights,
convert locally to F32, run functional conv2d (3x3/padding 1 profile), convert
output back to FP16. No persistent converted-weight cache or parameter mutation.
This is a synthetic helper, not a general Conv2d adapter (no bias/stride/groups
interface yet). Existing image pipeline unchanged.

Explicit --mixed runs two isolated cases, F32 baseline then mixed, with fresh
children/evidence; 20s wall/CPU each including imports, aggregate launch budget
40s, 8 GiB AS, sampled 2 GiB RSS, 2 GiB host reserve, two threads. Stops on first
failure, no retry. Whitelisted operator mode added to existing guarded child.
Per-call time includes conversions and returning FP16 output. Adds process
ru_maxrss high-water growth and explicit input/weight conversion payload size.

116 relevant tests PASS; new coverage verifies mixed-suite fail-stop, unchanged
FP16 input/weight values/storage pointers, output dtype, rejection of F32 input,
and exact equality to explicit F32-conv-to-FP16 reference on small tensors.
Existing numerical/guard/offline/reap suites pass. Ruff lint/format PASS.
All app tests completed before actual benchmark; none overlapped this run.

## Actual mixed-attempt-1 PASS

MemAvailable 12,138,258,432 bytes, fresh output ignored. Command:
`.venv/bin/python -m scripts.image_operator_probe --mixed --output data/image-operator-probe/mixed-attempt-1`

Two cases PASS, child exit 0/reason null; total 4.6914s. Seed 42, identical F32
source inputs/weights, shape (1,320,64,64), 320 output channels, 3x3 kernel.

| Case | First / warm wall seconds | Parent peak sampled RSS bytes |
| --- | --- | ---: |
| F32 | 0.053452 / 0.053632 / 0.054601 | 654712832 |
| FP16 storage, F32 conv | 0.051846 / 0.053321 / 0.052593 | 564568064 |

Mixed output finite; max absolute difference from original F32 reference
0.00255442, relative L2 0.000359475 (~0.036%). Includes FP16 input/weight/output
rounding; not a model quality threshold. Mixed input+weight storage 4,464,640
bytes; explicit F32 input+weight copies 8,929,280 bytes. Output/workspace/allocator
cost is additional. Mixed first-call process peak growth 30,007,296 bytes; its
three-call high-water peak reached 565,657,600 bytes.

Memory measurements are process-wide, not exact per-operation allocation.
Benchmark also retains original F32 inputs/weights for reference, prior output
between calls, and reference/difference buffers later. Parent sampling covers
whole child lifetime and differs from child per-call high-water samples. Do not
interpret lower mixed parent RSS as a memory reduction guarantee. Single small
run, fixed order and only two warm samples: no precise speed advantage claim.
The result establishes this mixed convolution path completed within guards,
unlike the previous pure-FP16 case; it is not full UNet feasibility evidence.

## Next

Next proposed owner-directed micro-step: implement/test an opt-in CPU mixed
Conv2d adapter for the local inference harness, preserving existing FP16 stored
parameters and Conv2d bias/stride/padding/dilation/groups semantics. Verify small
real module equivalence, temporary restoration/cleanup and unsupported-path
rejection; inventory local UNet convolution shapes to bound per-layer conversion
payload. No full model run in that adapter step. Other FP16 operators, full-model
activation/workspace fit, latency and anime image quality remain unproven.

Evidence summary/per-case consistency, doc links, plan drift, whitespace and
RESUME checks PASS. Phase 5.4 incomplete; 5.5 not started. No commit.
