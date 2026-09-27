# Dispatch ও cleanup double-failure fix

2026-09-27। [নির্বাচিত gap](gpu-mock-remaining-gap-review.md)-এর fix সম্পন্ন।

[MockRenderSession.submit](../animation_studio/providers/gpu_mock_session.py)-এ
cleanup exception হলে original dispatch exception একই instance হিসেবে re-raise হয়;
cleanup exception explicit `__cause__`-এ পাওয়া যায়। Cleanup successful হলে original
bare raise বহাল। Standalone finish/recover, retry/cap/admission ও schema অপরিবর্তিত।
KeyboardInterrupt/SystemExit-এর মতো BaseException interception যোগ করা হয়নি।

## Checks

[Durable session tests](../tests/test_gpu_durable_session.py)-এ ছয়টি regression:
provider timeout/reservation write/receipt write failure × cleanup intent/result write
failure। Fix-এর আগে ছয়টি FAIL; fix-এর পরে ছয়টি PASS। Primary identity/provider code,
secondary cause, closed admission, no retry, reservation/unknown receipt, consumed
cleanup attempt এবং false-complete না হওয়ার checks আছে।

Relevant report/ledger/durable session/observation/acceptance/mock session/dispatch/
receipt/offline/lifecycle/budget/provider suite: **207 PASS**। Test lint সংশোধনের পর
ছয়টি targeted test আবার PASS। Ruff lint/format, plan drift, links, whitespace ও
RESUME length PASS। Existing interpreter `.venv/bin/python -m pytest` ব্যবহার হয়েছে।

## সীমা ও পরের কাজ

Intent write failure-এ in-memory admission closed হলেও persisted closed flag পুরোনো
থাকতে পারে; result write failure-এ saved observation unknown। কোনো successful
cleanup result বানানো হয়নি। Exception chain caller-এর জন্য; নতুন logging/persistence
নয়। Local/mock সীমা বহাল; real GPU/billing/inference acceptance deferred। Blocker নেই।

পরের অনুমোদিত local micro-step: completed mock slice-এর evidence handoff সংক্ষেপে
একত্র করা—known deferred gates ও remaining authorized work স্পষ্ট করা। নতুন feature,
completed tests restart বা broad launch-readiness review নয়। No install/download/
cloud call/payment/commit; production API/UI/DB অপরিবর্তিত।
