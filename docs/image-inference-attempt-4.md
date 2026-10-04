# 5.4 — Mixed inference attempt 4: decode still exceeds RSS guard

2026-09-30। Owner next-work instruction authorized fresh readiness and one
bounded attempt after denoiser-release change. Readiness PASS: MemAvailable
11,987,009,536 bytes; disk free 98,708,213,760 bytes. Local snapshot index and
four weights present; prior inventory hashes and unchanged-source 131-test
evidence reused. New output directory absent and git-ignored before run.

Command: `.venv/bin/python -m scripts.image_load_probe --infer-mixed --output data/image-inference-probe/attempt-4`

Unchanged limits/settings: offline, 300s wall/CPU, 24 GiB address space,
8 GiB sampled RSS, 2 GiB host reserve, two threads, seed 42, 512x512,
one step/guidance 0. FP16 UNet/encoder storage, F32 UNet convolution compute,
F32 VAE. Older attempts preserved; no install/download/paid resource/retry.

## Result

FAIL: rss_limit at 210.042991639s; child -9, CLI 1. Supervisor completed
kill/wait. Sampled peak 8,592,891,904 bytes exceeds 8,589,934,592-byte guard
by 2,957,312 bytes. Sampling is approximate; limits were not increased.

| Event | Child elapsed seconds | Process CPU seconds |
| --- | ---: | ---: |
| loaded | 76.6411 | 27.2761 |
| unet_enter | 82.2368 | 38.2645 |
| unet_exit | 186.2852 | 232.8166 |
| latents_validated | 186.2922 | 232.8238 |
| denoisers_released | 186.4906 | 233.0224 |
| decoding | 186.4911 | 233.0224 |

UNet completed in ~104.05s and latents passed finite validation. The new
release event proves the release code path ran before decode; it does not
prove all real objects were collected or allocator pages returned to OS.
No decode_returned/image_saved event, PNG or metadata. The recorded events
lack per-stage RSS, so no measured memory-reduction or allocation attribution
claim can be made. Real image acceptance remains incomplete.

## Checks and next

All 22 events parsed; ordering, result/stage agreement and artifact absence
verified. Plan drift, whitespace, local links and RESUME length checks PASS.
No source changes or redundant application test run; prior 131 tests reused.

Next proposed owner-directed micro-step: read-only decode memory diagnosis
using current ownership paths and installed VAE/allocator behavior; choose a
bounded synthetic diagnostic or one reduction only after evidence review.
No automatic full-model retry, limit increase or new phase. 5.4 incomplete;
5.5 not started and requires authorization.
