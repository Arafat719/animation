# 5.4 — One bounded actual load attempt

2026-09-28। Existing-local-resource scope ও owner next-work instruction অনুযায়ী।

## Preflight (before execution)

Current RAM ~10 GiB available, workspace disk 92 GiB free। Existing snapshot and
checksums: [inventory](phase-5-model-inventory.md); no duplicate download।
Runtime installed versions: torch 2.14.0+cu130, diffusers 0.40.0, transformers
5.16.1, accelerate 1.14.0, safetensors 0.8.0। Local package LICENSE files inspected:
Diffusers/Transformers/Accelerate/Safetensors Apache-2.0; torch bundled license
notices include BSD and other third-party licenses (metadata lists Apache-2.0,
LLVM exception, BSD-2/3-Clause, BSL-1.0, MIT)। No redistribution in this test。

[Official pinned model card](https://huggingface.co/stabilityai/sdxl-turbo/blob/71153311d3dbb46851df1931d3ca6e939de83304/README.md)
and [weight license](https://huggingface.co/stabilityai/sdxl-turbo/blob/71153311d3dbb46851df1931d3ca6e939de83304/LICENSE.md)
reviewed: Stability AI Community License, personal evaluation scope; commercial
use has registration/revenue/attribution conditions, not blanket permission。
Model card prefers 512×512, warns of text/face limitations; Bengali support not
established. This load-only test uses no prompt and measures no output quality。

CPU route requires no VRAM; GPU minimum/recommended VRAM not claimed or used。
GPU time 0 by design; cloud/API spend cap $0. CPU load limit 300s; no inference
latency estimate. Existing 67-test guard evidence reused. Mixed-weight estimate
6.617 GiB is not total memory. Guard defaults unchanged: 24 GiB virtual limit,
8 GiB sampled RSS stop, 2 GiB host reserve, two CPU threads, offline load。

Command (one attempt only):

```sh
.venv/bin/python -m scripts.image_load_probe --load --output data/image-load-probe/attempt-1
```

Output directory verified ignored; new directory required, no overwrites/retries。

## Result

**FAIL: rss_limit**, elapsed **18.7836 seconds**। Sampled peak RSS
8,602,546,176 bytes (~8.012 GiB), exceeding 8 GiB stop threshold। Last saved stage
`loading_pipeline`; VAE loader had returned, full pipeline had not completed।
Child return code -9; supervisor killed/reaped it and subsequent /proc check
confirmed child absent। CLI exit 1, no image generated। No automatic retry,
limit increase or inference। Saved stage/result evidence remains in ignored
`data/image-load-probe/attempt-1/`।

This proves the current loading path exceeds the configured RSS budget. It does
not prove final resident weights cannot fit: F32 mappings/conversion buffers may
contribute, but the probe did not measure component-level allocation attribution。
Do not label it an OOM, model corruption or incompatible CPU without evidence。

## Next and checks

Next authorized 5.4 micro-step: inspect installed loading code and design/test a
load-memory reduction for conversion/mapping overhead, with the same resource
limits. No repeat real run until that change is supported by evidence. If no
bounded path is found, retain the blocker; do not silently raise the limit or
restart CPU planner experiments. Full Phase 5.4 acceptance remains incomplete。

Checks: actual bounded attempt failed as recorded, guard/child cleanup worked;
previous 67 tests reused because source unchanged. Docs links/plan drift/whitespace
and RESUME length PASS. Only docs/status and ignored runtime evidence changed;
no install/download/cloud/model-file mutation/commit。

