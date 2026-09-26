# দুই model path — owner decision review

2026-09-22। Owner “porer kaj koro” নির্দেশে review প্রস্তুতি সম্পন্ন।
**সুপারিশ: পরীক্ষিত দুই CPU path স্থগিত রাখো; mock flow বজায় রাখো এবং 3.10
real adapter শুরু করো না।**
Owner-এর পরবর্তী “jeta valo mone koro setai koro” নির্দেশে Codex-কে পথ নির্বাচনের
অনুমতি দেওয়া হয়েছে। সেই অনুমতিতে এই সুপারিশ নির্বাচিত ও কার্যকর: দুই পরীক্ষিত
CPU planner experiment স্থগিত; existing mock flow বজায় থাকবে।

## কী সিদ্ধান্ত নেওয়ার মতো evidence আছে

| বিষয় | Qwen3-4B Q4_K_M | Qwen3-1.7B Q8_0 |
| --- | --- | --- |
| পরীক্ষিত calls | পাঁচ configuration-এ মোট ৫ | latest request অপরিবর্তিত রেখে ১ |
| Accepted plan | ০ | ০ |
| Failure | ২ timeout; ২ strict PASS/semantic FAIL; ১ REFERENCE rejection | complete JSON, ROLE `$.c` rejection—দুই courier |
| একই request-bound input-এ সময় | 300.001s timeout | 215.215s, stop finish |
| ঐ call-এর peak sampled RSS | 5.30 GiB | 2.78 GiB |
| পরবর্তী validation-এর সীমা | incomplete JSON; full policy/narrative verdict হয়নি | ROLE-এ stop; full custody/StoryPlan assembly হয়নি |

উৎস: [4B review ও পাঁচ report-এর links](local-planner-suitability-review.md),
[4B request-bound result](local-planner-request-bound-test-result.md),
[1.7B result](local-planner-small-model-result.md)। ছয় observed call-এ accepted ০;
এগুলো একই test suite-এর repeated trials নয়, reliability estimate-ও নয়।

ছোট model সময়সীমার মধ্যে output দিয়েছে, কিন্তু role, actor ID, possession,
visibility ও repeated beat-এর diagnostic সমস্যা আছে। বড় model-এর partial output-এও
custody/action mismatch ছিল। **Latency কমা quality gate পূরণ করেনি।** দুই call-এ
model/quantization/output বদলেছে; causal speedup বা সব CPU/model ব্যর্থ দাবি নয়।
RAM/resource stop পাওয়া যায়নি; timeout বাড়ানো বা RAM বাড়ানোকে semantic সমস্যার
সমাধান ধরার evidence নেই। Offline tests PASS rejection logic-এর evidence,
model-এর গল্প গ্রহণযোগ্য হওয়ার প্রমাণ নয়।

## ব্যয় ও সংরক্ষণের সিদ্ধান্ত

দুটি verified model এবং raw evidence স্থানীয়ভাবে আছে; latest runtime report-এ
মোট experiment directory প্রায় 4.42 GB, 6 GiB cap-এর নিচে। ছোট model acquisition
একা 25.57 মিনিট ও 1.83444 GB response body নিয়েছে; তার generation 215.215s।
এই review-এ নতুন download/inference হয়নি। বিদ্যুৎ/আর্থিক খরচ মাপা হয়নি।
Assets/evidence মুছবে না, পুনরায় download নয়; exclusive markers অক্ষত রাখবে।

## Owner-এর নির্বাচন

| পথ | এখনকার মূল্যায়ন | বেছে নিলে পরের bounded কাজ |
| --- | --- | --- |
| পরীক্ষিত CPU planner স্থগিত, mock flow রাখা — সুপারিশ | বাড়তি experiment ব্যয় নেই; real planner অসম্পূর্ণ থাকবে | status-এ owner সিদ্ধান্ত নথিভুক্ত; নতুন feature/run নয় |
| আলাদা model/hardware path বিবেচনা | capability, quality, latency ও খরচ এখনও অমাপা | শুধু একটি নির্দিষ্ট candidate-এর feasibility/budget proposal; download/run নয় |
| বর্তমান model-এ আরেক prompt/contract/timeout experiment | নতুন hypothesis ছাড়া সুপারিশ নয়; প্রথম rejection ঠিক করলেই অন্য diagnostic সমস্যা মেটে না | owner নির্দিষ্ট নতুন hypothesis চাইলে আগে evidence review; blind retry নয় |

দ্বিতীয় পথ বেছে নিলে proposal-এ official source/pinned asset, hardware,
acquisition size, storage headroom, সময়/টাকা cap, exact input ও অপরিবর্তিত quality
rubric থাকতে হবে। GPU-কে quality fix ধরে নেওয়া যাবে না; কোনো hardware/model এখানে
নির্বাচিত বা priced হয়নি। Paid resource এবং >2 GB model download-এর explicit
approval প্রয়োজন; এই review তার অনুমোদন নয়।

## Gate ও authorization

[Phase 3](plan/phase-3.md)-এর 3.10 strict JSON output test set এবং narrative acceptance
এখনও পূরণ হয়নি। একটি isolated case PASS হলেও Bengali/অন্য duration/traits/
repeatability ও প্রাসঙ্গিক broader checks বাকি থাকত। Mock completion real adapter
বা পরের phase শুরু করার অনুমোদন নয়। Acceptance requirement পরিবর্তন করা হয়নি।

Review micro-step **সম্পন্ন**; blocker নেই। Real-planner অগ্রগতির blocker:
accepted plan/test-set evidence নেই। **পথ নির্বাচন ও status checkpoint সম্পন্ন।**
এই experiment queue-তে আর কোনো সক্রিয় micro-step নেই। নতুন প্রয়োজন বা নির্দিষ্ট
নতুন hypothesis এলে পৃথক scope নির্ধারণ করবে; একই review/proposal loop restart নয়।
Assets, raw evidence ও execution markers সংরক্ষিত; production configuration বদলানোর
প্রয়োজন নেই, কারণ real adapter যুক্ত হয়নি। Phase 3 অসম্পূর্ণই থাকবে।

Document links, RESUME <60 lines, ledger/status/scope, plan excerpt drift ও
whitespace checks PASS। নির্দিষ্ট reports ব্যবহার হয়েছে; source/raw logs/model assets
পড়া বা বদলানো হয়নি। App/model/offline tests পুনরায় নয়; production/master অপরিবর্তিত;
commit হয়নি।
