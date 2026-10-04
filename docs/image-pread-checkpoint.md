# 5.4 — Mapping diagnosis and pread loader

2026-09-29। Owner authorized mapping diagnosis and evidence-led adjustment with
synthetic checks. No SDXL load, inference, install or download in this step.

## Evidence

Installed safetensors 0.8.0 torch.py and __init__.pyi expose safe_open's `backend`
keyword: mmap default, pread reads tensor bytes. No dependency update needed.
Local 64 MiB synthetic F32 checkpoint, CPU/two threads, 45s alarm and 24 GiB
hard address limit: mmap retained one file mapping of 67,112,960 bytes inside
safe_open; pread retained zero at the same observation point. Peak RSS 563,584 KiB.
This measures retained mappings, not transient allocations while opening.

A separate subprocess lowered its soft address limit to current VmSize +32 MiB
(after imports and fixture creation; hard ceiling still 24 GiB). Both backends
failed with MemoryError opening the 64 MiB fixture. The first diagnostic stopped
because it caught RuntimeError only; after including MemoryError, pread also
failed. Therefore pread does NOT eliminate all file-sized opening headroom.

With +96 MiB soft headroom, mmap failed with RuntimeError / Cannot allocate
memory (12), while pread opened, validated the large tensor shape and returned
a small tensor's correct value. Peak RSS 564,168 KiB. This demonstrates reduced
opening/retained mapping pressure, without claiming the exact internal mapping
count or that the full model will fit. Synthetic soft limits were below the
unchanged production ceiling; no model-run limit was increased.

## Change and checks

Both header validation and per-tensor reads now explicitly use backend='pread'.
Existing keys/shapes/F32 checks, one-tensor owned copy, destination dtype and
source preservation behavior remain. A new regression inspects actual /proc
maps during loader opening/reads and rejects retained checkpoint mappings.
85 tests PASS: 11 streaming + 23 probe + 22 image + 29 workflow. Small real
UNet/VAE/CLIP roundtrips, both target dtypes and malformed checkpoints included.
Ruff lint/format, plan drift, whitespace, local doc links/RESUME length PASS.

## Limits and next

A source tensor still needs RAM before its destination copy; opening still needs
transient virtual space. The previous attempt's exact VmSize was not captured.
Full-model feasibility and performance remain unmeasured. No automatic retry.
Next proposed owner-directed micro-step: fresh memory check and one changed-path
load-only attempt-4 in a new ignored directory, unchanged limits; stop/report on
failure. Phase 5.4 real image remains incomplete; inference/5.5 not started.
