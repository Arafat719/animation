# Phase 3 planner repair/retry — gap review ও পরের micro-step

2026-09-23। Owner “hmm etai koro tahole” দিয়ে model ছাড়া gap review এবং একটি ছোট
implementation step নির্ধারণ অনুমোদন করেছেন। Review সম্পন্ন; implementation হয়নি।
এটি বন্ধ CPU-model experiment queue থেকে পৃথক offline scope।

## Source-এ পাওয়া বর্তমান অবস্থা

| অংশ | Evidence | ঘাটতি / সিদ্ধান্ত |
| --- | --- | --- |
| Input validation | [PlannerRequest ও MockPlanner](../animation_studio/providers/planner.py): strict request, blank/length/seed/duration/unique cast checks; unchecked model copy revalidation | আগে থেকেই আছে; পুনরায় বানানোর প্রয়োজন নেই |
| Output schema | [StoryPlan](../animation_studio/domain/v1/story_plan.py): cast/reference/order/timeline checks | invalid output reject করতে পারে; retry orchestration নেই |
| Planner boundary | PlannerProvider.plan(request) → StoryPlan; deterministic MockPlanner | raw malformed output ও repair feedback পাঠানোর interface নেই |
| API preview | [get_mock_plan](../apps/api/main.py): request error → 422; সরাসরি MockPlanner call | network-free read-only preview; এখানে retry যোগ করা এই ধাপের প্রয়োজন নয় |
| Shot retry | [MockShotRunner](../animation_studio/pipeline/mock_shot_runner.py): explicit rerun, max_attempts initial attempt-সহ | এটি shot execution; planner output repair নয় |
| Tests | [mock planner](../tests/test_mock_planner.py), [preview](../tests/test_mock_plan_api.py), [shot runner](../tests/test_mock_shot_runner.py) | determinism/input rejection/read-only preview/shot resume আছে; malformed planner → repair → bounded stop coverage নেই |

[Phase 3 task 5](plan/phase-3.md) prompt validation, repair ও maximum retry count
চায়। বিদ্যমান checks বজায় রেখে অনুপস্থিত output-repair orchestration আলাদা করে
পরীক্ষা করা যায়। Runtime health/cancellation, real semantic acceptance ও API wiring
এখনও পৃথক কাজ। পূর্ণ source/master/logs পড়া হয়নি; সংশ্লিষ্ট files-এ সীমিত review।

## নির্বাচিত একমাত্র implementation micro-step

**Offline planner output repair runner, scripted fake provider-সহ unit tests।**
প্রস্তাবিত files: `animation_studio/providers/planner_repair.py` এবং
`tests/test_planner_repair.py`। Existing PlannerProvider/MockPlanner/API/DB/UI অপরিবর্তিত
রেখে নতুন internal utility; production path-এ সংযোগ এই step-এ নয়। এটি Phase 3
repair task-এর একটি অংশ, 3.10 real adapter বা phase completion নয়।

প্রস্তাবিত আচরণ:

1. Caller-এর PlannerRequest পুনরায় validate করে independent snapshot রাখবে। Invalid
   input/config হলে provider call ০। Existing normalization নিয়মই ব্যবহার করবে।
2. ছোট পৃথক protocol: `generate(request) -> str`,
   `repair(request, previous_output, issues) -> str`। Tests-এ scripted fake;
   mock-plan JSON থেকে valid fixture বানানো যাবে, model success বলা যাবে না।
3. `max_retries` strict integer 0–2; default 0। Initial generate একবার,
   তারপর সর্বোচ্চ max_retries repair calls; মোট call ≤ 1 + max_retries। এই cap
   utility-র প্রস্তাবিত local policy; master-এর নতুন global budget নয়।
4. প্রত্যেক raw string existing StoryPlan JSON validator দিয়ে validate করবে।
   Declared total duration request-এর duration-এর সঙ্গে 1e-6 tolerance-এ মিলবে;
   schema-valid 30s output দিয়ে 60s request success বলা যাবে না।
5. শুধু invalid output/schema বা duration mismatch repairযোগ্য। Feedback-এ stable
   issue code/path এবং আগের raw output যাবে; runner নিজে JSON strip/patch, story
   invention, default beat বা ID replacement করবে না। প্রতিটি repair output আবার
   একই checks পেরোবে; unchecked object candidate হিসেবে নেওয়া হবে না।
6. Provider exception, timeout exception বা non-string return হলে সঙ্গে সঙ্গে stop;
   broad exception ধরে retry নয়। Validation error-এর boundary হবে returned raw
   output-এর চারপাশে, provider call-এর চারপাশে নয়। Input/provider failure আলাদা থাকবে।
7. Success result-এ validated plan, attempts এবং `REVIEW_REQUIRED` থাকবে; automatic
   accepted status নয়। Retry exhaustion-এ typed failure ও attempt/issue diagnostics;
   partial/candidate success নয়। Request snapshot প্রতিটি call-এ fresh copy পাবে।
8. No network/model/filesystem persistence, sleep/backoff বা hidden retry। Provider
   timeout exception propagate করা প্রকৃত timeout enforcement নয়; live provider
   ব্যবহারের আগে lifecycle/cancellation design পৃথকভাবে প্রয়োজন।

## প্রয়োজনীয় meaningful tests / completion check

- Valid first output → এক call, repair ০, independent validated plan ও REVIEW_REQUIRED।
- Malformed JSON এবং reference/timeline-invalid output → fake repaired output-এ
  success; feedback ও original request preserved; raw input নিজে সংশোধন নয়।
- Schema-valid wrong requested duration → repair/reject, false success নয়।
- Always-invalid fake-এ max_retries 0/1/2 → মোট 1/2/3 call-এর পরে typed failure;
  negative/bool/non-integer/>2 config এবং invalid request → zero calls।
- Generate ও repair দুটির provider exceptions/non-string result → আর call নয়।
- Fake request mutate করলেও পরের call ও caller-এর input অক্ষত; success হলেও
  semantic/human acceptance দাবি নেই।

Implementation অনুমোদিত হলে targeted নতুন suite এবং existing mock-planner/
StoryPlan suites চালাবে; API change না থাকলে full app suite নয়। Public schema বদলালে
তা এই bounded scope-এর বাইরে—আগে review করতে হবে। এই turn-এ app tests চালানো হয়নি।

## সীমা, outcome ও next authorization

এই runner raw full StoryPlan boundary পরীক্ষা করবে; ignored semantic-draft experiment
policy-কে production-এ টেনে আনবে না। Request fidelity-এর সব semantic criterion,
character-trait preservation ও real-provider behavior এই step-এ সমাধান দাবি নয়।
Offline PASS হলেও 4B/1.7B failed results বহাল; তাদের rerun অনুমোদিত হবে না।

Review-তে blocker নেই। পরবর্তী bounded কাজ উপরের runner ও tests implement করা;
Owner-এর পরবর্তী নির্দেশে implementation অনুমোদিত ও সম্পন্ন;
[checkpoint ও checks](planner-repair-checkpoint.md)।
Requirements বদলায়নি; master/excerpts edit নয়। Document links, RESUME <60 lines,
status/scope, generated-plan drift ও whitespace checks PASS। Source/production/model
assets অপরিবর্তিত; নতুন model run/download এবং commit হয়নি।
