# Phase 5.4 — remaining original plan, Step 1: ComfyUI runtime

তারিখ: 2026-10-02। **Runtime specification/pinning সম্পন্ন; source ও dependency
metadata compatibility PASS। Installed ComfyUI/GPU execution এখনো অযাচাইকৃত।**
শুধু owner-authorized Step 1; ImageProvider implementation, deployment ও generation নয়।

## Exact runtime

- Repository: `https://github.com/Comfy-Org/ComfyUI.git`
- Release: **v0.38.0**, published 2026-09-29।
- Immutable commit: **`6b747c0428c343e1417219641db93a4fb7cb69ae`**।
- CPython 3.12 / Linux x86_64 / Ubuntu 24.04; existing CUDA 13.0 ও
  `torch==2.14.0+cu130` অপরিবর্তিত। Existing base-image digest, driver minimum
  580.126.20 ও library/resource preflight: [CUDA checkpoint](image-cuda-runtime.md)।
- Machine-readable pin, source SHA256, exact wheel metadata evidence ও launch
  arguments: [runtime manifest](manifests/comfy-runtime.json)।
- [Additive lock](../requirements-comfy-cu130.lock) existing
  [62-package CUDA lock](../requirements-sdxl-cu130.lock) include করে; আগের কোনো
  package বদলায় না। 45টি additional package version/wheel SHA256 pinned।
  Upstream requirements-এর “non essential” section-ও রাখা হয়েছে, যাতে upstream
  install requirements বাদ দিয়ে আলাদা unsupported profile বানাতে না হয়।

