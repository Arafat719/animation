# 5.4 — Bounded single-image inference harness

2026-09-29। Owner authorized harness implementation and synthetic/stub tests only.
No SDXL weights loaded or real inference performed in this step.

## Implementation

Existing image_load_probe adds explicit --infer, mutually exclusive with --load;
default remains synthetic smoke. Same guarded child, offline environment/socket
restriction, 300s wall/CPU, 24 GiB address space, sampled 8 GiB RSS/2 GiB host
reserve, exit monitoring and kill/reap behavior. Load and inference share the
same total budget; no retries or automatic limit increases.

New scripts/image_inference.py calls the validated pipeline with fixed English
anime explorer prompt, seed 42, CPU generator, 512x512, one step, guidance 0,
one image and latent output. Under inference_mode it checks finite latents,
decodes explicitly with the F32 VAE and scaling factor, rejects unsupported
latent mean/std normalization, checks decoded values before postprocess/clamp,
then checks finite normalized RGB pixels and exact shape.

Writes image.png exclusively, verifies PNG format/RGB/512x512 with Pillow verify
and decode, and records SHA-256 plus prompt/seed/snapshot/model/steps/guidance/
device/dtypes in metadata.json. Stage image_saved is written only after validation.
Parent requires successful exit and final stage then revalidates PNG/checksum
and seed/prompt before reporting image_saved. Other failures remain failed.
The fresh evidence directory rule protects old runs; failed runs may contain
partial artifacts and must not be presented as successes.

## Verification

104 relevant tests PASS: 8 inference + 26 probe + 19 streaming + 22 image +
29 workflow. Stub pipeline tests fixed inference arguments, F32 scaling/decode,
finite checks, real synthetic PNG and metadata/checksum, wrong shape/range/NaN,
existing file preservation and parent rejection of success stage without image.
Child orchestration stubs exercise load/infer success and component exceptions;
existing subprocess offline/memory/timeout/reap tests remain passing.
Initial parent stub lacked returncode and failed; fixture corrected, final suite
fully passed with no skipped tests. Ruff lint/format and docs checks PASS.

## Limits and next

No real image yet. Load-only peak ~7.547 GiB leaves ~0.453 GiB below the RSS
stop threshold; real inference may fail on activations/time. No claim of memory
fit, image quality or seed repeatability across platforms. Pixel/PNG validity
is not human anime-quality acceptance. Production API/UI/artifact delivery untouched.

Next proposed owner-directed micro-step: fresh RAM/readiness check then one
--infer attempt in a fresh ignored data/image-inference-probe/attempt-1 directory,
same limits, no retry. Verify result/metadata and visually review any successful
image. Stop/report if a guard or runtime fails; no implicit budget increase.
Phase 5.4 image acceptance incomplete; 5.5 still not started. No install/download,
paid resource, model-file mutation or commit.
