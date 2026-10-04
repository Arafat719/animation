# Phase 5.4 — CUDA inference প্রস্তুতি

২০২৬-১০-০২ update: [explicit CUDA AS policy](image-cuda-address-policy.md) যোগ হয়েছে; নিচের পুরোনো AS blocker এখন সেই policy দ্বারা superseded, actual GPU validation বাকি।

২০২৬-১০-০১। Owner শুধু minimal CUDA preparation ও lightweight tests অনুমোদন
দিয়েছেন। কোনো real model load/generation, CUDA kernel run, RunPod deployment,
paid GPU, download বা package install হয়নি। Existing unrelated edits preserved।

## ঠিক কী বদলেছে

| File | পরিবর্তন |
|---|---|
| `scripts/image_device.py` | `torch.cuda.is_available()` দিয়ে CUDA/CPU নির্বাচন; device-only transfer; CUDA failure হলে error, automatic retry/fallback নয় |
| `scripts/image_inference.py` | pipeline CUDA-তে transfer; selected-device seeded generator; F32 decode input একই device-এ; CPU mixed-convolution adapter শুধু CPU-তে; actual device/compute dtype metadata |
| `scripts/image_split_probe.py` | saved latents-এর generation device/compute metadata; separate real-latent VAE decoder-ও auto CUDA/CPU; CPU↔GPU handoff-এ checksum/NPY contract অপরিবর্তিত |
| `scripts/image_load_probe.py` | local `SDXL_TURBO_SNAPSHOT` environment override; default আগের path; selected device bounded JSONL-এ persist |
| `tests/test_image_device.py` | availability selection, dtype-preserving transfer arguments, CUDA failure propagation, device event, snapshot override |
| `tests/test_image_inference.py` | synthetic CPU tests GPU host-এও CPU-তে বাধ্য; mocked CUDA pipeline/generator/latent routing, CPU adapter bypass, F32 VAE/metadata |
| `tests/test_image_split_probe.py` | synthetic CPU/GPU separate-decode routing/scaling/metadata; actual CUDA allocation ছাড়া |
| `docs/RESUME.md`, `docs/current-build-status.md`, এই checkpoint | ফল, সীমা ও next-step handoff |

FP16 UNet/encoders, F32 VAE, seed 42, 512x512, এক step অপরিবর্তিত।
CPU loader আগের মতো tensor-at-a-time CPU-তে load/validate করে, তারপর inference
হলে CUDA transfer হয়। `--load` ও zero-latent `decode-only` diagnostics CPU-only
থাকে। `--infer`, `--infer-mixed`, latent-only generation ও real split-decode
auto selection ব্যবহার করে। CUDA-তে mixed flag CPU adapter চালায় না।
CPU/GPU একই seed-এর output byte-identical হবে—এমন দাবি নেই।

## Guards এবং checks

আগের 8 GiB sampled **host RSS**, 2 GiB host reserve, 24 GiB virtual address-space,
300 wall/CPU seconds, offline/network block, child kill/reap, no retry ও output
verification অক্ষত। 8 GiB RSS guard GPU VRAM cap নয়; GPU OOM error propagate হয়।
CUDA transfer/inference failure ঢেকে CPU-তে আবার costly কাজ চালানো হয় না।

151-test relevant regression PASS (22.78s), পরে expanded split/device suite
12 PASS (8.38s): মোট 152 distinct relevant cases, কিছু overlap আছে। Ruff
lint/format এবং generated plan drift/whitespace checks PASS। সব CUDA routes
mocked; কোনো GPU hardware validation হয়নি।

## প্রথম RunPod test readiness

**Source-level CUDA preparation সম্পন্ন; unconditional RunPod launch-ready নয়।**
GPU-enabled compatible PyTorch/CUDA driver ও model dependencies, verified existing
F32 snapshot/config/tokenizer files-এর local path, available RAM/VRAM preflight
এবং paid-run authorization দরকার। Runtime/model dependencies মূল requirements
ফাইলে ইচ্ছাকৃতভাবে নেই; owner install করবেন। এই turn deployment package বানায়নি।

বিশেষ unresolved compatibility: unchanged 24 GiB `RLIMIT_AS`-এর মধ্যে CUDA
context/virtual address reservations initialize হতে পারবে কি না GPU host-এ
যাচাই হয়নি। Guard silently disable/বাড়ানো হয়নি। তাই GPU allocation smoke preflight
pass না করলে full-model test শুরু করা উচিত নয়। CPU loading-এর host RAM pressure
সম্পূর্ণ চলে গেছে বলাও যাবে না। GPU diagnostic hooks-এর timing asynchronous;
বর্তমান RSS/HWM diagnostics host memory মাপে, GPU peak VRAM নয়।

পরবর্তী owner-authorized GPU preflight-এর পরে existing guarded command ব্যবহার
করা যাবে, verified snapshot remote host-এ আগে থেকে রাখতে হবে:

```bash
SDXL_TURBO_SNAPSHOT=/absolute/path/to/verified-sdxl-turbo-snapshot \
  .venv/bin/python -m scripts.image_load_probe --infer-mixed --address-policy cuda \
  --output data/image-inference-probe/NEW-GPU-EVIDENCE-DIRECTORY
```

এই command চালানো হয়নি। Phase 5.4 real-image acceptance এখনো incomplete;
Phase 5.5, deployment ও paid test অনুমোদিত/সম্পন্ন নয়।
