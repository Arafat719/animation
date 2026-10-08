# Phase 5.4 — bounded local RAM telemetry reader

2026-10-05। Owner next-work নির্দেশে reader/tests micro-step সম্পন্ন।

## Implementation

[OwnedChildRamReader](../animation_studio/providers/comfy_ram_telemetry.py) Linux
Popen direct-child handle নেয়; PID, current parent PID ও প্রথম valid sample-এর
process start ticks ধরে। Read-এর আগে/পরে stat identity এবং child.poll exit check;
PID reuse/parent mismatch/exit race-এ success sample নয়। Stat comm-এর spaces,
parentheses/newline handling আছে। /proc stat/status/meminfo প্রতি read সর্বোচ্চ
65537 bytes; 65536 bytes-এর বেশি হলে invalid। VmRSS/MemAvailable একবারই থাকতে হবে,
nonnegative integer kB থেকে bytes conversion; wrong unit/duplicate/missing reject।

Immutable result-এ monotonic read-start timestamp, PID/start ticks, RSS এবং available
RAM। Source local_procfs; coverage direct_child; VRAM সবসময় None। unavailable,
invalid, identity_mismatch বা exited হলে memory/start fields None; valid measured
zero আলাদা। Signal/spawn/network/model/GPU import বা supervisor wiring নেই।
Reader poll child exit observe/reap করতে পারে; OS read latency hard deadline নয়।

## Checks

Prior unchanged policy/supervisor baseline evidence reused। New
[37 cases](../tests/test_comfy_ram_telemetry.py): fixture byte conversion, malformed/
duplicate fields, four read-boundary disappearances, PID reuse, identity/parent
mismatch, exit during read, permission errors, byte-boundary checks, no network/GPU
imports ও real small owned child read/exit। কোনো বড় allocation/model load হয়নি।

`.venv/bin/python -m pytest -q tests/test_comfy_ram_telemetry.py
 tests/test_comfy_resource_guard.py tests/test_comfy_dummy_supervisor.py`
(এক লাইনে): **124 PASS**। Ruff lint/format, docs links/RESUME length,
plan drift ও whitespace checks PASS। Existing source/schema unchanged।

## সীমা ও next

Direct child RSS process-tree aggregate বা hard cap নয়; kernel-provided approximate
reading, files atomic snapshot নয়। MemAvailable local host estimate, cgroup remaining
budget নয়। Read bracket identity validation সম্পূর্ণ PID-namespace/security attestation
নয়; caller owned Popen lifecycle বজায় রাখবে। VRAM/remote host সম্পর্কে evidence নেই।
এই partial CPU reading full ComfyResourceSample-এ fake GPU values দিয়ে রূপান্তর হয়নি।
Offline reader-এর blocker নেই; real image GPU gate বহাল।

পরের owner-directed micro-step: dummy supervisor-এ real CPU telemetry ব্যবহারের
সীমিত integration contract—CPU-only guard, unknown VRAM provenance, missing/invalid
reading abort ও bounded sampling ownership নির্ধারণ। Full GPU admission bypass,
process-tree enforcement বা live Comfy launcher নয়; implementation আলাদা scope।
