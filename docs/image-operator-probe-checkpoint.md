# 5.4 — Guarded synthetic operator probe

2026-09-30। Owner authorized harness/tests and one bounded synthetic suite.
No model weights loaded, real image inference, install or download.

## Implementation/checks

New scripts/image_operator_probe.py uses existing run_probe guards through six
explicit operator modes. Each child has 20s wall/CPU including import, 8 GiB AS,
sampled 2 GiB RSS and 2 GiB host reserve; aggregate launch budget 120s. Cleanup
can add small elapsed overhead. Suite stops on first failed case, never retries,
creates fresh evidence directories and persists summary plus partial stage logs.
Existing offline audit hook and kill/wait behavior apply. Model modes unchanged.

Seed 42 generates identical F32 source inputs/weights per operator; convert to
selected dtype. Conv shape (1,320,64,64), 320 output channels, 3x3/padding 1;
linear (1,256,1280) to 1280. Two intra-op/one inter-op threads, inference_mode,
three calls (first plus two warm), then F32 reference. Records wall/process CPU
per call, finite checks, max absolute/relative L2 error. Conv order F32/FP16/BF16;
linear rotates to FP16/BF16/F32. No claim this eliminates ordering bias.

114 relevant tests PASS (33 operator/probe + 81 inference/stream/provider/workflow).
Tests cover suite bounds/order/fail-stop/deadline/existing-output preservation,
small actual numerical conv/linear, and existing subprocess offline/memory/
timeout/reap behavior. Ruff lint/format, plan drift, whitespace and doc checks
PASS. Initial Ruff import-style finding fixed before benchmark.

## Actual attempt-1

Fresh MemAvailable 12,178,472,960 bytes, output absent/git-ignored. Command:
`.venv/bin/python -m scripts.image_operator_probe --output data/image-operator-probe/attempt-1`

Suite FAIL, 22.4151s total; stopped after two cases:

| Case | Result | First / warm wall seconds | Peak sampled RSS bytes |
| --- | --- | --- | ---: |
| conv F32 | PASS | 0.117707 / 0.047052 / 0.046803 | 562651136 |
| conv FP16 | SIGXCPU (-24), first call unfinished | no completed sample | 553127936 |

FP16 child entered first convolution at child elapsed 1.5628s/process CPU
1.6474s; supervisor returned after 19.9954s with child_failed. Signal code was
checked against local SIGXCPU. Parent correctly reports child_failed rather than
wall timeout because child CPU guard fired first. Summary matches per-case
results. No BF16 or linear cases ran; no retries.

This is evidence that this representative FP16 convolution exhausted the CPU
budget while F32 completed quickly in this run; it does not prove all UNet
operators behave identically. Some regression tests overlapped the FP16 case,
so timings are not an uncontended benchmark and no precise speed ratio is
claimed. The CPU-time breach is still a failed bounded case. No FP16 output
exists for error comparison; F32 self-reference errors are zero.

## Next

Next proposed owner-directed micro-step: design/test a bounded synthetic
FP16-storage/F32-convolution wrapper comparison, including conversion cost,
finite/numerical checks and temporary allocation measurement. Preserve two
threads and strict guards, no full UNet run or model dtype switch. It would
investigate a targeted route without the >8 GiB full-F32 UNet payload; full-model
memory fit and image quality remain unproven. Benchmark in isolation from app
tests. Phase 5.4 real image acceptance incomplete; 5.5 not started.
