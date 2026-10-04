# 5.4 — Pread load-only attempt 4

2026-09-29। Owner next-work instruction authorized one changed-path load attempt.
No retries, inference, limit increases or source edits. Earlier attempts retained.

## Preflight and execution

MemAvailable 11,977,879,552 bytes (~11.16 GiB), swap unused; disk available
98,914,967,552 bytes (~92.13 GiB). New output directory absent and git-ignored.
Existing model/runtime inventory and unchanged 85-test evidence reused.
Same offline CPU limits: 300s, 24 GiB address space, sampled 8 GiB RSS and
2 GiB host reserve.

```sh
.venv/bin/python -m scripts.image_load_probe --load --output data/image-load-probe/attempt-4
```

## Result

**FAIL: child_failed / ValueError**, failed_stage `loading_text_encoder`.
Error: `Checkpoint/model keys differ`, image_stream_load.py line 36.
Elapsed 53.0912s; sampled peak RSS 6,447,804,416 bytes (~6.005 GiB).
Child/CLI exit 1; supervisor wait/reap completed. No reported memory/timeout
or monitor guard failure. Ignored stage/result evidence retained under
`data/image-load-probe/attempt-4/`.

VAE and UNet component loading returned before the first text encoder's key
validation failed. Thus the pread path passed the earlier UNet mapping blocker
in this run; full pipeline load and inference feasibility remain unproven.
The key mismatch is correctly rejected; exact missing/extra keys have not yet
been inspected. Do not infer corruption or silently drop checkpoint keys.
No image generated; Phase 5.4 acceptance remains incomplete.

## Checks and next

Actual bounded attempt failed as recorded. Prior 85 passing tests reused because
source unchanged. Plan drift, whitespace, checkpoint links and RESUME length PASS.
Only docs and ignored evidence changed; no install/download/paid action/commit.

Next proposed owner-directed micro-step: compare local text-encoder checkpoint
header keys with its empty-model schema and inspect installed compatibility
handling; implement/test a narrowly justified correction if supported by evidence.
Use metadata/meta models and small synthetic fixtures, not another full-model
run. No automatic retry or relaxed key validation. Inference/5.5 not started.
