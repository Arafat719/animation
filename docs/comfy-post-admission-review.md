# Phase 5.4 — A3-পরবর্তী offline/live gap review

2026-10-10। Owner next-work নির্দেশে একক docs-only review সম্পন্ন।
A1–A3 completed acceptance পুনরায় নয়; real 5.4 ও পূর্ণ L4 অসম্পূর্ণ।

## বর্তমান সিদ্ধান্ত

| অংশ | সম্পন্ন evidence | অবশিষ্ট gap |
| --- | --- | --- |
| Admission | A1 pure capability decisions; A2 same-lock pre/post-preflight checks; A3 resource failure/recheck, combined 348 PASS | Fixture claims actual target evidence নয়; collector/trust binding বাকি |
| Resource/time | Mock resource evaluator deadlines হিসাব করে; session admission-এ ব্যবহার করে | Run deadline HTTP preflight/submit/poll/view-তে পৌঁছায় না; চলমান resource monitoring নেই |
| Ownership | C3 fixed owned CPU child ও exceptional cleanup acceptance | Selected Comfy worker/process tree/GPU ownership ও independent supervision বাকি |
| Live path | L2 transport, L4.1 generation store, L4.2 supervision store standalone support | HTTP/session/durable composition এখনও mock-only; live integration ও target TLS/auth/routes unverified |
| Real output | PNG validation এবং mock provenance acceptance | GPU/native operation, target model registration/load, real image ও human review বাকি |

[Session](../animation_studio/providers/comfy_offline_session.py)-এ resource decision-এর
run_deadline return/forward হয় না। [Durable executor](../animation_studio/providers/comfy_v2_executor.py)
preflight ও execute আলাদাভাবে ডাকে। [HTTP executor](../animation_studio/providers/comfy_http.py)
দুই entry point-এ `time.monotonic() + timeout_seconds` বানায়; accepted timeout cleanup
আবার পৃথক পাঁচ সেকেন্ড পায়। তাই admission PASS মানে combined execution budget নয়।
এটি source review finding; নতুন timeout experiment চালানো হয়নি।

[RAM reader](../animation_studio/providers/comfy_ram_telemetry.py) direct-child-only,
VRAM unknown। তাকে remote supervisor হিসেবে ব্যবহার করা যাবে না। A3-এর static
sample freshness checks চলমান allocation/spike enforce করে না। Standalone live
transport network করতে পারে; workflow gate package-wide network prohibition নয়।

## পরের একক micro-step: D1 shared cooperative deadline integration

GPU ছাড়াই অবশিষ্ট নির্দিষ্ট কাজ: existing offline session-এর এক absolute run deadline
preflight → submit → polling → download পর্যন্ত পৌঁছানো, deterministic fixture tests-সহ।
এটি নতুন evaluator, worker supervisor বা live factory নয়। পরবর্তী owner next-work
নির্দেশে এই সীমিত implementation শুরু করা যাবে; এই turn review-only।

Implementation contract:

- Existing resource evaluator-এর run/cleanup/final deadlines reuse; execute attempt-এর
  শুরুতে policy/start bound করে immutable ceilings রাখবে। Recheck নতুন sample যাচাই
  করতে পারবে, কিন্তু start/policy replacement দিয়ে run budget বাড়াতে পারবে না।
- Session/admission/HTTP/transport-এ এক monotonic clock domain নিশ্চিত করতে হবে;
  fixture clock 100-কে host monotonic clock-এর সঙ্গে তুলনা নয়। Clock failure,
  nonfinite/backward time bounded failure; default real monotonic আচরণ বহাল।
- Generation-এর প্রতিটি HTTP stage original absolute run ceiling মানবে; existing
  timeout_seconds আরও ছোট cap হতে পারে, নতুন stage budget ceiling বাড়াবে না।
  Chunk checks/poll wait একই remaining budget ব্যবহার করবে।
- Intent-এর আগে deadline exhausted হলে no intent/POST। Intent লেখার পরে বা submit-এর
  অনিশ্চিত failure-এ intent retained/no resubmit; receipt ছাড়া guessed cancel নয়।
- Accepted timeout/cancel-এ existing durable single-cancel owner বহাল; cleanup run
  expiry-তে suppressed নয়, তবে `min(now + 5, original cleanup_deadline)`-এ bounded।
  Cleanup allowance exhausted হলে no dispatch/unknown; primary failure ও durable
  attempt semantics বজায় থাকবে। Final/reap deadline data process reap-এর proof নয়।
- Recovery পুরোনো generation monotonic budget reuse করবে না: fresh bounded GET-only,
  admission-independent, no submit/cancel। Legacy raw mock callers-এর default timeout
  contract এবং existing cancellation tests বজায় রাখবে। Schema migration প্রয়োজন নেই।

Pass checks (synthetic clock/MockTransport; socket/DNS নিষিদ্ধ):

1. Preflight time consume করলে submit/poll/view remaining budget কমে; reset নয়।
2. Initial expiry, inventory চলাকালে expiry এবং pre-intent expiry-এ no intent/POST;
   intent-after-write expiry-এ retained ambiguous journal/no automatic retry।
3. Accepted timeout-এ durable cancel সর্বোচ্চ একবার; cleanup ceiling অতিক্রম নয়;
   receipt write failure/unknown receipt/recovery আগের semantics রাখে।
4. Clock mismatch/failure/reversal/nonfinite ও mid-preflight policy/start replacement
   budget bypass করতে পারে না; failure text bounded।
5. Existing success/mock provenance, A1–A3 rejection, raw legacy cancellation,
   GET-only restart recovery ও transport lifetime regressions PASS।

D1 cooperative deadline propagation মাত্র। Synchronous blocking I/O, native decode,
OS scheduling বা worker execution-এর hard wall-clock bound দাবি করা যাবে না।
Independent target supervisor এবং actual telemetry পরবর্তী পৃথক scope।

## Blocker, checks ও authorization

Real GPU environment নেই; existing-authorized native preflight blocked। একই probe,
install/model download বা paid launch নয়। Target নির্বাচিত হলে runtime/model/TLS/
worker ownership evidence ও live composition আলাদাভাবে যাচাই করতে হবে। 5.5/new phase
অনুমোদিত নয়। D1-এর জন্য GPU প্রয়োজন নেই; এই review-এ source/test edit হয়নি।

A3-এর 348 PASS evidence reused; app tests rerun প্রয়োজন হয়নি। Changed-doc local links,
RESUME <60 lines, plan excerpt drift ও whitespace PASS। Requirements অপরিবর্তিত;
master edit/regeneration প্রয়োজন নেই। আগের dirty A3 files সংরক্ষিত; commit নয়।

## D1 update — 2026-10-10

Owner নির্দেশে [D1 integration](comfy-shared-deadline-checkpoint.md) সম্পন্ন; 598 tests
PASS। উপরের reset/source finding historical; shared cooperative run/cleanup ceiling
এখন যুক্ত। Hard independent supervision ও target evidence এখনও বাকি।
