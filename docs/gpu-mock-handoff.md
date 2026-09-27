# Phase 4 local/mock evidence handoff

2026-09-27। বর্তমান অনুমোদিত local/mock follow-up ধারার handoff সম্পন্ন।
এটি পূর্ণ Phase 4 completion, live launch approval বা পুরো repo audit নয়।

## সম্পন্ন কাজ ও evidence

| কাজ | Evidence | ফলের অর্থ |
| --- | --- | --- |
| 4.1–4.6 interface/HTTP/retry/budget/secrets/RunPod skeleton | [বর্তমান status/history](current-build-status.md) | Local/mock steps complete; live dispatch acceptance নয় |
| Durable attempt reservation, dispatch ও receipt | [Offline acceptance](gpu-offline-acceptance.md) | Restart-এ consumed slot retained; ambiguous outcome automatic resubmit নয় |
| Fixed deadline, closed admission, durable restart | [Durable acceptance](gpu-durable-offline-acceptance.md) | Recovery নতুন submit বন্ধ রাখে; hard remote runtime cap নয় |
| Saved cleanup observation | [Observation checkpoint](gpu-cleanup-observation-checkpoint.md) | Latest-attempt association ও bounded recovery; live billing proof নয় |
| Read-only session report | [Report checkpoint](gpu-session-report-checkpoint.md) | Locks/writes/cleanup ছাড়া historical saved/unknown ফল |
| Dispatch + cleanup double failure | [Fix checkpoint](gpu-double-failure-checkpoint.md) | Primary exception identity/code retained; cleanup error explicit cause |
| Separate cleanup supervisor | [Supervisor checkpoint](gpu-supervisor-checkpoint.md) | Hung local fixture child bounded; remote compute shutdown নয় |

সর্বশেষ সংশ্লিষ্ট 12-file regression suite **207 PASS**; নতুন ছয়টি failure test
fix-এর আগে FAIL, পরে PASS। এটি উপরের dispatch/session/report slice-এর evidence;
সমস্ত GPU tests/full application suite-এর একত্র total নয়। Supervisor-এর পৃথক
126-test evidence retained; overlapping counts যোগ করে নতুন total করা যাবে না।
এই handoff-এ source বদলায়নি, তাই completed tests পুনরায় চালানো হয়নি।

## কার্যকর সীমা

- Durable guards exact local mock components-এর জন্য। Standalone APIs ও production
  orchestration এই session guard-এর অন্তর্ভুক্ত নয়; live idempotency/spend wiring বাকি।
- Deadline caller-driven; blocking operation interrupt বা host power/network loss
  protection নয়। Recovery submit বন্ধ রাখে, automatic model/job resume করে না।
- Receipt historical acceptance; current execution/completion নয়। Saved cleanup
  result historical; retained/unknown storage-কে cleared বা billing-zero বলা নয়।
- Compute-only estimate-এ storage/egress/tax নেই। Current quote পাওয়া যায়নি;
  historical launch draft executable cost preview নয়।
- Intent write failure-এ persisted closed flag পুরোনো থাকতে পারে; caller session
  বন্ধ থাকে। Result write failure-এ outcome unknown; false success তৈরি হয় না।
- Production API/UI/DB/schema অক্ষত; install/download/commit করা হয়নি। Existing
  dirty/untracked work সংরক্ষিত; এই handoff Git commit বা release নয়।

## Deferred gates ও পুনরায় শুরুর শর্ত

| বাকি কাজ | বর্তমান অবস্থা / শর্ত |
| --- | --- |
| Phase 3 real planner acceptance | Real adapter/test-set, Bengali/duration/traits/repeatability/lifecycle evidence বাকি; owner-এর CPU experiment স্থগিত সিদ্ধান্ত বহাল |
| 4.7 final cost/action preview | Quote/payment handoff স্থগিত; owner এটি পুনরায় চাইলে exact configuration/quote/budget সংগ্রহের কাজ ফিরবে |
| 4.8 authenticated real GPU health | Applicable phase-order prerequisite বা explicit scoped revision, private pull/operator path, final preview ও paid approval দরকার |
| 4.9 tiny inference | Health-only image inference দেয় না; model/runtime/artifact evidence ও পৃথক bounded execution scope বাকি |
| 4.10 compute/storage verification | Approved real session-এর পরে actual resource/storage observation প্রয়োজন; mock outcome যথেষ্ট নয় |
| নতুন phase | Prerequisites ও owner approval ছাড়া শুরু নয় |

Owner dashboard access ইতিমধ্যে নিশ্চিত করেছেন; deployment/payment status অনুমান
নয়। [Attended proposal](gpu-attended-health-proposal.md)-এর পুরোনো access-pending
বাক্যের চেয়ে বর্তমান RESUME status প্রযোজ্য; একই access/server প্রশ্ন পুনরায় নয়।
Secrets চাইবে না। Paid GPU/billable resource বা >2 GB model download-এর জন্য
পৃথক explicit approval প্রয়োজন; সব dependency install owner করবেন।

## পরের কাজ ও authorization

এই bounded local/mock ধারায় নির্দিষ্ট pending implementation আর তালিকাভুক্ত নেই।
আগের local/mock authorization বহাল, কিন্তু নতুন feature/review loop নিজে থেকে
তৈরি করার কারণ নয়। নতুন concrete bug/evidence এলে তার একক scope বিবেচনা করা যাবে।
Plan-order-এর পরের অসম্পূর্ণ ধাপ 4.7 final preview; বর্তমানে owner-deferred।
সাধারণ “পরের কাজ” স্থগিত quote/model experiment বা নতুন phase চালুর অনুমতি নয়;
owner নতুন local scope বা deferred কাজ পুনরারম্ভের নির্দেশ দিলে পরের step নির্ধারিত হবে।

Checks: evidence/status/authorization consistency, local links, plan excerpt drift,
whitespace ও RESUME length PASS। Handoff blocker নেই; real acceptance gates বাকি।
