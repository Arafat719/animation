# Phase 5.4 — A3 offline resource admission/recheck

2026-10-10। Owner next-work নির্দেশে A3 acceptance সম্পন্ন। Session-এর existing
resource evaluator integration ও fixture ইতিমধ্যে source-এ ছিল; পুনরায় implementation
না করে 39 নতুন regression cases, API contract docstring ও checkpoint যোগ করা হয়েছে।

## আচরণ ও evidence

OfflineComfyAdmission-এর explicit run_started_at/resource_sample একই caller-owned
monotonic clock domain ব্যবহার করে। Existing callback একই job lock-এর মধ্যে
inventory preflight-এর আগে ও পরে capability admission এবং resource evaluation করে;
তারপরই durable intent/submit। Sample/start নিজে তৈরি বা refresh হয় না।
Missing/stale/invalid sample, context/worker/device mismatch, RAM/host reserve/VRAM
threshold এবং expired run deadline-এ bounded resource_reasons সহ failure;
প্রথম check-এ zero dispatch, দ্বিতীয় check-এ inventory GET-only, কোনো intent/POST নয়।
Malformed object/extra fields ও invalid start resource_input_invalid দেয়।

নতুন tests উভয় check-এ failure matrix, preflight চলাকালে sample ageing, exact fresh
boundary, limit-এর ঠিক নিচে success এবং simultaneous breaches-এর স্থির reason order
যাচাই করে। Existing regressions same-lock ordering, fixture provenance, no-resubmit,
GET-only admission-independent recovery ও durable cancellation যাচাই করে।

## Checks

Baseline session/resource suites: **113 PASS**। নতুন 39 cases-সহ targeted **152 PASS**;
final combined **348 PASS**:

```sh
.venv/bin/python -m pytest -q tests/test_comfy_offline_session.py tests/test_comfy_resource_guard.py tests/test_comfy_admission.py tests/test_comfy_v2_executor.py tests/test_comfy_preflight.py tests/test_comfy_auth_workflow.py tests/test_comfy_cancel_crash.py tests/test_comfy_transport_composition.py
```

Ruff/check/format, plan excerpt drift, changed-doc local links, RESUME length ও
whitespace PASS। Network/DNS নিষিদ্ধ fixture tests; কোনো install/model/GPU/server run নয়।
Schema বা feature requirements বদলায়নি; migration/master edit প্রয়োজন নেই।

## সীমা ও next

A3 fixture acceptance সম্পূর্ণ; real telemetry collection/enforcement, shared hard
execution deadline, target supervision এবং live durable composition এখনও বাকি।
Admission-এ deadline evaluation পরবর্তী HTTP execution-এর hard timeout নয়।
Caller clock-domain identity resource sample-এ আলাদাভাবে attest করা নেই; caller-এর
দায়িত্ব, restart-এ পুরোনো sample relabel নয়। Last check/POST target-atomic নয়।
Real 5.4 GPU ছাড়া blocked; unchanged probe নয়। Next proposed owner-directed micro-step:
remaining offline/live prerequisite gap review, যাতে completed acceptance পুনরায় না হয়।
এই checkpoint পরবর্তী implementation/live/paid কাজের approval নয়।
