# 5.4 — Opt-in CPU mixed Conv2d adapter

2026-09-30। Owner authorized adapter/tests/header inventory only. No full model
load or inference. New scripts/image_mixed_conv.py temporarily overrides exact
plain torch.nn.Conv2d instances on UNet. Stored CPU FP16 parameters are unchanged;
input/weight/bias convert per call to F32, output returns FP16. No persistent
F32 cache. Bias, stride, dilation, groups and zero/reflect/replicate/circular
padding follow Conv2d semantics. Requires eval, gradients disabled, CPU FP16,
no CPU autocast; customized Conv2d/instance forward overrides rejected. Validates
all modules before mutation and restores forward in finally, including failures.
Single-threaded harness scope; concurrent calls on the patched model unsupported.

Explicit --infer-mixed in image_load_probe selects this behavior; default
--infer unchanged. Context affects UNet only, retains module hooks, and records
unet_conv_compute=float32 in image metadata (stored dtype remains float16).
Existing offline/time/memory/success/PNG guards remain. No changed-path run here.

## Checks

128 relevant test cases PASS across the completed runs (124 initial suite plus
4 added integration cases; 43 probe/inference cases rerun PASS). Coverage includes
small real Conv2d F32-reference equivalence for bias/stride/groups/dilation and
padding modes, parameter storage/value preservation, hooks, exception cleanup,
invalid input/training/gradient/dtype rejection, opt-in context/metadata and
stubbed child mixed success/failures. Ruff lint/format PASS after correcting a
test f-string/style issue. Documentation/plan drift/whitespace checks PASS.

## Header-only inventory

Read local UNet safetensors JSON header, no weight payload: 51 four-dimensional
convolution weight entries. Largest F32 weight+bias conversion 117,969,920 bytes
(~112.505 MiB), up_blocks.0.resnets.0/1.conv1, shape [1280,2560,3,3]. Maximum
input channels 2560. For batch 1, conservative 64x64 activation assumption gives
41,943,040 bytes of F32 input and 20,971,520 bytes of F32 output at 1280 channels.
Together with largest weight+bias: 180,884,480 bytes (~172.5 MiB). This deliberately
combines maxima; actual deepest blocks use smaller spatial dimensions. This is
explicit tensor payload arithmetic, not total memory: original FP16 tensors,
output conversion overlap, retained skips, workspace, allocator caching and
other operations are additional. Prior ~0.44 GiB RSS margin does not prove fit.

## Next

Next proposed owner-directed micro-step: fresh readiness then one bounded
--infer-mixed attempt-3 in a fresh ignored directory, unchanged limits, no retry.
Validate PNG/metadata and visually inspect only if successful. Other FP16
operators, full-model memory/latency and output quality remain unproven. No
install/download/paid resources/commit. Phase 5.4 incomplete; 5.5 not started.
