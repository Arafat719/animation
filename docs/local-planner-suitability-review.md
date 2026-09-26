# বিদ্যমান model+CPU path — suitability review

2026-09-22। Owner-এর নির্দেশে existing report-ভিত্তিক bounded review সম্পন্ন।
**সুপারিশ: বর্তমান Qwen3-4B Q4_K_M + CPU path-এর নতুন experiment স্থগিত রাখো;
3.10 real adapter-এর উপযোগিতা প্রমাণিত হয়নি।** এটি owner-এর চূড়ান্ত নির্বাচন নয়।
Mock flow ব্যবহারযোগ্য; Phase 3 সম্পূর্ণ নয়। নতুন run/download বা implementation হয়নি।

## Evidence ও সিদ্ধান্তের ভিত্তি

পরীক্ষিত পরিবেশ: Intel i7-4790S, চার CPU threads, GPU/offload ০,
llama.cpp b10964, এক slot, 8192 context। একই notebook-return synthetic গল্পের
পাঁচটি পরিবর্তিত configuration-এর এক-call evidence; repeatability benchmark নয়।

| নির্দিষ্ট report | Generation সময় | Structural ফল | Acceptance / সীমা |
| --- | --- | --- | --- |
| [Full-schema A](local-planner-smoke-result.md) | 300.02s timeout | প্রথম shot-এ incomplete JSON | FAIL; semantic verdict অমাপা |
| [Compact v1](local-planner-compact-test-result.md) | 52.44s | strict JSON/assembled StoryPlan PASS | FAIL; notebook ও return সম্পর্ক নেই |
| [Compact v2](local-planner-semantic-test-result.md) | 140.93s | strict JSON/assembled StoryPlan PASS | FAIL; owner/possession অস্পষ্ট, transfer actor visible cast-এ নেই |
| [Semantic contract](local-planner-semantic-model-test-result.md) | 222.91s | JSON shape PASS; REFERENCE `$.b[4].e.object` FAIL | unknown object `:`; assembly হয়নি; pickup/action ও placeholder সমস্যা diagnostic-এ আছে |
| [Request-bound](local-planner-request-bound-test-result.md) | 300.001s timeout | পঞ্চম shot-এ incomplete JSON | FAIL; full policy/narrative verdict হয়নি; prefix-এ holder/pickup ও action mismatch |

Accepted plan **০/৫ observed calls**; এটি পরিসংখ্যানভিত্তিক success-rate estimate নয়।
Compact v1/v2-এর schema-valid candidate-কে accepted plan গণনা করা হয়নি। পরের
contract-এ ভিন্ন checks ছিল; পুরোনো output নতুন validator দিয়ে পুনরায় পরীক্ষা হয়নি।

## Suitability: কী প্রতিষ্ঠিত, কী নয়

- **সময়:** full-schema ও latest request-bound configuration 300s deadline মানেনি।
  ছোট compact output সময়ের মধ্যে এলেও narrative acceptance পায়নি। তিনটি completed
  call-এর runtime decode যথাক্রমে 3.89/3.10/2.77 tokens/s। Timeout run-এর last-log
  ~2.08/~2.22 tokens/s final usage নয়; এগুলো থেকে completion time extrapolate নয়।
- **গল্পের মান:** prompt/contract পরিবর্তনে পূর্ণ বাক্য, explicit roles, object IDs ও
  concrete scene-এর আংশিক উন্নতি আছে। কিন্তু সব প্রয়োজন একসঙ্গে পূরণ করা valid
  output নেই। Timeout বাড়ালেই custody/action consistency ঠিক হবে—এমন evidence নেই।
- **স্থানীয় resource:** reported peak sampled RSS প্রায় 5.20–5.30 GiB;
  কোনো report-এ memory/resource stop ধরা পড়েনি। Latest run-এ minimum available RAM
  8.14 GiB ও process swap ০; deadline-ই stop কারণ। RAM বাড়ালে এই failure সারবে বলে
  evidence নেই। Sampled RSS hardware capacity-এর সর্বজনীন guarantee নয়।
- **ব্যয়:** আগের verified model 2,497,280,256 bytes স্থানীয়ভাবে আছে; latest experiment
  directory প্রায় 2.585 GB, 6 GiB cap-এর নিচে। পাঁচ call-এর reported generation সময়ের
  যোগ প্রায় 1,016.30s (16.94 মিনিট); acquisition/load/review বাদ। বিদ্যুৎ বা আর্থিক
  খরচ মাপা হয়নি। এই review-এ নতুন compute/download ব্যয় সৃষ্টি করা হয়নি।
- **সীমা:** Bengali, 45/60s, dialogue, supplied traits, repair ও repeatability acceptance
  প্রতিষ্ঠিত নয়। একই model-এর সব configuration বা অন্য hardware/model অসমর্থ বলা
  যায় না; prompt/schema/output/reasoning settings বদলেছে বলে causal speedup দাবিও নয়।

## Owner-এর জন্য সিদ্ধান্তের বিকল্প

| বিকল্প | Evidence-ভিত্তিক মূল্যায়ন | ব্যয়/অনুমোদনের সীমা |
| --- | --- | --- |
| বর্তমান path স্থগিত, mock flow বজায় রাখা — সুপারিশ | accepted output নেই; একই loop চালানোর ভিত্তি অপর্যাপ্ত | নতুন inference/download নেই; বিদ্যমান evidence/assets সংরক্ষণ |
| আলাদা model/runtime বা hardware path-এর bounded proposal | সম্ভাবনা অমাপা; এই review কোনো candidate নির্বাচন করেনি | proposal-এ নির্দিষ্ট candidate, acquisition size, CPU/GPU, সময়/টাকা cap ও একই quality gate দিতে হবে; execution আলাদা অনুমোদন |
| বর্তমান path-এ আরেক prompt/run বা দীর্ঘ timeout | বর্তমান evidence থেকে সুপারিশ নয়; quality failure-ও আছে | নতুন নির্দিষ্ট hypothesis ও owner authorization ছাড়া নয় |

[Phase 3](plan/phase-3.md)-এর 3.10-এ strict JSON output test set PASS প্রয়োজন;
বর্তমান isolated ফল সেই gate পূরণ করেনি। Offline harness/policy PASS হলো rejection
ও test plumbing-এর evidence, model suitability নয়। কোনো acceptance requirement
শিথিল করা হয়নি; master/excerpts পরিবর্তনের প্রয়োজন নেই।

## Outcome, checks ও next step

Review preparation সম্পন্ন; owner suitability decision pending। পরের bounded কাজ:
owner বিকল্প path বেছে নিলে শুধু তার reviewable proposal প্রস্তুত করা—এখনও অনুমোদিত নয়।
নতুন run/download/retry/timeout বৃদ্ধি/adapter শুরু নয়। এটি docs review-এর blocker
নয়; real-adapter অগ্রগতির blocker হলো valid accepted plan/test-set evidence-এর অভাব।

Local document links, RESUME <60 lines, ledger/status/scope consistency,
generated plan drift ও whitespace checks PASS। App tests বা offline/model tests
পুনরায় চালানো হয়নি; নির্দিষ্ট reports-এর evidence ব্যবহার হয়েছে। Source/logs/raw
outputs, পুরোনো ফল, model assets ও production code অপরিবর্তিত; commit হয়নি।
