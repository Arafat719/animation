# ছোট model + বর্তমান CPU — bounded alternative proposal

2026-09-22। Owner “porer kaj suru koro” বলে suitability review-এর পরের proposal
প্রস্তুতি অনুমোদন করেছেন। নির্দিষ্ট CPU/GPU পছন্দের উত্তর না আসায় বর্তমান CPU-তে
ছোট model-কে প্রস্তাবিত বিকল্প ধরা হয়েছে; owner নির্বাচন/execute approval দাবি নয়।
**Proposal সম্পন্ন; owner-এর পরবর্তী “porer kaj suru koro” নির্দেশে
acquisition, isolated harness ও এক-call execution অনুমোদিত (2026-09-22)।**
Execution সম্পন্ন: [ফল](local-planner-small-model-result.md)—ROLE rejection, acceptance FAIL।
পুরোনো Qwen3-4B path স্থগিত রাখার [সুপারিশ](local-planner-suitability-review.md) বহাল।

## প্রশ্ন ও নির্বাচনের যুক্তি

একই notebook-return request, policy ও 300s deadline রেখে ছোট Qwen3-1.7B Q8_0
কি complete এবং narrative-সহ acceptable output দিতে পারে? পুরোনো পাঁচ call-এ
accepted plan নেই; এই candidate-এর পক্ষে planner-quality evidence নেই।

Official GGUF পাওয়া যায়, নতুন GPU/runtime acquisition লাগে না, এবং model payload
2 GB-এর নিচে—এই কারণে একটি সীমিত feasibility test প্রস্তাব। কম parameter থেকে
কম latency হতে পারে—এটি hypothesis; throughput guarantee নয়। ছোট model-এ semantic
quality আরও খারাপ হতে পারে। Parameter count ও quantization দুটোই বদলাবে, তাই ফল
থেকে model size-এর একক causal প্রভাব দাবি করা যাবে না। এটি সর্বোত্তম model-এর
বাজারসমীক্ষা নয়; paid GPU বা বড় model-এর suitability-ও এই proposal বিচার করে না।

## নির্দিষ্ট asset ও acquisition budget

Official metadata 2026-09-22-এ read-only যাচাই:

- Repository: [Qwen/Qwen3-1.7B-GGUF](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF)।
  Apache-2.0; official card llama.cpp usage দেখায়, কিন্তু pinned b10964-এ এই
  নির্দিষ্ট file/schema combination এখানে চালিয়ে যাচাই হয়নি।
- Revision: [90862c4b9d2787eaed51d12237eafdfe7c5f6077](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/commit/90862c4b9d2787eaed51d12237eafdfe7c5f6077)।
- File: [Qwen3-1.7B-Q8_0.gguf](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/blob/90862c4b9d2787eaed51d12237eafdfe7c5f6077/Qwen3-1.7B-Q8_0.gguf)।
  Exact payload **1,834,426,016 bytes** (~1.834 GB); pinned raw LFS pointer থেকে
  size/hash পড়া হয়েছে, model bytes নয়।
- Expected SHA256: `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`।
  Acquisition শেষে local whole-file size+SHA256 মিললেই use; mismatch-এ stop।
- নতুন ignored destination `data/planner-smoke/small-model-v1/`; model, license,
  request/harness/raw evidence এখানে। আগের model/runtime/evidence অক্ষত রাখবে।
- Downloaded response-body budget মোট **1.90 GB decimal**, metadata-সহ; acquisition
  wall-clock cap 45 মিনিট। এক transfer attempt, automatic retry/resume/redownload ০;
  interrupted partial সংরক্ষণ করে report। Network wire overhead এই মাপের বাইরে।
- সব `data/planner-smoke/` assets/evidence মিলে আগের **6 GiB disk cap** বহাল;
  extra full-file copy নয়, `.part` থেকে rename। Latest reported directory 2.585 GB;
  proposed file যোগে আনুমানিক 4.420 GB, নতুন evidence বাদ। Preflight-এ actual usage
  ও অন্তত 3 GiB free disk চাই; না মিললে stop, পুরোনো evidence মুছবে না।
- Proposal-time filesystem free: 102,072,348,672 bytes; acquisition-এর সময় পুনরায়
  মাপবে। Paid compute/API/storage budget **০**; স্থানীয় বিদ্যুৎ/সময় মাপা হয়নি।

## অপরিবর্তিত request ও runtime

