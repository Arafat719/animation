# Phase 5.4 — C2 RAM sampler lifecycle

2026-10-08। Owner next-work নির্দেশে [CPU contract](comfy-cpu-supervision-contract.md)-এর
C2 সম্পন্ন। Existing unfinished sampler/source tests যাচাই ও সংশোধন করা হয়েছে।

[Sampler](../animation_studio/providers/comfy_ram_sampler.py): one-shot session,
এক serialized daemon thread, সর্বোচ্চ একটি admitted read ও bounded latest slot।
Reader-এর read-start timestamp অপরিবর্তিত; snapshot I/O completion-এর জন্য অপেক্ষা
করে না। Stop-এর পরে নতুন admission ও late reading/exception publication বন্ধ।
Interval wait stop event-এ জাগে; restart নেই। Reader exception bounded error code
দিয়ে failed হয়, arbitrary message প্রকাশ নয়; terminal failure reading retry হয় না।

Close absolute monotonic deadline-এর remaining budget পর্যন্ত join করে। Read আটকে
থাকলে status unknown: caller needs_manual_cleanup report করবে ও session রাখবে;
thread force-kill/fully-closed দাবি নয়। Lock/OS scheduling hard real-time guarantee
নয়; stop-এর আগে admitted call শেষ হতে পারে। CPU guard sample fields/freshness যাচাই
করবে; এই step-এ supervisor enforcement/wiring নেই।

## Checks

[Sampler tests](../tests/test_comfy_ram_sampler.py): 22 cases; serialized read/latest
slot, delayed timestamp, missing initial reading, bounded close with past/current/
future deadline, late result ও exception suppression, interval stop, terminal reader
failure, invalid input, start failure ও no restart। Blocked fixtures শেষে release/join।
Baseline relevant 293 PASS; final combined **295 PASS**:

```sh
.venv/bin/python -m pytest -q tests/test_comfy_ram_sampler.py tests/test_comfy_cpu_guard.py tests/test_comfy_ram_telemetry.py tests/test_comfy_resource_guard.py tests/test_comfy_supervision.py
```

Ruff lint/format, plan excerpt drift, document links/RESUME length ও whitespace PASS।
Offline C2 blocker নেই; GPU/model/server run বা dependency install হয়নি।
Next owner-directed micro-step **C3 fixed dummy integration**; এই turn-এ শুরু নয়।
