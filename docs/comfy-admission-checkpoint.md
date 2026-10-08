# Phase 5.4 — A1 pure offline admission evaluator

2026-10-08। Owner next-work নির্দেশে [admission contract](comfy-admission-contract.md)
এর A1 source/tests সম্পন্ন। Production evidence collector/consumer বা live dispatch নয়।

## Implementation

[Source](../animation_studio/providers/comfy_admission.py): strict/frozen observation
schema, maximum five-observation immutable tuple এবং pure evaluate_admission।
Existing ComfyExecutionContext, ComfySupervisionPolicy ও finite-time validation
reuse; policy-এর সব validated field sorted canonical JSON/SHA256 দিয়ে bind হয়।
New persistence/schema migration নেই; নতুন executor/store/transport নেই।

Required capabilities: runtime_native, model_identity, endpoint_auth_routes,
worker_ownership, resource_supervision। সবগুলো exactly once passed না হলে deny।
প্রতিটি observation expected context/worker/device/policy/source/clock session-এর
সঙ্গে মেলে; missing/failed/unknown/duplicate/invalid/mismatched evidence deny।
Checked-at future হলে deny; age > explicit max_age হলে stale, equality গ্রহণযোগ্য।
Same-clock session canonical UUID caller দেন; restart-এ নতুন UUID caller-এর দায়িত্ব।
Evaluator clock পড়ে না, wall-clock budget reset বা actual process identity check নয়।

Fixture source শুধু mock-context evaluation-এ allow; target claims live context
চায়। Mixed sources deny। Output frozen action/source/bounded reason codes;
invalid top-level input source unknown। Synthetic target-claim test actual target
measurement নয়। `allow` কেবল supplied claims-এর consistency: evidence hash lookup,
verification, freshness of actual measurement, worker stop বা GPU readiness proof নয়।
No executor decision consume করে; existing live workflow gates intact।

Bypassed model_copy/model_construct revalidate হয়। Initial test-এ model_dump
unknown injected fields বাদ দেওয়ার gap পাওয়া যায়; raw field mapping validate করে
ঠিক করা হয়েছে, যাতে extra fields reject হয় ও malformed serializer warning না আসে।
Errors/results-এ untrusted values বা secrets echo হয় না। Direct schema ValidationError
caller log করার আগে sanitize করবেন; evaluator-এর public result bounded।

## Checks

Relevant unchanged identity/policy/resource baseline **282 PASS**।
[New tests](../tests/test_comfy_admission.py): **85 cases**। Final combined **460 PASS**:

```sh
.venv/bin/python -m pytest -q tests/test_comfy_admission.py tests/test_comfy_resource_guard.py tests/test_comfy_supervision.py tests/test_comfy_identity.py tests/test_comfy_transport_composition.py tests/test_comfy_storage.py tests/test_comfy_offline_session.py
```

All-required fixture/target claims, every capability/context/policy field, missing/
failed/unknown/duplicate, source isolation, clock/session/age bounds, malformed/
forged nested models, deterministic reasons, no socket/DNS/file/process I/O এবং
unchanged mock executor/live-storage gate regressions PASS। Ruff/format, plan drift,
docs links/RESUME length ও whitespace PASS। No install/server/model/GPU/network run।
Existing unrelated dirty files preserved; commit নয়।

## Next ও limitations

A1 complete; actual live admission ও full L4/5.4 incomplete। Available target-এর
runtime/GPU preflight এখনও blocked; একই hardware probe পুনরায় নয়।
Next proposed A2: offline session-এ fixture-only mandatory admission check ও
preflight-এর পরে freshness recheck, intent-এর আগে deny/no-POST tests। এটি আলাদা
একক integration scope; পরবর্তী owner next-work নির্দেশে শুরু করা যাবে। Runtime
collector/target trust verification/live dispatch বা paid launch এর অন্তর্ভুক্ত নয়।
