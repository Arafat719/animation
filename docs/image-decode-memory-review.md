# 5.4 — Read-only decode memory review

2026-09-30। Owner instructed continued work; completed the proposed read-only
review after attempt-4. No source change, model load, inference, allocation
experiment, install, download or limit change. Existing unrelated edits retained.

## Findings from installed source and local evidence

- Attempt-4 proves finite latents and execution of denoisers_released before
  decoding, then sampled RSS guard failure. No per-stage RSS or real-model
  weak-reference observations exist; the peak alone cannot attribute memory.
- child_probe deletes components/modules/module validation aliases. Inference
  exits timing and mixed-convolution contexts, deletes the context reference,
  clears all three pipeline attributes and calls gc.collect. Loader locals
  return normally. Installed DiffusionPipeline.register_modules stores class
  identifiers in config, and __setattr__ replaces the actual attribute. No
  additional obvious permanent denoiser owner was found in these paths; this
  is source review, not proof that every runtime tensor/storage is released.
- Existing weakref tests cover synthetic module roots. They do not prove
  collection of real model roots, every parameter or underlying storage.
- Installed AutoencoderKL.decode slices only when batch > 1: this batch is 1.
  Config sample_size=1024 and four channel blocks give tile_latent_min_size=128.
  Current 512x512 image corresponds to 64x64 latents; _decode uses tiling only
  if latent width/height is strictly greater than 128. Merely enabling tiling
  therefore does not activate it here. Lower tile thresholds would change the
  decode path and can change pixels; no quality/memory benefit measured.
- Decoder uses channel stages 512/512/256/128 with three 2x upsamplers.
  The third upsampler produces [1,256,512,512] F32: 256 MiB for that tensor
  alone, before convolution workspace, residuals and other live allocations.
  This is shape-derived payload, not total/peak RSS or proof of the failing op.
  inference_mode already disables gradient recording; training gradient
  checkpointing does not address this active path.
- Installed CPU allocator headers expose alloc/free and replaceable allocator
  interfaces; they do not establish which allocator/workspace retains pages
  in this process. No malloc_trim or allocator environment change is justified
  by current evidence. gc.collect success does not measure OS memory return.
- StageRecorder writes only stage/time/CPU into events.jsonl; extra values go
  into the overwritten stage.json. Adding RSS only as an extra argument would
  lose historical samples. Persistent bounded diagnostics need explicit tests.

Reviewed local files: scripts/image_load_probe.py, image_inference.py,
image_mixed_conv.py, image_stream_load.py; tests/test_image_inference.py;
installed diffusers pipeline_utils.py, autoencoder_kl.py, vae.py,
unet_2d_blocks.py, upsampling.py; torch CPUAllocator.h/impl/alloc_cpu.h;
verified snapshot vae/config.json. These findings describe the installed code,
not a claim about newer package versions.

## Selected next micro-step (proposed)

Add/test bounded persistent decode diagnostics using synthetic fixtures only:
current /proc RSS before/after denoiser release; weakrefs for the three module
roots without retaining them; VAE decoder mid/up-block enter/exit RSS and
elapsed/CPU timing. Remove all hooks on success/failure; no tensor dumps or
strong ownership in diagnostic closures. Persist only explicitly allowed
scalar fields; test JSONL preservation, missing RSS behavior and event bound.
Module collection must not be presented as proof of all storage release, and
boundary RSS samples cannot capture every transient within an operation.

This separates observed retained process memory from growth during decode
before choosing tiling, allocator intervention or another reduction. A later
fresh-readiness full run is a separate owner-directed step, with unchanged
limits and no retries. No automatic attempt-5. Phase 5.4 remains incomplete;
5.5 is not started.

## Checks

Read-only source/config consistency checks PASS; shape/tile arithmetic checked
without tensor allocation. Documentation links, RESUME length, plan excerpt
drift and whitespace PASS. Prior 131 application tests reused; no source edits
requiring a new application test run.
