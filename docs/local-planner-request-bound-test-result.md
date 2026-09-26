# Request-bound one-call test — ফল

2026-09-22। **অনুমোদিত test সম্পন্ন: acceptance FAIL — generation timeout।**
Owner “ok porer kaj koro” বলে [exact proposal](local-planner-request-bound-test-proposal.md)
কার্যকর করতে বলেছেন। এক generation call; retry/repair ০।

## ফল ও diagnostic সীমা

300.001s-এ deadline guard থামিয়েছে। 1,648-character partial JSON পঞ্চম shot-এর
`e` object-এর শুরুতে থেমেছে; finish reason নেই। JSON parser incomplete content
প্রত্যাখ্যান করে। Full policy/custody/StoryPlan validation ও candidate assembly হয়নি।

Raw prefix-এ concrete riverside market, relieved/anxious mood ও golden-hour light
আছে; completed event objects-এ `notebook` ID আছে। এগুলো partial observations,
whole-plan policy PASS বা runtime const enforcement-এর পূর্ণ প্রমাণ নয়। Runtime
schema গ্রহণ করে generation শুরু করেছে; unsupported-schema error পাওয়া যায়নি।

আগের narrative/custody সমস্যাও prefix-এ আছে: initial `o.holder=c1` (Courier),
প্রথম event আবার pickup c1 from=null। Contract-এ pickup-এর আগে holder=null প্রয়োজন।
প্রথম action “Courier approaches the market with a notebook in hand”—pickup বর্ণনা
নয়। এটি Codex-এর unmodified partial-text diagnostic; corrected JSON তৈরি বা
validator bypass করে hypothetical PASS দাবি করা হয়নি। পূর্ণ narrative verdict অমাপা।

## Config ও মাপা evidence

Verified Qwen3-4B Q4_K_M / llama.cpp b10964 পুনর্ব্যবহার; asset size/mtime মিলে গেছে,
checksum evidence আগেরটি; নতুন download/rehash নয়। Exact request 4,588 bytes,
schema 1,985 bytes; policy hash unchanged। CPU ৪ threads, GPU/offload ০, এক slot,
8192 context; reasoning off; seed/sampling unchanged; 768 output cap, 300s deadline।

| Measurement | Observed |
| --- | --- |
| Model load | 13.66s |
| Generation | 300.001s; timeout |
| First content | 44.37s |
| Content | 1,648 characters; invalid incomplete JSON |
| Final usage / prompt/decode totals | unavailable; stream অসম্পূর্ণ |
| Last runtime decode log | n_gen=569, ~2.22 tokens/s; final usage নয় |
| Lifecycle | 314.74s |
| Peak sampled RSS | 5,553,572 KiB ≈ 5.30 GiB |
| Minimum available RAM | 8,535,296 KiB ≈ 8.14 GiB |
| Process swap / memory stop | ০ / নেই |
| Experiment directory | 2,585,243,643 bytes; 6 GiB cap-এর নিচে |

Memory monitor-এর resource_stop null; timeout main deadline guard থেকে এসেছে।
First-content time prompt-eval metric নয়। Final token totals বা speedup অনুমান নয়।

## Checks ও cleanup

নতুন harness-এর **চার offline test methods ও compile PASS**: pending review,
REQUEST_OBJECT code/path, incomplete/token/resource/thinking rejection ও one-call
marker। Existing policy ৬ tests/17 fixtures baseline পুনর্ব্যবহার; rerun নয়।

Localhost-only ephemeral auth/CORS; unauthenticated models endpoint → 401। Runtime
exit 0; connection check ও independent `/proc/net/tcp*` LISTEN check-এ port বন্ধ।
Candidate file নেই। Ignored `data/planner-smoke/request-bound-run-v1/`-এ exact
request/harness/tests, authorization/preflight/hash, raw events/content, metrics,
partial diagnostic ও cleanup evidence সংরক্ষিত। পুরোনো policy/validators/evidence অক্ষত।

Document links, RESUME size, scope/status, plan drift ও whitespace checks PASS।
Production source/API/DB/UI/master অপরিবর্তিত; full app tests নয়; commit হয়নি।

## সিদ্ধান্ত ও next step

এই CPU/model path বর্তমান single-call 300s budget-এ এখনও valid accepted plan দেয়নি।
এতে সব configuration/model অসমর্থ প্রমাণ হয় না; কিন্তু আবার blind prompt/contract
loop-এর যথেষ্ট ভিত্তিও নেই। Concrete scene এসেছে, full output আসেনি এবং partial
custody/action mismatch বহাল—শুধু timeout বাড়ালে quality সমাধান নিশ্চিত নয়।

পরবর্তী bounded কাজ: existing experiments একত্রে **owner suitability review**—এই
path স্থগিত রাখা বা আলাদা বিকল্পের proposal বিবেচনার evidence/ব্যয়/সীমা উপস্থাপন।
Review preparation অনুমোদন pending। Automatic rerun, model switch/download, larger
budget, paid GPU বা 3.10 adapter নয়। Phase 3 real-adapter gate ও Bengali/বড় duration
acceptance অসম্পূর্ণ।
