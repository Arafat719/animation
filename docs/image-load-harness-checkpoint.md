# 5.4 — Bounded load-only harness

2026-09-28। অনুমোদিত local CPU feasibility micro-step সম্পন্ন; model load হয়নি।

## Implementation

`scripts/image_load_probe.py` নতুন evidence directory-তে stage.json/result.json
লেখে। Existing output directory overwrite করে না। Default synthetic smoke;
`--load` থাকলেই exact inventoried local SDXL snapshot load path নেওয়া হয়।
কোনো inference call, image generation, download, retry বা persisted weight conversion নেই।

Default limits: 300s parent deadline + child ITIMER_REAL; RLIMIT_CPU 300/301s;
RLIMIT_AS 24 GiB before torch import; core dump disabled। 24 GiB is a virtual
address ceiling allowing F32 mappings/reduced weights/runtime; it is not a
physical-memory budget or measured proof of successful loading। RSS stop 8 GiB,
host MemAvailable reserve 2 GiB sampled every 50ms। These two are polling limits,
not hard allocation caps; short spikes can escape detection। Parent kills/reaps
child on breach/error; trusted child has no subprocess workers। Parent crash
still leaves child timer/limits, but no claim of durable supervisor recovery。

Offline environment flags plus Python socket audit guard reject connect/DNS/sendto;
local_files_only/use_safetensors/low_cpu_mem_usage set on both loaders। This is
trusted Python runtime protection, not a kernel network sandbox against arbitrary
native code。 Two torch threads, one interop thread; F32 VAE explicitly supplied,
FP16 encoders/UNet requested; CPU/dtype checked after load। Final child evidence
records stage/error type or successful dtypes and peak RSS। Exit zero alone does
not count as loaded: supervisor requires matching final stage too。

## Checks

16 new tests + 22 ImageProvider + 29 workflow = **67 PASS**। Synthetic success,
network rejection, applied RLIMIT_AS, timeout/RSS/AS failures, host reserve before
and during launch, monitor failure/reaping, preserved output, invalid limits;
stubbed-runtime child checks exact offline/dtype settings without torch/weights。
Ruff lint/format, plan drift, whitespace, local docs links/RESUME length PASS。
Only source added is isolated probe script and its tests; provider/API/UI/DB untouched。

## Usage and next step

Safe synthetic command (directory must not already exist):

```sh
.venv/bin/python -m scripts.image_load_probe --output /tmp/animation-image-load-synthetic
```

Next authorized micro-step is one actual load-only attempt after checking current
free memory and runtime/license preflight, using a fresh ignored evidence directory:

```sh
.venv/bin/python -m scripts.image_load_probe --load --output data/image-load-probe/attempt-1
```

No command with `--load` was run in this step. Runtime import under the new
24 GiB ceiling and actual loading peak/time remain unmeasured. If it fails, report
saved stage/error and limits; do not automatically retry or increase budgets。
Success establishes load only, not image quality or inference acceptance. 5.4
remains incomplete; 5.5 and paid/download/install work are not started。
