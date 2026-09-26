# ছোট model + CPU — এক-call test ফল

2026-09-22। Owner “porer kaj suru koro” দিয়ে [নির্দিষ্ট proposal](local-planner-small-model-proposal.md)
অনুমোদন করেছেন; acquisition ও এক-call test সম্পন্ন। **Acceptance FAIL: ROLE `$.c`**।
Generation 215.22s-এ complete JSON দিয়েছে; timeout নয়। দুইটি cast entry-এর role
`courier`, অথচ contract-এ ঠিক একজন courier ও একজন owner প্রয়োজন। Candidate assembly হয়নি।

## Acquisition ও checks

Pinned Qwen3-1.7B Q8_0 revision `90862c4b9d2787eaed51d12237eafdfe7c5f6077`;
model size **1,834,426,016 bytes**, whole-file SHA256 PASS:
`061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`।
Official pointer ও Apache-2.0 license সংরক্ষিত। এক transfer, retry/resume ০;
response-body মোট 1,834,437,695 bytes, সময় 1,533.95s ≈ 25.57 মিনিট;
1.90 GB/45 মিনিট caps মানা হয়েছে। Network wire overhead মাপা হয়নি।

নতুন acquisition/harness-এর **৭ offline test methods ও compile PASS**: acquisition
byte/time/disk/hash rejection, exact request equality ও policy/runtime hash,
one-call marker, incomplete/token/resource/thinking rejection, error code/path ও
REVIEW_REQUIRED। Existing policy ৬ methods/17 fixtures baseline reuse; rerun নয়।
Saved request-এর সঙ্গে delta শূন্য; messages/schema/sampling/policy অপরিবর্তিত।
Request 4,588 bytes/schema 1,985; llama.cpp b10964 reuse, CPU ৪ threads,
GPU/offload ০, context 8192, reasoning off, 768-token/300s caps।

## মাপা ফল

| Measurement | Observed |
| --- | --- |
| Model load | 5.50s |
| Generation end-to-end | 215.215s |
| First content | 45.683s |
| Prompt eval | 492 tokens / 45.644s |
| Decode | 692 tokens / 169.531s; runtime 4.076 tokens/s |
| Total usage / cached | 1,184 / ০ |
| Content / finish | 1,977 characters / stop; reasoning empty |
| Runtime lifecycle | 220.98s |
| Peak sampled RSS | 2,914,444 KiB ≈ 2.78 GiB |
| Minimum available RAM | 9,726,836 KiB ≈ 9.28 GiB |
| Process swap / resource stop | ০ / নেই |
| Generation calls / repair / retry | ১ / ০ / ০ |
| Experiment directory after runtime | 4,420,145,989 bytes; 6 GiB-এর নিচে |

আগের 4B request-bound run 300s timeout হয়েছিল; এই call শেষ হয়েছে ও sampled RSS কম।
Model/quantization/output বদলেছে, এক sample—causal speedup/reliability দাবি নয়।
সময়ের মধ্যে JSON পাওয়া semantic suitability প্রতিষ্ঠা করেনি।

## Unmodified raw output-এর diagnostic review

- Cast-এ Kaito/courier ও Akira/owner ছাড়াও `id=holder`, `name="null"`,
  `role=courier` আছে—এটাই automated ROLE rejection-এর কারণ।
- Event actor `Kaito`/`Akira` নাম, declared ID `courier`/`owner` নয়।
- Initial holder `holder`; তারপর ground pickup। Shot 2/5 transfer-এ recipient
  visible cast-এ নেই; shot 2 বাক্য carrying বর্ণনা করে, handover নয়।
- Shot 4/6 একই holds বাক্য, কিন্তু event pickup; relevant distinct beats নেই।

এগুলো Codex-এর raw-text diagnostic, validator-এর পরবর্তী layer PASS/FAIL নয়।
ROLE-এ rejection হওয়ায় পূর্ণ custody/StoryPlan validation হয়নি। Output ঠিক করে
rerun করা হয়নি; owner approval বা hypothetical repaired plan-এর PASS দাবি নেই।

## Cleanup, outcome ও next step

Localhost ephemeral auth/CORS; unauthenticated models → 401। Runtime exit 0,
connection closure ও independent LISTEN check PASS; post-run closure পুনরায় নিশ্চিত।
Candidate file নেই। Ignored `data/planner-smoke/small-model-v1/`-এ acquisition,
license/model, harness/tests, exact request, raw content/events, metrics ও diagnostic
review সংরক্ষিত। পুরোনো policy/request/runtime hashes unchanged; পুরোনো evidence অক্ষত।

**এই candidate স্থগিত; নতুন prompt/run loop নয়।** দুই পরীক্ষিত model path-এর কোনোটিতে
accepted plan পাওয়া যায়নি। Bengali/অন্য duration/traits/repeatability ও Phase 3 gate
অসম্পূর্ণ; 3.10 শুরু হয়নি। পরের bounded কাজ চাইলে দুই path-এর evidence দিয়ে owner
decision review; অনুমোদন pending। Retry/download/model switch/budget বৃদ্ধি নয়।

Document links, RESUME <60 lines, ledger/status/scope, plan excerpt drift ও whitespace
checks PASS। Production/master অপরিবর্তিত; app tests পুনরায় নয়; commit হয়নি।
