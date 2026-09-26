# Compact v2 — অর্থ অক্ষুণ্ণ রাখার isolated test ফল

2026-09-20। **এক-call test সম্পন্ন: strict JSON/StoryPlan PASS;
semantic acceptance FAIL।** Owner-এর পরবর্তী “ok porer kaj suru koro” নির্দেশে
[নির্দিষ্ট proposal](local-planner-semantic-test-proposal.md) কার্যকর হয়েছে।
Retry/repair, download, timeout বৃদ্ধি বা 3.10 adapter হয়নি।

## কী বদলেছে ও কী যাচাই হয়েছে

শুধু exact proposed system prompt বদলেছে। AST comparison ও request equality-তে
schema, user message, sampling ও assembly অপরিবর্তিত PASS; runner byte-identical।
Verified Qwen3-4B Q4_K_M / llama.cpp b10964 পুনর্ব্যবহার; model size/mtime আগের
preflight-এর সঙ্গে মিলে গেছে। পূর্বের checksum evidence পুনর্ব্যবহার, rehash নয়।

চার offline contract test methods ও compile PASS। আগের raw output structural
PASS রেখেও semantic negative হিসেবে চিহ্নিত; keyword-only, reverse transfer ও
inconsistent possession-এর তিন synthetic example-ও textual review-তে FAIL।
এগুলো automated semantic detector বা নতুন model output নয়।

CPU ৪ threads, zero GPU/offload, এক slot, 8192 context, 768 output cap;
reasoning off; seed 42 ও sampling আগের মতো। Load 180s/generation 300s cap বহাল।
পরিচিত socket restriction-এর জন্য অনুমোদিত escalation-এ localhost-only server;
ephemeral auth ও restrictive CORS, unauthenticated models request → 401।

## মাপা ফল: v1 বনাম v2

| Measurement | Compact v1 | Compact v2 |
| --- | --- | --- |
| Model load | 4.02s | 4.43s |
| Generation end-to-end | 52.44s | 140.93s |
| First content | 7.70s | 32.72s |
| Prompt tokens / evaluation | 133 / 7.688s | 280 / 32.708s |
| Output tokens / decode | 175 / 44.738s | 336 / 108.208s |
| Runtime decode rate | 3.89 tokens/s | 3.10 tokens/s |
| Total usage / cached | 308 / ০ | 616 / ০ |
| Content / finish | 455 characters / stop | 973 characters / stop |
| Message UTF-8 bytes | 465 | 1,198 |
| Schema UTF-8 bytes | 930 | 930 |
| Compact serialized request bytes | 1,749 | 2,485 |
| Peak sampled RSS | 5.20 GiB | 5,531,672 KiB ≈ 5.28 GiB |
| Minimum available RAM | 7.40 GiB | 7,619,908 KiB ≈ 7.27 GiB |

V2-তে এক generation, repair ০; reasoning empty; finish `stop`, cap/truncation হয়নি।
Runtime lifecycle 145.68s; process swap ০, resource stop নেই; directory মাপ
2,584,358,988 bytes, 6 GiB-এর নিচে। ছয়টি 5.0s shot, 30.0s timeline ও StoryPlan PASS।

বড় prompt ও বেশি descriptive output-এর সঙ্গে সময়ও বেড়েছে; এক sample থেকে causal
performance বা reliability দাবি নয়। পুরোনো model run পুনরায় করা হয়নি।

## Raw actions ও semantic review

| Shot | Model-এর action | Visible cast |
| --- | --- | --- |
| 1 | Rina finds a blue notebook on the ground | Rina |
| 2 | Takumi approaches and checks the notebook's seal | Takumi |
| 3 | Aiko notices the notebook's missing pages | Aiko |
| 4 | Takumi opens the notebook and shows the pages | Takumi |
| 5 | Aiko asks Takumi to return the notebook to Rina | Aiko, Takumi |
| 6 | Takumi hands the notebook back to Rina | শুধু Rina |

Reviewer: Codex criteria-based textual review; owner human approval নয়।

| Criterion | Verdict ও evidence |
| --- | --- |
| Action completeness | PASS: 1–6-এ actor ও পূর্ণ action; 6-এ object/recipient স্পষ্ট |
| Lost notebook/ownership | FAIL: 1-এ Rina finder; 5–6 তাকে recipient করেছে, owner পরিচয় প্রতিষ্ঠিত নয় |
| Return direction | FAIL: 6-এ Takumi → Rina transfer আছে, কিন্তু courier/owner role কোনো model field-এ স্পষ্ট নয় |
| Causal/visual consistency | FAIL: 1 থেকে 2/4-এ possession transition অস্পষ্ট; 6-এ handing actor Takumi visible cast-এ নেই |
| Six useful beats | FAIL: 2–4-এর seal/missing pages/showing pages owner identification-এর সঙ্গে যুক্ত নয়; missing-pages detail-এর resolution নেই |
| Resolution | FAIL: 6-এ transfer ending আছে, প্রতিষ্ঠিত owner-কে lost item ফেরত দেওয়ার সমাপ্তি নেই |
| Scene/derived prompts | FAIL: shared scene/light compatible, assembly faithful; কিন্তু 6-এর prompt cast শুধু Rina, action-এ Takumi-ও আবশ্যক |

আগের bare verbs-এর তুলনায় পূর্ণ বাক্য, notebook ও recipient এসেছে—এই উন্নতি
আছে। কিন্তু সব criterion pass হয়নি। Copied logline দিয়ে courier/owner role পূরণ
করা হয়নি। `plan-schema-validated.json` শুধু candidate; accepted/rendered plan নয়।

## Cleanup, evidence ও next step

Runtime exit 0; connection check এবং আলাদা `/proc/net/tcp*` LISTEN check-এ port
বন্ধ। কোনো server বাকি নেই। Ignored `data/planner-smoke/compact-v2/`-এ harness,
authorization/AST evidence, offline checks, negative review, request/schema,
preflight, raw content/events, candidate plan, timings/resource samples,
semantic review ও cleanup evidence রাখা হয়েছে। V1 evidence/markers অক্ষত।

Document links, RESUME size, status/scope, plan excerpt drift ও whitespace checks
PASS। Production source/API/DB/UI অপরিবর্তিত; app tests পুনরায় নয়; commit হয়নি।

পরবর্তী bounded কাজ: **দুই compact output-এর offline failure analysis**—role,
object possession ও visible cast-এর কোথায় contract/check ঘাটতি তা evidence দিয়ে
নির্ধারণ, তারপর প্রয়োজন হলে একটি reviewable experiment proposal। পরপর semantic
failure-এর পরে অনুমান করে আরেক prompt/run নয়। Owner-এর পরবর্তী নির্দেশে
[offline analysis](local-planner-offline-failure-analysis.md) সম্পন্ন হয়েছে;
কোনো নতুন model run বা 3.10 অনুমোদিত নয়। Bengali/অন্য duration/traits/repair/
repeatability অমাপা; Phase 3 real-adapter gate ও পূর্ণ five-case acceptance অসম্পূর্ণ।
