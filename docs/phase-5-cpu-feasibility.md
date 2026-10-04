# 5.4 — Existing CPU reduced-precision feasibility

2026-09-28। Local feasibility micro-step সম্পন্ন; **real image acceptance এখনও নয়**।
Existing 5.4 authorization বহাল। Model weights load বা inference করা হয়নি।

## Evidence

Installed torch 2.14.0+cu130 / diffusers 0.40.0 code inspected।
`pipeline_utils.py` supports low_cpu_mem_usage and CPU dtype selection;
`model_loading_utils.py` converts floating tensors to requested dtype during load।
SDXL pipeline has VAE force_upcast handling। These establish a candidate loading
path, not a measured peak-memory guarantee।

Small synthetic probe: seed 42, two CPU threads, inference_mode; conv2d (1×32×32×32),
group_norm, SiLU, nearest interpolation, attention (1×4×64×32), layer_norm।

| Dtype | Finite outputs | Elapsed seconds |
| --- | --- | ---: |
| F32 | PASS | 0.1554 |
| FP16 | PASS | 0.0339 |
| BF16 | PASS | 0.0201 |

Peak process RSS 511364 KiB (~499 MiB)। Single small run, warmup/order bias আছে;
এটি SDXL latency/accuracy benchmark নয়। Probe bound: external 45s timeout,
RLIMIT_CPU soft/hard 30/35 seconds, post-import RLIMIT_AS baseline VMS +1 GiB।
No sockets, model files, downloads or generated images used in this probe।

Safetensors headers only re-read; exact tensor payload projection:

| Component | Existing F32 bytes | Proposed resident weight bytes |
| --- | ---: | ---: |
| text_encoder | 492241920 | 246120960 |
| text_encoder_2 | 2778639360 | 1389319680 |
| unet | 10269854736 | 5134927368 |
| vae (keep F32) | 334615452 | 334615452 |

Total projected weight payload **7,104,983,460 bytes / 6.617 GiB**। No new FP16
checkpoint is required to test conversion of existing F32 files in memory。
Buffers, retained F32 modules, transient copies, mappings, activations and runtime
allocations are additional; projected weight bytes are not measured model RSS。

## Resource limits and alternatives

Earlier root cgroup lookup was incomplete। Actual process cgroup resolved from
`/proc/self/cgroup`: `/user.slice/user-1000.slice/user@1000.service/app.slice/app-code-9289.scope`。
Its memory.max is `max`, memory.current was 9627664384 bytes (shared scope, not
this agent/model's RSS), and memory.max is not writable। Do not modify the shared
editor scope; no isolated cgroup hard RSS cap established。

Installed enable_model_cpu_offload / enable_sequential_cpu_offload explicitly
require an accelerator by default; these are not a CPU-only RAM fix। See also
[official Diffusers pipeline documentation](https://huggingface.co/docs/diffusers/main/api/pipelines/overview)。
Disk/group offload is not selected or proven here। ComfyUI still absent from
searched roots; direct Diffusers is a feasibility route, not ComfyUI acceptance。

## Concrete next micro-step

Build and test a separate bounded **load-only** subprocess harness before real
load: exact existing snapshot path, local_files_only/use_safetensors,
HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE, no model mutation, no network, two CPU threads,
FP16 encoders/UNet and F32 VAE. It must enforce a hard wall-time/virtual-memory
limit and monitor child RSS plus host MemAvailable, kill/reap on breach and save
stage/error evidence. Initial proposed limits: 300s load window, RSS stop at 8 GiB,
host reserve 2 GiB; address-space bound must include existing file mappings and
be established before model load. RSS polling is not a hard allocation ceiling。
Test guard behavior with synthetic children first; no requirement to ask again
for this already authorized local feasibility work. No automatic retries or
full inference until a load test passes. If guards cannot be established or
load exceeds bounds, report the concrete failure, not readiness success。

5.4 stays incomplete; 5.5 not started. Paid/download/install restrictions and
CPU planner suspension unchanged. Source/provider/UI/DB untouched. Documentation
links, excerpt drift, whitespace and RESUME length checks PASS。
