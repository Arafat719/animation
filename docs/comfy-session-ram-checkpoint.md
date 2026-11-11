# Phase 5.4 — D5 parent RAM admission/monitoring

2026-10-11। Owner next-work নির্দেশে D4-এর নির্ধারিত একক implementation সম্পন্ন।
Existing অসমাপ্ত source/tests সংরক্ষণ করে review ও missing failure coverage যোগ হয়েছে।

## আচরণ ও evidence

[Parent](../animation_studio/providers/comfy_session_supervisor.py) owned fixture child
spawn করে existing OwnedChildRamReader/RamSampler শুরু করে। First valid reading-এর
PID/start ticks pin করে CPU guard allow না দেওয়া পর্যন্ত startup JSON পাঠায় না।
Bootstrap window min(original run deadline, start + stale interval); missing sample,
reader failure, invalid identity, RAM/reserve rejection-এ startup বন্ধ। Partial JSON
abort হলে stdin close; full payload sent হলে আগের single stop/child cancel path।

প্রতি monitor cycle nonblocking snapshot guard-এ যায়; failed/stale/mismatched reading
পুরোনো allow দিয়ে চালানো হয় না। Confirmed child exit telemetry rejection-এর আগে
দেখা হয়। Original run/cleanup/final deadlines অপরিবর্তিত; parent HTTP cancel করে না।
Cleanup sampler stop, child kill/reap, sampler close ও pipe close independent attempts।
Blocked sampler থাকলে reaped child-ও needs_manual_cleanup; returned result ও exception
উভয়েই sampler/child handles রাখে। Primary exception অক্ষত; raw errors repr-এ নেই।

Result-এর ram_source=local_procfs/direct_child, sampler status/sequence, ram_admitted
ও bounded ram_reasons পৃথক। RSS/available RAM সর্বশেষ guard-allowed reading-এর মান;
এগুলো peak বা rejected reading-এর measurement নয়। Child telemetry_source=synthetic,
is_mock=True; VRAM unknown। Caller explicit budget দেন; tests small child-এর জন্য
512 MiB budget ব্যবহার করে। কোনো allocation stress/model load হয়নি।

## Checks

Existing D5 work-এর baseline session suite: 42 PASS। অতিরিক্ত 7 failure cases:
bootstrap reader exception/unavailable/invalid/identity mismatch, first-sample cancel,
sampler snapshot/close exception। Final combined regression: **515 PASS** (97.52s); session suite এখন 49 cases।
Ruff check/format, docs links/RESUME length, plan excerpt drift ও whitespace PASS।
[Tests](../tests/test_comfy_session_supervisor.py) normal fixture PNG/local RAM evidence,
RAM/reserve equality rejection, wrong PID/ticks, blocked/stale sampler, accepted journal
preservation/single cancel, partial startup cancellation ও retained cleanup পরীক্ষা করে।
Existing D3 GET-only recovery, unrelated sentinel, timeout/IPC/unknown exit regressions
একসঙ্গে চালানো হয়েছে। Network/DNS guards বহাল; real GPU/server test নয়।

## সীমা ও next

এটি local fixed direct-child monitoring; process launch/import allocation hard cap,
OS memory enforcement, descendants/remote worker বা target VRAM coverage নয়।
Real image 5.4 ও native/GPU preflight hardware absence-এ blocked; authorization বহাল,
পরিবর্তিত environment ছাড়া repeated probe নয়। Live/paid/new phase/5.5 অনুমোদিত নয়।
D5 শেষে নতুন offline implementation scope নির্ধারিত নেই; owner-এর পরবর্তী নির্দেশ
প্রয়োজন। Existing schema/feature requirements বদলায়নি; master/excerpts edit নয়।

চালানো combined command:

```sh
.venv/bin/python -m pytest -q tests/test_comfy_session_supervisor.py tests/test_comfy_offline_session.py tests/test_comfy_v2_executor.py tests/test_comfy_cancel_crash.py tests/test_comfy_cpu_dummy_integration.py tests/test_comfy_supervised_recovery.py tests/test_comfy_ram_sampler.py tests/test_comfy_ram_telemetry.py tests/test_comfy_cpu_guard.py tests/test_comfy_resource_guard.py tests/test_comfy_admission.py
```