[Request-bound exact proposal](local-planner-request-bound-test-proposal.md)-এর
“Exact messages”, response schema, sampling, assembly, rejection order ও narrative
rubric সম্পূর্ণ বহাল। Saved `request-bound-run-v1/request.json`-এর সঙ্গে equality
check করে কেবল API model identifier প্রয়োজন হলে বদলানো যাবে; messages/schema নয়।
Policy `request-bound-policy-v1/policy.py` অপরিবর্তিত। Missing/mismatched inputs-এ
stop; reconstruct করে অনুমান নয়। Expected baseline request 4,588 bytes/schema 1,985;
model identifier বদলালে নতুন byte count এবং exact diff report করতে হবে।

Verified llama.cpp b10964 / b29c606e2 reuse; Intel i7-4790S, CPU generation/batch
threads ৪, GPU/offload ০, এক slot, context 8192, reasoning off। Seed 42,
temperature .7, top-p .8, top-k 20, min-p 0, presence penalty 1.5,
cache_prompt=false; streaming usage আগের মতো। Runtime upgrade নয়।

| Limit | প্রস্তাবিত cap / stop |
| --- | --- |
| Generation / repair / retry | ১ call / ০ / ০; warm-up generation-ও নয় |
| Model load / generation | 180s / 300s; সর্বমোট load+generation 480s |
| Output | 768 tokens; cap hit/length finish/incomplete/reasoning থাকলে FAIL |
| Runtime memory | RSS 8 GiB; available RAM floor 2 GiB; persistent process swap-এ stop |
| Disk / acquisition | মোট 6 GiB; response-body 1.90 GB / 45 মিনিট |

## অনুমোদনের পরে এক bounded execution

1. Acquisition-এর আগে byte/disk/time guards ও pinned metadata যাচাই; local hash
   PASS-এর পরে existing runtime provenance ও saved policy/request hashes যাচাই।
   আলাদা ignored harness ও exclusive one-call marker; আগের run restart নয়।
2. Harness compile ও targeted offline checks: exact request delta, acquisition
   budget/hash rejection, one-call guard, timeout/token/resource rejection,
   code/path propagation ও REVIEW_REQUIRED। অপরিবর্তিত policy baseline reuse।
3. Loopback server, ephemeral auth/key, explicit local CORS; key logs-এ নয়।
   Load/schema/template unsupported হলে stop/report; runtime upgrade বা fallback নয়।
4. এক generation call। Complete content-এ existing policy.candidate(raw), strict
   semantic/custody/StoryPlan validation। Failure-এ raw/code/path রাখবে; ID/action
   rewrite, repaired JSON, fixture answer বা invented scene নয়।
5. Valid candidate-ও REVIEW_REQUIRED: raw actions-এর independent narrative review
   চাই। সব object ID notebook, concrete scene, courier/owner role, lost item,
   custody/visible participants, sentence-event agreement, ছয়টি relevant distinct
   beat ও courier→owner resolution—সব PASS প্রয়োজন। Codex text review owner approval নয়।
6. Prompt/output totals, prompt-eval/decode/first-content/end-to-end time, finish,
   RSS/RAM/swap, directory/body byte counts ও raw events record। Missing metric
   unavailable; সব exit-এ shutdown, connection ও independent LISTEN closure check।

## ফলের সিদ্ধান্ত ও পরবর্তী সীমা

শুধু দ্রুত complete JSON যথেষ্ট নয়; existing strict policy + narrative + resource
ও cleanup checks সব PASS হলে **এক-case feasibility PASS**। কোনো FAIL/UNRESOLVED-এ
accepted নয়। Smaller model comparison descriptive; reliability/causal speedup নয়।

PASS হলে পরের কাজ broader-case evaluation proposal; automatic run নয়। Quality,
timeout, setup বা resource failure হলে report করে এই candidate স্থগিত; আরেক
prompt/contract loop, model switch, retry বা budget বৃদ্ধি নয়। Bengali, 45/60s,
traits, repeatability ও পূর্ণ test set বাকি থাকবে; 3.10 adapter শুরু নয়।

## Checks ও authorization

Docs-only: local links, RESUME <60 lines, ledger/status/scope, generated plan drift
ও whitespace checks PASS। Official pages ও ছোট pointer ছাড়া model/tokenizer/logs
পড়া বা run হয়নি; app tests/harness implementation হয়নি; master অপরিবর্তিত।

পরের bounded কাজ: এই pinned asset acquisition, isolated harness ও এক-call test;
owner-এর পরবর্তী নির্দেশে এই scope অনুমোদিত হয়েছে। [Phase 3 step 3.9](plan/phase-3.md)-এর “download/run করার আগে
অনুমতি চাইবে” শর্ত অনুযায়ী proposal approval ছাড়া execute নয়। Payload <2 GB হলেও
এই phase-specific শর্ত বহাল; পরবর্তী owner নির্দেশে তা পূরণ হয়েছে।
Retry, budget বৃদ্ধি বা 3.10-এর অনুমোদন নয়।
