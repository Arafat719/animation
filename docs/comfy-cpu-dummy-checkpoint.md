# Phase 5.4 — C3 fixed CPU dummy integration

2026-10-08। Owner next-work নির্দেশে [CPU contract](comfy-cpu-supervision-contract.md)-এর
C3 সম্পন্ন। Existing unfinished source সংশোধন ও integration acceptance যাচাই।

[Source](../animation_studio/providers/comfy_cpu_dummy_integration.py) শুধু fixed
small Linux child চালায়; model/network/GPU/large allocation নয়। Ready handshake-এর
পরে owned reader + serialized sampler; first validated identity দিয়ে CPU guard।
Bootstrap একই run window consume করে, first-sample deadline পেরোলে admission নয়।
Failure reading/reader exception-এ abort; first allow-এর আগে admitted false।
RAM/reserve/staleness/run deadline guard-এ enforce; প্রথম abort reasons অপরিবর্তিত।

Parent poll exit confirm করে; normal exit-এর পরে telemetry loss-এর জন্য অপেক্ষা
বা false abort নেই। Owned direct child-এ stop, cleanup boundary-তে kill, bounded
reap; sampler join-এর আগে worker cleanup। Setup errors-এও bounded cleanup।
Deadline arithmetic spawn-এর আগে validate। Unknown sampler/worker হলে
needs_manual_cleanup; result cleanup_sampler/cleanup_child handle ধরে রাখে।
Caller-কে retained session রেখে blocked read শেষ হলে close/reap করতে হবে;
thread force-kill বা unattended production readiness দাবি নয়।

## Checks

[Tests](../tests/test_comfy_cpu_dummy_integration.py): **20 cases**। Real small child
RSS/CPU admission, low threshold abort, cooperative/ignored stop, normal early exit,
initial/post-admission hung read, exception/disappearing sample, failure statuses,
first-reason retention, invalid/live no-spawn, setup cleanup ও unrelated child isolation।
Hung fixtures finally release করে retained sampler join করেছে।

Combined **315 PASS**:

```sh
.venv/bin/python -m pytest -q tests/test_comfy_cpu_dummy_integration.py tests/test_comfy_ram_sampler.py tests/test_comfy_cpu_guard.py tests/test_comfy_ram_telemetry.py tests/test_comfy_resource_guard.py tests/test_comfy_supervision.py
```

Ruff lint/format, excerpt drift, checkpoint links/RESUME length ও whitespace PASS।
C2 baseline 295 PASS reused; C3 integration-সহ combined suite চালানো হয়েছে।

## সীমা ও next

CPU-only/direct-child RSS; VRAM/job/compute/storage unknown। Host reserve
before-spawn guarantee নেই; dummy bootstrap exception real worker-এর জন্য নয়।
OS/GIL scheduling hard real-time guarantee নেই। Durable journal/live executor
wiring এই step-এর বাইরে। GPU/model/server run বা dependency install হয়নি।
C1–C3 complete; next owner-directed readiness review দিয়ে পরবর্তী scoped কাজ
নির্ধারণ হবে। Real 5.4 GPU gate blocked; 5.5/new phase অনুমোদিত নয়।
