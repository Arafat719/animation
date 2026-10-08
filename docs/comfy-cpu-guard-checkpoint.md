# Phase 5.4 — C1 pure CPU guard

2026-10-05। Owner next-work নির্দেশে [CPU contract](comfy-cpu-supervision-contract.md)-এর
C1 implementation সম্পন্ন। Sampler বা process integration এই step নয়।

## Implementation

[CPU evaluator](../animation_studio/providers/comfy_cpu_guard.py) existing policy ও
mock context revalidate করে; caller-pinned PID/start_ticks এবং LocalRamReading-এর
exact type, status, provenance, timestamp ও memory types যাচাই করে। Malformed
caller arguments ValueError; malformed/missing/failure telemetry abort with bounded
reason। Reader exited status worker_exit_unconfirmed: parent exit proof লাগবে।

RAM >= limit, host available <= reserve, stale age > threshold, run deadline >=
boundary-তে abort; multiple reasons stable order। একই start থেকে run/cleanup/final
budget; finite/overflow/precision checks, remaining clamp zero। Result frozen,
input unchanged, scope local_cpu_dummy, VRAM unknown। GPU fields দিয়ে fake reading
তৈরি হয় না। Guard I/O/clock read/process action করে না; full image admission নয়।

## Checks

Prior unchanged RAM/resource/supervision evidence reused।
[65 new cases](../tests/test_comfy_cpu_guard.py): CPU boundaries, failure statuses,
forged dataclass/types/provenance/identity, invalid policy/live context, simultaneous
breaches, stale equality, overflow/collapse, no deadline reset, valid zero এবং
no file/socket/process/time/GPU I/O।

`.venv/bin/python -m pytest -q tests/test_comfy_cpu_guard.py
 tests/test_comfy_ram_telemetry.py tests/test_comfy_resource_guard.py
 tests/test_comfy_supervision.py` (এক লাইনে): **273 PASS**।
Ruff lint/format ও docs links/RESUME length/plan drift/whitespace checks PASS।
Existing source/API/storage schema/master requirements পরিবর্তন হয়নি।

## Limits ও next

Decision enforcement নয়; caller ownership/clock continuity pin করবে। CPU-only
allow GPU-ready বা process-tree/cgroup cap proof নয়। Sampler/thread/supervisor
wiring এখনও নেই; no GPU/model/server run। Offline C1-এর blocker নেই।
Next owner-directed micro-step: **C2 sampler lifecycle/tests**—single serialized
read, bounded latest slot, preserved read-start time, stop/late-publication guard,
bounded join এবং stuck sampler unknown। C3 fixed dummy integration পরে পৃথক step।
Current completion C2/C3 implementation বা live/new phase নিজে থেকে শুরু করে না।
