# Phase 5.4 — L1 pure request-policy validator

2026-10-08। Owner next-work নির্দেশে [transport contract](comfy-live-transport-contract.md)
এর L1 সম্পন্ন। [Source](../animation_studio/providers/comfy_request_policy.py)
canonical_origin reuse করে normalized selected HTTPS origin ফেরায়; narrow relative
route/method/payload/view parameters ও finite positive numeric timeout যাচাই করে।
Bool/string/NaN/inf/overflow timeout rejected; public ImageProviderError bounded,
input echo নয়। Credential/config পুনরায় তৈরি নয়; clock/DNS/network/client নেই।

Existing mock route grammar/payload-shape semantics বজায়; এটি workflow validator
নয় এবং route ID grammar UUID semantic validation দাবি করে না। Mutable input
retain/mutate করে না; validation result reusable dispatch permit নয়—future caller
dispatch-এর সময় পুনরায় validate করবে। Private selected endpoint বৈধ।
Existing auth/executor/storage source ও mock gates অপরিবর্তিত; future composition
এই validator ব্যবহার করবে, তখন duplicate inline route checks consolidate করবে।
এখন standalone validator; runtime enforcement/TLS/live readiness দাবি নয়।

## Checks

[Tests](../tests/test_comfy_request_policy.py): **64 cases**; allowed routes, malformed
origin/route/method/payload/query, invalid numeric timeout, input mutation/revalidation,
bounded error privacy ও private selected origin। Autouse fixture socket/DNS/
httpx.Client creation নিষিদ্ধ করে। Existing unchanged auth/config/identity baseline
173 PASS reused; final combined **237 PASS**:

```sh
.venv/bin/python -m pytest -q tests/test_comfy_request_policy.py tests/test_comfy_auth.py tests/test_comfy_config.py tests/test_comfy_identity.py
```

Ruff lint/format, docs links/RESUME length, excerpt drift ও whitespace PASS।
Source schema/master requirements unchanged; install/server/network/GPU/model নেই।

## Next

Next owner-directed micro-step L2 explicit transport factory/lifecycle ও injected
offline failure tests; এই turn শুরু হয়নি। Live workflow/storage wiring ও real
TLS/server/GPU acceptance পৃথক pending gates। GPU নেই; real 5.4 blocked।
