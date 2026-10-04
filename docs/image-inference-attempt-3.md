# 5.4 — Mixed inference attempt 3: decode RSS guard

2026-09-30। Owner authorized one bounded --infer-mixed run. Readiness PASS:
MemAvailable 12,086,247,424 bytes, disk free 98,674,315,264 bytes; expected local
snapshot index/four weights present, inventory hashes reused. Output absent,
git-ignored. Unchanged source's prior 128-test evidence reused.

Command: `.venv/bin/python -m scripts.image_load_probe --infer-mixed --output data/image-inference-probe/attempt-3`

Same offline settings: 300s wall/CPU, 24 GiB AS, sampled 8 GiB RSS, 2 GiB host
reserve, two threads, seed 42, 512x512, one step/guidance 0. UNet/encoder storage
FP16, UNet Conv2d compute F32 through opt-in adapter, VAE F32.

## Result

FAIL: rss_limit after 188.642731912s; child -9, CLI 1, supervisor kill/wait
completed. Sampled peak 8,591,810,560 bytes (~8.00175 GiB), above 8,589,934,592
threshold by 1,875,968 bytes. Guard polling is approximate; no limit increase.

| Event | Child elapsed seconds | Process CPU seconds |
| --- | ---: | ---: |
| loaded | 68.2639 | 26.1415 |
| unet_enter | 73.3928 | 36.3423 |
| unet_exit | 176.2626 | 229.3853 |
| pipeline_returned | 176.2652 | 229.3894 |
| latents_validated | 176.2660 | 229.3904 |
| decoding | 176.2664 | 229.3914 |

UNet completed in 102.8697s wall (~193.043 CPU seconds), and latents passed
finite validation. Unlike attempt-2, this run reached VAE decode; no claim of
controlled speed ratio across runs. No decode_returned/image_saved event, PNG or
metadata. Image acceptance remains incomplete. The stage narrows the memory
breach to the decode interval, not a specific allocation: all loaded components,
retained tensors and allocator caches may contribute.

## Checks/next

21 timing events parsed; final event agrees with stage/result evidence. Artifact
absence verified. Plan drift, whitespace, doc links and RESUME length PASS.
No source change/test rerun, install/download, paid resource, retry or commit.

Next proposed owner-directed micro-step: inspect object lifetimes and installed
VAE decode options; design/test one memory reduction using synthetic fixtures.
Candidate: release denoising-only UNet/text encoders before decode, accounting
for both pipeline and loader dictionaries/temporary hooks retaining references.
No full run or limit increase in that step; no guarantee allocator RSS returns
without measurement. Other options require evidence before selection. Phase
5.4 incomplete; 5.5 not started.
