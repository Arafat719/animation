# Semantic contract model test — ফল

2026-09-21। **অনুমোদিত এক-call test সম্পন্ন: acceptance FAIL।**
[Exact proposal](local-planner-semantic-model-test-proposal.md)-এর পরে owner
“ok porer kaj suru kor” বলে isolated harness/test অনুমোদন করেছেন।

## মূল ফল

Call 222.91s-এ `stop` finish হয়েছে; JSON shape PASS। কিন্তু existing semantic
validator প্রত্যাখ্যান করেছে: **REFERENCE `$.b[4].e.object`**। পঞ্চম shot-এ object
`:`; declared notebook ID `N`। কোনো repair, fallback বা candidate assembly হয়নি।
এটি আগের structural checks-এর বাইরে explicit object-reference rejection-এর
বাস্তব evidence; model story quality PASS নয়।

## Execution ও checks

Verified Qwen3-4B Q4_K_M / llama.cpp b10964 পুনর্ব্যবহার; model size/mtime মিলে গেছে,
আগের checksum evidence পুনর্ব্যবহার। Download/rehash/upgrade হয়নি। Contract hash
অপরিবর্তিত। CPU চার threads, zero GPU/offload, এক slot, context 8192; reasoning off;
seed/sampling proposal অনুযায়ী; output cap 768, generation timeout 300s।

নতুন isolated harness-এর **চার offline test methods ও compile PASS**: pending review,
stable code/path propagation, incomplete/length/token/memory/thinking rejection এবং
exclusive one-call marker। Existing ছয়-test/27-fixture contract baseline পুনর্ব্যবহার।
Request 4,222 bytes, schema 1,947 bytes; exact approved messages/schema ব্যবহৃত।

| Measurement | Observed |
| --- | --- |
| Calls / repair | ১ / ০ |
| Model load | 21.29s |
| Generation end-to-end | 222.91s |
| First content | 80.66s |
| Prompt eval | 436 tokens / 80.624s |
| Decode | 395 tokens / 142.242s; runtime 2.77 tokens/s |
| Usage | 831 total tokens; cached ০ |
| Content / finish | 1,298 characters / stop; reasoning empty; token cap হয়নি |
| Lifecycle | 244.61s |
| Peak sampled RSS | 5,504,684 KiB ≈ 5.25 GiB |
| Minimum available RAM | 7,933,680 KiB ≈ 7.57 GiB |
| Process swap / resource stop | ০ / নেই |
| Experiment directory | 2,584,792,697 bytes; 6 GiB cap-এর নিচে |

V2-এর 140.93s/280 prompt/336 output tokens-এর তুলনায় prompt ও output বেড়েছে।
এক sample, schema/prompt উভয় পরিবর্তন: causal speedup/slowdown বা reliability দাবি নয়।
Timeout/token cap এই failure-এর কারণ নয়।

## Raw evidence-এর diagnostic review

Cast: A=Courier/courier, B=Vendor/owner; notebook N, owner B, initial holder null।

| Shot | Action | Event / observation |
| --- | --- | --- |
| 1 | Courier approaches the riverside market. | pickup A; action-এ notebook তোলা নেই |
| 2 | Courier hands notebook to Vendor. | transfer A→B, visible A/B |
| 3 | Vendor inspects the notebook. | inspect B |
| 4 | Vendor confirms the notebook is lost. | mention B |
| 5 | Courier leaves the market area. | gesture A, object `:` → unknown reference |
| 6 | Vendor holds the notebook as the Courier leaves. | observe B; departure পুনরাবৃত্তি |

Shared fields literal `shared setting`, `mood`, `lighting`—প্রকৃত scene description নয়।
Roles metadata ও transfer visibility আগের থেকে স্পষ্ট, কিন্তু shot 1 action-event
mismatch এবং placeholder/repeated departure-এর কারণে narrative-ও গ্রহণযোগ্য নয়।
Reviewer Codex; এটি invalid draft-এর diagnostic review, owner human approval নয়।

Reference layer-এ rejection হওয়ায় full custody/final-holder/StoryPlan stages চালানো
হয়নি। `:` বদলে `N` বসিয়ে validator rerun হয়নি; hypothetical corrected plan-এর PASS
দাবি নেই। Raw content থেকে missing pickup/ownership অর্থ harness দিয়ে পূরণ হয়নি।

## Cleanup ও recovery

Localhost-only ephemeral auth/CORS; unauthenticated models request → 401। Runtime
exit 0; connection এবং independent `/proc/net/tcp*` LISTEN checks-এ port বন্ধ।
`plan-schema-validated.json` নেই—কোনো accepted/candidate plan save হয়নি।

Ignored `data/planner-smoke/semantic-run-v1/`-এ request, wrapper/harness/tests,
authorization/preflight/hashes, offline checks, raw content/events, metrics/samples,
code/path rejection, diagnostic review ও cleanup evidence সংরক্ষিত। পুরোনো contract,
fixtures/raw outputs অক্ষত; marker accidental rerun আটকাবে।

Document links, RESUME size, scope/status, plan drift ও whitespace checks PASS।
Production API/UI/DB/source/master অপরিবর্তিত; app tests পুনরায় নয়; commit হয়নি।
নতুন model/download/timeout বৃদ্ধি, retry/repair বা 3.10 implementation হয়নি।

পরবর্তী bounded কাজ: saved reference error, placeholder copying ও action-event
mismatch-এর [offline evidence review](local-planner-semantic-run-review.md) owner-এর
পরবর্তী নির্দেশে সম্পন্ন। আরেক run স্বয়ংক্রিয় নয়।
Bengali/অন্য duration/traits/repeatability ও Phase 3 real-adapter gate অসম্পূর্ণ।