[Release](https://github.com/Comfy-Org/ComfyUI/releases/tag/v0.38.0),
[pinned requirements](https://github.com/Comfy-Org/ComfyUI/blob/6b747c0428c343e1417219641db93a4fb7cb69ae/requirements.txt)
এবং [pinned README](https://github.com/Comfy-Org/ComfyUI/blob/6b747c0428c343e1417219641db93a4fb7cb69ae/README.md)
পর্যালোচিত। README-তে torch minimum 2.7 এবং NVIDIA-এর জন্য cu130 নির্দেশিত;
Python 3.12 অনুমোদিত বিকল্প। এটি exact combination-এর real execution guarantee নয়।

## Existing workflow এবং model mapping

[Pinned nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/6b747c0428c343e1417219641db93a4fb7cb69ae/nodes.py)-তে
সাতটি workflow node registered। Built-in `DiffusersLoader` deprecated হলেও আছে;
`model_path` input এবং `(MODEL, CLIP, VAE)` output order existing JSON-এর সঙ্গে মেলে।
**Custom nodes প্রয়োজন নেই।** একই নামে third-party Diffusers loader install নয়।

Future registration: configured `diffusers` root-এর নিচে `sdxl-turbo/` directory
বা verified snapshot-এ symlink থাকতে হবে; তার মধ্যে `model_index.json` লাগবে।
Default layout: `<ComfyUI>/models/diffusers/sdxl-turbo/`। Loader input থাকবে
`sdxl-turbo`; snapshot revision `71153311d3dbb46851df1931d3ca6e939de83304`।
কোনো model registration/copy এই step-এ করা হয়নি।

[Pinned loader](https://github.com/Comfy-Org/ComfyUI/blob/6b747c0428c343e1417219641db93a4fb7cb69ae/comfy/diffusers_load.py)
existing manifest-এর `unet/diffusion_pytorch_model.safetensors`,
`vae/diffusion_pytorch_model.safetensors`, এবং দুই
text encoder-এর `model.safetensors` নির্বাচন করতে পারে। এটি ComfyUI-এর native
model/CLIP/VAE loading path; Python diffusers pipeline চালায় না। Existing
`diffusers==0.40.0`/`accelerate==1.14.0` রাখা হয়েছে, loader-এর জন্য নতুন version লাগে না।
আগের custom streaming-loader/CPU memory ফল এই native loader-এর memory evidence নয়।

## Dependency compatibility

182 active upstream/transitive requirement checks PASS; Python requirements ও
CPython 3.12/Linux-compatible additional wheel availability PASS। এটি metadata
closure check, pip clean-install/resolver বা native ABI execution test নয়।

| Dependency | নির্বাচন / ফল |
| --- | --- |
| torch / torchvision | `2.14.0+cu130` / `0.29.1+cu130`; exact official wheel sidecar-এ torchvision চায় torch >=2.14.0: PASS |
| transformers / tokenizers | existing `5.16.1` / `0.23.2`; upstream lower bounds PASS; actual `CLIPTokenizer` import PASS |
| safetensors / numpy / Pillow | existing `0.8.0` / `2.5.3` / `12.3.0`; constraints PASS |
| Comfy native packages | upstream exact `comfy-kitchen==0.2.36`, `comfy-aimdo==0.5.5`; compatible platform wheels আছে, native import/GPU ABI untested |
| UI packages | upstream exact frontend `1.53.6`, templates `0.11.70`, embedded docs `0.5.12` |
| Other direct additions | torchsde, einops, sentencepiece, aiohttp, yarl, scipy, alembic, SQLAlchemy, av, simpleeval, blake3, kornia, spandrel, pydantic, pydantic-settings, PyOpenGL, comfy-angle; exact versions/transitives additive lock-এ |

[Official torchvision cu130 index](https://download.pytorch.org/whl/cu130/torchvision/)
ও [exact wheel metadata](https://download.pytorch.org/whl/cu130/torchvision-0.29.1%2Bcu130-cp312-cp312-manylinux_2_28_x86_64.whl.metadata)
যাচাই হয়েছে। Torch-এর [exact cu130 sidecar](https://download.pytorch.org/whl/cu130/torch-2.14.0%2Bcu130-cp312-cp312-manylinux_2_28_x86_64.whl.metadata)-ও
এবার `download.pytorch.org` host-এ পাওয়া গেছে; আগের r2-host 403 সীমা metadata-এর
জন্য দূর হয়েছে। Binary wheel extract/install হয়নি।

Pinned `comfy/quant_ops.py` optimized CUDA backend-এর জন্য CUDA >=13 পরীক্ষা করে;
বর্তমান build সেই condition পূরণ করে। Comfy-aimdo 0.5.5-এর published support
PyTorch >=2.8/CUDA >=12.8; numerical bounds মেলে। Native-library load ও actual GPU
architecture support যাচাই বাকি। `xformers`, FlashAttention, custom CUDA compilation
ও torchaudio এই seven-node image workflow-এর requirement নয়।

## Owner installation / later verification boundary

নিচের commands ভবিষ্যতের owner installation recipe, **এই step-এ চালানো হয়নি**।
আগে disk/download budget দেখতে হবে; additional wheels প্রায় 0.70 GB compressed
(PyPI torchvision size দিয়ে estimate), existing CUDA stack/source/unpacked disk
এর বাইরে। কোনো binary/model download বা environment mutation এই review-তে হয়নি।

```sh
git clone --no-checkout https://github.com/Comfy-Org/ComfyUI.git /workspace/ComfyUI
git -C /workspace/ComfyUI checkout --detach 6b747c0428c343e1417219641db93a4fb7cb69ae
git -C /workspace/ComfyUI rev-parse HEAD
# Run from this project's checkout, using the isolated Python 3.12 CUDA venv:
/workspace/sdxl-venv/bin/python -m pip install -r requirements-comfy-cu130.lock
/workspace/sdxl-venv/bin/python -m pip check
```

Mutable master, auto-update ও unpinned `pip install -r ComfyUI/requirements.txt`
এই lock-এর বিকল্প নয়। Future local-only launch arguments manifest-এ আছে:
`--listen 127.0.0.1 --port 8188 --disable-all-custom-nodes --disable-api-nodes
--disable-xformers --use-pytorch-cross-attention`। Remote authentication/tunnel
ও resource supervision wiring এই step-এর অংশ নয়; application inference scripts-এর
limits standalone ComfyUI server-এ স্বয়ংক্রিয়ভাবে প্রযোজ্য হয় না।

## Checks, result, next

- Pinned source isolated checks PASS: seven node registrations; real
  `DiffusersLoader` class-এর schema/discovery/invalid-path rejection; four component
  filename selection with empty fixture files। Full server import/weights নয়।
- Local torch reports `2.14.0+cu130`, CUDA build `13.0`, CUDA available **False**।
- Existing workflow/provider regressions: `51 passed`; provider implementation বদলায়নি।
- **Step 1 runtime definition complete**, source/metadata compatibility PASS;
  clean locked install, native imports, `/object_info`/prompt validation,
  driver/library/tiny CUDA operation এবং real model loading এখনো pending।
- Original plan-এর next Step 2 ImageProvider adapter এই request-এ অনুমোদিত নয়;
  শুরু করা হয়নি। Phase 5.4 real-image acceptance এখনও incomplete।
