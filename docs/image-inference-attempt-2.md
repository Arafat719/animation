# 5.4 — Instrumented inference attempt 2: timeout

2026-09-30। Owner authorized one bounded run. Fresh readiness passed:
MemAvailable 12,115,574,784 bytes; disk free 98,677,075,968 bytes. Expected
snapshot index/four weights present; prior inventory hashes reused. Output
absent and git-ignored. Prior 109-test evidence reused.

Command: `.venv/bin/python -m scripts.image_load_probe --infer --output data/image-inference-probe/attempt-2`

Same offline CPU settings: 300s shared wall/CPU budget, 24 GiB address space,
sampled 8 GiB RSS, 2 GiB host reserve, two threads; 512x512, one step, guidance
0, seed 42, FP16 encoders/UNet and F32 VAE. No retry or limit increase.

## Result

FAIL: timeout, elapsed 300.589339201s, child -9/CLI 1. Supervisor kill/wait
completed. Sampled peak RSS 8,113,725,440 bytes (~7.5565 GiB). No image.png or
metadata.json. All 17 events parse and have monotonic elapsed/CPU timestamps;
last event matches stage.json and result child_evidence.

| Event | Child elapsed seconds | Process CPU seconds |
| --- | ---: | ---: |
| loaded | 70.0846 | 25.6711 |
| pipeline_enter | 70.0862 | 25.6718 |
| text_encoder_enter | 70.1006 | 25.6841 |
| text_encoder_exit | 70.6810 | 26.8425 |
| text_encoder_2_enter | 70.6825 | 26.8449 |
| text_encoder_2_exit | 75.6988 | 36.8007 |
| unet_enter | 75.7511 | 36.8115 |

No UNet exit, pipeline return or decode event. Both encoders completed
(~0.58s/~5.02s); this run narrows unfinished work to UNet forward. Roughly 224s
remained without recorded return (parent/child clock origins differ slightly).
No terminal CPU sample exists; slow operator, utilization, paging and FP16
performance cause remain unknown. No RSS/host-memory guard reason reported;
sampling cannot exclude transient memory pressure.

## Checks and next

Evidence consistency and absence of artifacts PASS. Source unchanged; previous
109 tests reused. Plan drift, whitespace, doc links and RESUME length PASS.
Attempt-1 preserved. No install/download, paid resource or commit.

Next proposed owner-directed micro-step: read-only local UNet CPU-path/hardware
review to choose targeted diagnostics or a bounded optimization proposal.
No unchanged retry, speculative dtype/resolution change or limit increase.
Phase 5.4 image acceptance incomplete; 5.5 not started.
