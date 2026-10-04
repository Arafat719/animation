# 5.4 — Tensor-at-a-time loading change

2026-09-28। One approved load-memory reduction micro-step complete; no new full
SDXL attempt in this step. Attempt 1 remains FAIL at 8 GiB sampled RSS threshold。

## Evidence and change

Installed diffusers 0.40.0 `models/modeling_utils.py` loads a complete unsharded
state_dict; `models/model_loading_utils.py` uses safetensors load_file and casts
floating tensors while the source dictionary is retained. This supports transient
source/destination overlap as a candidate cause; attempt 1 did not capture exact
allocation attribution, so root cause is not proven by its last stage alone。

New `scripts/image_stream_load.py` constructs the four existing component configs
under accelerate.init_empty_weights(include_buffers=False), leaving nonpersistent
buffers on CPU. Before materializing each component it validates safetensors
keys/shapes/F32 dtype against the meta model; shared tensors and unexpected
buffers are rejected. It opens a fresh mapping per tensor, copies to an owned CPU
tensor in target dtype, releases the source tensor/mapping, then installs the
value with accelerate.set_module_tensor_to_device. No complete mapped source
state_dict is retained; no disk conversion or weight mutation occurs。

VAE stays F32; UNet and both CLIP encoders FP16. The probe now supplies all four
loaded components to the existing pipeline, which only loads remaining local
configs/tokenizers. Stages identify loading_vae/unet/text_encoder/text_encoder_2
before pipeline assembly. Previous offline guards and 300s/24 GiB AS/8 GiB sampled
RSS/2 GiB host reserve limits remain unchanged; no retry added。

Scope: inventoried non-sharded F32 safetensors only, not a general model loader.
Unrecognized names/shapes/shared tensors fail closed; no silent key dropping or
checkpoint key rewriting. One large tensor can still cause a transient spike;
RSS polling remains approximate. Full-model peak/time benefit is not yet measured。

## Verification

**77 PASS:** 10 streaming-loader tests + 16 load-probe + 22 image + 29 workflow。
Small real safetensors test values, forward output, both destination dtypes,
source-file preservation; missing/extra/wrong-shape/wrong-dtype/corrupt checkpoints,
non-meta/shared-model rejection. Small actual UNet/VAE/CLIP configs roundtrip via
four-component helper, checking every parameter and CPU buffers. Stubbed child
checks pipeline assembly and offline options; subprocess guard regressions pass。
No SDXL weights loaded by tests. Ruff lint/format, plan drift, whitespace and
local doc links/RESUME checks PASS. No package install/download, API/UI/DB change。

## Next

Next authorized 5.4 micro-step: fresh memory check then **one** changed-path
load-only attempt in a new ignored directory (attempt-2), same limits. Preserve
attempt-1. Do not infer image readiness from synthetic tests. Stop/report on any
failure; no automatic retry or limit increase. If load passes, inference still
needs its own bounded step. Phase 5.4 real image acceptance remains incomplete。
