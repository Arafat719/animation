# Phase 5.4 — cancellation process-crash acceptance

2026-10-04। Owner next-work নির্দেশে এক test-only micro-step সম্পন্ন।

## Evidence

New `test_comfy_cancel_crash.py` real child process-এ mock executor চালিয়ে
`os._exit(73)` দিয়ে চারটি deterministic boundary-তে cleanup/finally ছাড়াই exit:

| Boundary | Persisted phase | মোট cancel dispatch |
| --- | --- | --- |
| Initial sidecar fsync-এর পরে | not_requested / attempt 0 | 0 |
| Intent fsync-এর পরে, cancel-এর আগে | intent / attempt 1 | 0 |
| Cancel acknowledgement পাওয়া, observation লেখার আগে | intent / attempt 1 | 1 |
| Observed sidecar fsync-এর পরে | observed / attempt 1 | 1 |

Mock request ledger প্রতিটি request file flush/fsync করে রাখে। প্রতি case-এ
দুটি আলাদা fresh process দিয়ে duplicate execute ও explicit cleanup-handler
re-entry reject, accepted GET-only recovery ও generation/sidecar byte preservation
যাচাই। প্রতিটি recovery history/view পড়ে; কোনো নতুন POST নয়। Lock process exit-এ
release হয়। Socket/DNS forbidden; fixture server নতুন process-এ পুনর্গঠিত।

## Checks

`.venv/bin/python -m pytest -q tests/test_comfy_cancel_crash.py
 tests/test_comfy_v2_executor.py tests/test_comfy_supervision_storage.py`
(এক লাইনে): **56 PASS**, including 4 new subprocess scenarios। Ruff lint/format,
docs links/RESUME length/plan drift/whitespace PASS। Previous unchanged full
671 PASS baseline reused; total suites overlap, counts যোগ করা হয়নি।

## Limits / next

এটি abrupt process-exit evidence, host power-loss/filesystem durability বা real
remote server persistence test নয়। Mock request ledger dispatch observation;
remote compute stopped proof নয়। No production source changes, runtime install,
model load, network/GPU/paid action। Intent বা initial record রেখে crash হলে
cleanup automatic retry হয় না; outcome unknown/operator follow-up বহাল।

এই cancellation chain-এর schema/storage/integration/crash acceptance সম্পন্ন;
একই কাজ restart করার প্রয়োজন নেই। পরের execution কাজ owner-installed runtime/GPU
prerequisites পেলে existing authorized native preflight; এখন deferred। Resource
telemetry/admission এবং outer process supervision এখনও পৃথক unresolved scope;
এই test completion তাদের implementation বা live enable-এর অনুমোদন নয়।
