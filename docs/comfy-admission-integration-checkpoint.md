# Phase 5.4 — A2 offline admission integration/recheck

2026-10-08। Owner next-work নির্দেশে A2 সম্পন্ন: existing offline session-এর
mandatory fixture admission ও preflight-এর পরে freshness recheck।

## পরিবর্তন

[Session](../animation_studio/providers/comfy_offline_session.py)-এ immutable
OfflineComfyAdmission bundle: policy, worker identity, caller clock-session UUID,
explicit maximum age ও observation tuple। Constructor-এ observation তৈরি/refresh
হয় না। Bundle না দিলেও session তৈরি করে recovery করা যায়, কিন্তু execute deny।
Session clock default monotonic; offline tests injected clock ব্যবহার করে। Invalid/
failed/backward clock bounded error দেয়। Caller restart-এ নতুন clock-session UUID
দেবেন; পুরোনো observation relabel নয়। Actual process attestation এখানে নেই।

[Durable executor](../animation_studio/providers/comfy_v2_executor.py)-এ optional
admission callback দুই জায়গায়, একই lock-এর মধ্যে: existing journal check →
admission → mandatory inventory preflight → admission recheck → graph/cancel
recheck → durable intent → submit/receipt। Session সব execute-এ callback দেয়;
raw legacy mock durable caller-এর optional callback compatibility বহাল। অর্থাৎ
session-এর mandatory gate package-wide live security boundary নয়।

Missing/invalid/stale/mismatched/target-source evidence অথবা clock failure-এ
no generation intent/no POST। Initial rejection-এ inventory request-ও নেই;
preflight-এর পরে rejection-এ শুধু inventory GET হয়েছে। Permanent lock file তৈরি
হতে পারে; সেটি submit intent নয়। A1-এর bounded reason codes error-এ থাকে।
Policy hash capability binding দেয়; resource telemetry measurement/enforcement
এই step যোগ করে না। Last check এবং intent/POST atomic target observation নয়।

Recovery admission/clock/preflight invoke করে না; accepted receipt থেকে GET-only,
পুরোনো sidecar/receipt অপরিবর্তিত। Existing journal execute attempt callback-এর
আগেই reject হয়; missing snapshot দিয়ে resubmit bypass করা যায় না। Session output
mock থাকে; live context/transport gate বন্ধ।

## Checks

Recent A1/L4.3 unchanged evidence reused as baseline। Initial targeted **177 PASS**;
final combined **237 PASS**, session suite **42 cases** (22 নতুন):

```sh
.venv/bin/python -m pytest -q tests/test_comfy_offline_session.py tests/test_comfy_admission.py tests/test_comfy_v2_executor.py tests/test_comfy_preflight.py tests/test_comfy_auth_workflow.py tests/test_comfy_cancel_crash.py tests/test_comfy_transport_composition.py
```

[Tests](../tests/test_comfy_offline_session.py): both checks hold job lock and precede
intent; before/after stale/future/nonfinite/backward/failing clock, changed source/
policy/context/session/missing capabilities, missing bundle, failed preflight,
last-check cancellation, admission-independent recovery, no retry ও cleanup regressions।
Network/DNS forbidden; fixture clocks/synthetic evidence। Ruff/format, excerpt
drift, docs links/RESUME length ও whitespace PASS। No source schema migration,
install/server/GPU/model/network/paid run। Existing dirty work preserved; commit নয়।

## Next ও limitations

A2 complete; full L4/5.4 ও target-backed admission incomplete। Existing cooperative
HTTP budgets hard combined deadline নয়; target collector/worker supervision বাকি।
GPU environment এখনও absent; একই probe পুনরায় নয়।
Next proposed A3: offline session-এর admission callback-এ existing mock resource
evaluator যুক্ত করে missing/stale/over-budget resource sample-এ intent/POST বন্ধ
ও preflight-এর পরে recheck। একক fixture-only scope, owner next-work নির্দেশে;
actual telemetry collection/enforcement বা live dispatch নয়।
