# 5.4 — Local image runtime preflight

2026-09-28। Owner next-work নির্দেশে 5.4 existing-local-resource scope শুরু;
**preflight সম্পন্ন, real image acceptance BLOCKED**। আবার সাধারণ execution
approval চাওয়ার প্রয়োজন নেই; নিচের readiness সমস্যা সমাধান করতে হবে।

## Read-only findings

| Check | Observation |
| --- | --- |
| Project interpreter | `.venv/bin/python` |
| Installed distributions | torch 2.14.0, diffusers 0.40.0, transformers 5.16.1, accelerate 1.14.0, safetensors 0.8.0 |
| Runtime import | torch 2.14.0+cu130; StableDiffusionXLPipeline import PASS |
| CUDA | build 13.0, `torch.cuda.is_available()` false; nvidia-smi not on PATH |
| Visible DRM device | vendor 0x8086, device 0x0412; CUDA execution unavailable in current environment |
| RAM snapshot | 15 GiB total, about 10 GiB available; 2 GiB swap |
| Workspace disk | 92 GiB available |
| Dependency consistency | `python -m pip check`: no broken requirements |
| ComfyUI discovery | folder_paths.py / extra_model_paths.yaml absent in searched Developments, animation-app, /opt; candidate-name search also checked Downloads |
| ComfyUI frontend package | absent from project venv; absence alone does not establish server availability |
| Listener discovery | ss netlink access denied; no claim that no external/local server exists |

Import produced a torchvision-missing warning with PIL fallback; pipeline import
still passed। No dependency install is inferred necessary from that warning alone।
Cgroup memory limit files unavailable at checked standard paths; no verified hard
memory budget established। No package install/update, model load or inference।

## Why execution did not proceed

[Existing inventory](phase-5-model-inventory.md) has 12.93 GiB F32 snapshot;
resident model plus runtime/activations has no demonstrated fit within currently
available RAM। This blocks an unbounded full-F32 CPU run, not a claim that every
optimized CPU/offload/precision route is impossible। A different bounded route
needs measured feasibility and explicit technical design first।
[Workflow](comfy-workflow-checkpoint.md) uses a future DiffusersLoader registration
alias, not a verified installed ComfyUI runtime/model registration। Its loader is
also deprecated upstream; live node inventory and version compatibility remain
unverified। Current runtime licenses/hardware preflight are incomplete because
no runnable ComfyUI installation/version was found or selected।

Legacy `app.py` uses online-capable from_pretrained(model_id), implicit runtime
choice, 1024×1024/four-step generation and no explicit seed in the pipeline call।
It was read, not invoked or changed; it does not implement the bounded 5.4 profile।

## Next concrete work

5.4 remains active but blocked on a usable runtime/hardware route. Resolve one
local runtime route (existing ComfyUI path if owner has one, or a separately
specified bounded CPU feasibility path) before inference. Agent will not install
software: owner preference remains in force. If installation becomes necessary,
prepare exact pinned commands, download size/destination/free-space first; no
speculative installation request now. RunPod/payment suspension remains in force。

Current 5.4 authorization persists; paid resources/new downloads still need their
separate approvals. Do not skip to 5.5 or repeat completed mock work. No real
image, measured inference time, model-output quality or hardware success claimed。

## Checks

Read-only package/runtime/RAM/disk/device checks above; model hashes from 5.1
reused (no repeated 13 GB read). Plan excerpt drift, whitespace, RESUME length and
local document links PASS. App tests not rerun for this documentation-only result。
