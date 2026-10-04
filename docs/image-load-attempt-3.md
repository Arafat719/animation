# 5.4 — Diagnostic load-only attempt 3

2026-09-29। Owner next-work instruction authorized one bounded diagnostic load.
Prior attempts retained; no retry, inference or source changes.

## Preflight and command

MemAvailable 12,002,865,152 bytes (~11.18 GiB), swap unused; disk available
98,916,016,128 bytes (~92.13 GiB). New attempt-3 directory absent and git-ignored.
Existing snapshot/runtime inventory and unchanged 84-test plus 30 synthetic-run
guard evidence reused. Same CPU/offline limits: 300s, 24 GiB address space,
sampled 8 GiB RSS / 2 GiB host reserve.

```sh
.venv/bin/python -m scripts.image_load_probe --load --output data/image-load-probe/attempt-3
```

## Result

**FAIL: child_failed / RuntimeError**, failed_stage `loading_unet`.
Elapsed 7.7068s; sampled peak RSS 1,116,200,960 bytes (~1.040 GiB).
Child/CLI exit 1; supervisor wait/reap path completed. No monitor error or
reported RSS/host-reserve/timeout breach. No image generated.

Error: `unable to mmap 10270077736 bytes` from the existing UNet safetensors
file, followed by `Cannot allocate memory (12)`. Traceback ends at
`load_f32_component`, image_stream_load.py line 44 (header-validation safe_open).
The VAE-loading call had returned; UNet tensor materialization had not started.

Evidence is retained in ignored `data/image-load-probe/attempt-3/` stage/result
JSON. Diagnostics now identify operation, message and frames. This proves a
mapping allocation failure, not physical RAM exhaustion or model corruption.
The active 24 GiB virtual-address limit is a candidate constraint; exact virtual
usage/mapping multiplicity was not measured, so that cause is not yet proven.
Attempt-2 lacked these details and cannot be conclusively attributed retroactively.

## Checks and next

Actual bounded load FAIL as recorded; source unchanged, previous 84 passing
tests and 30 synthetic checks reused. Plan drift, whitespace, local doc links
and RESUME length PASS. Only docs and ignored runtime evidence changed.
No install/download/paid resource/limit increase/commit.

Next proposed owner-directed micro-step: inspect the installed safetensors
mapping path and measure bounded synthetic mapping/address-space behavior;
design/test a loading adjustment only if supported by evidence, under the same
limits. No automatic full-model retry. Phase 5.4 real image remains incomplete;
inference and 5.5 are not started.
