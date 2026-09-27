# Local/mock remaining-gap review

2026-09-27। Read-only review সম্পন্ন; source/test পরিবর্তন নয়।

## পর্যালোচিত slice ও ফল

| Scope | Evidence | সিদ্ধান্ত |
| --- | --- | --- |
| Budget/reservation/dispatch/receipt | [Offline acceptance](gpu-offline-acceptance.md) | Completed; পুনরায় implementation নয় |
| Deadline/restart admission | [Durable acceptance](gpu-durable-offline-acceptance.md) | Local slice completed; cooperative সীমা বহাল |
| Cleanup observation/report | [Report checkpoint](gpu-session-report-checkpoint.md); 201 tests PASS | Historical saved/unknown semantics আছে; নতুন CLI/UI ধরে নেওয়া নয় |
| Dispatch + cleanup persistence failure | নিচের reproduction | একটি error-contract bug নির্বাচিত |
| Real runtime/spend/HTTP wiring | Exact mock types only | Deferred production work; এই fix-এর scope নয় |

এটি accumulated local slice review; পূর্ণ repo/security audit বা নতুন live-launch
readiness review নয়। [Launch review](gpu-launch-readiness-review.md)-এর deferred
quote/private pull/operator/inference gates অপরিবর্তিত; pricing refresh নয়।

## নির্বাচিত gap: double failure-এ original dispatch error

[Session source](../animation_studio/providers/gpu_mock_session.py)-এর `submit()`
exception handler-এ `_cleanup()`-এর পর bare raise আছে। Durable subclass-এর
[cleanup](../animation_studio/providers/gpu_durable_session.py) intent/result write
বা fsync failure-এ exception দেয়। তখন bare raise পৌঁছায় না।
[Runtime scope](gpu-runtime-integration-scope.md)-এ original failure propagate করার
contract আছে; single-failure tests সেটি verify করলেও double failure coverage নেই।

Temporary ledger ও exact mock components দিয়ে reproduction:

- Provider fixture `GPUProviderError('timeout', ...)` দেয়; reservation আছে।
- পরের cleanup intent write fixture `OSError` দেয়।
- Caller top-level `OSError` পায়; original GPUProviderError কেবল `__context__`-এ।
  Error পুরো হারায় না, কিন্তু caller-এর provider-error handling bypass হয়।
- Session closed, cleanup_result None, backend calls শূন্য। Temporary data সরানো
  হয়েছে; source/test/environment edit বা network call হয়নি।

## পরের অনুমোদিত একক micro-step

শুধু combined dispatch/cleanup failure propagation fix। Original dispatch exception
একই instance হিসেবে top-level-এ থাকবে; cleanup failure explicit exception chaining-এ
inspectable থাকবে। কোনো error swallow/log-only success নয়। Cleanup successful হলে
আগের behavior বহাল। Standalone finish/recover failure নিজস্ব error-ই দেবে।
Ledger schema/retries/cleanup cap/admission policy/provider wiring বদলাবে না।

Pass checks:

1. Provider timeout + cleanup intent-write failure: original identity/code retained;
   cleanup error inspectable; admission closed; backend cleanup call শূন্য।
2. Provider timeout + cleanup result-write failure: original error retained; cleanup
   error inspectable; consumed attempt/unknown observation; false complete নয়।
3. Reservation/receipt persistence failure + cleanup persistence failure: দুটো error
   আলাদাভাবে inspectable; automatic submit retry নয়।
4. পরের submit blocked; successful cleanup/original-error propagation ও standalone
   finish/recover write-failure regression PASS।

## Checks, সীমা ও authorization

Local reproduction PASS; source/test/requirements consistency, links, plan drift,
whitespace ও RESUME length PASS। আগের 201-test evidence retained; docs-only review
বলে regression rerun নয়। Review blocker নেই; next fix existing Phase 4 local/mock
authorization-এর মধ্যে। নতুন phase নয়। Paid GPU/payment/quote ও CPU experiments
স্থগিত। No install/download/cloud call/commit; production API/UI/DB অক্ষত।
পূর্ণ Phase 3/4 acceptance অসম্পূর্ণ।
