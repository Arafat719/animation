# 5.4 — Release denoising components before decode

2026-09-30। Owner authorized lifetime review and one synthetic-tested reduction;
no full model loading/inference performed.

## Evidence and change

Attempt-3 reached finite latents then crossed RSS guard during VAE decode.
Inspection found pipeline attributes plus child loader `components` and
validation `modules` dictionaries retained UNet/encoders. Timing-hook and mixed
adapter contexts also spanned decode. These are demonstrable retention paths,
not proof of attribution for every byte at the prior RSS peak.

Child now drops component/validation aliases after validation. generate_image
closes timing hooks and temporary mixed-convolution context after finite latent
validation, then clears pipeline UNet/text_encoder/text_encoder_2 attributes,
collects cycles and records denoisers_released before F32 VAE decode. Metadata
records released_before_decode. Both plain and mixed inference use this lifecycle.
Stored model files, prompt, seed, latent values, VAE dtype and limits unchanged.

This is explicitly single-use: after successful latent validation the pipeline
cannot denoise again. VAE and image processor remain available. No allocator trim,
forced process restart, retry, memory-limit increase or tiling added. Installed
VAE source only slices batches greater than one, so slicing alone does not
address this batch-1 path; tiling is conditional on spatial thresholds and can
change outputs. Component release chosen first without changing decode math.

## Verification

131 relevant tests PASS across inference/probe/mixed adapter/operator/stream/
provider/workflow suites. New weak-reference tests prove synthetic denoisers
are collected before decode, including decode failure, and valid artifact still
passes checksum/metadata checks. Invalid latents fail before release, hooks
cleaned. Existing mixed context, parameter restoration, PNG/nonfinite rejection
and subprocess guards remain passing. Ruff/format, plan drift, whitespace,
document links and RESUME checks PASS.

Real pipeline runtime can retain additional references or allocator pages;
Python collection is not a guarantee of lower process RSS. Existing metadata
dtypes describe generation storage even after components are released. No
claim of measured full-model memory reduction, valid real PNG or anime quality.

## Next

Next proposed owner-directed micro-step: fresh readiness then one bounded
--infer-mixed attempt-4, preserving all older attempts and unchanged limits.
Check event/artifact evidence and visually review if successful. Stop/report
on failure; no automatic retry. Phase 5.4 image acceptance remains incomplete;
5.5 not started. No install/download, paid resource or commit.
