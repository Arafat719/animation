# Offline repair runner — request-fidelity gap review

2026-09-23। Owner “ok porer kaj koro” দিয়ে review অনুমোদন করেছেন।
Review সম্পন্ন; source implementation হয়নি। ভিত্তি: [runner checkpoint](planner-repair-checkpoint.md),
[Phase 3](plan/phase-3.md) ও নিচের সংশ্লিষ্ট source/tests।

## পাওয়া ঘাটতি

| বিষয় | বর্তমান evidence | প্রভাব |
| --- | --- | --- |
| Requested duration | [repair_plan](../animation_studio/providers/planner_repair.py) schema validation-এর পরে request duration মেলায় | এই সীমা ইতিমধ্যে covered |
| Supplied cast | একই runner request-এর characters-এর সঙ্গে output cast তুলনা করে না | request-এর ID বাদ বা name বদলালেও schema-valid output REVIEW_REQUIRED পেতে পারে |
| Traits | [MockPlanner/inject_character_traits](../animation_studio/providers/planner.py) visible cast-এর prompts-এ caller traits inject করে; generic repair runner তা করে না | mock-এর traits guarantee generic runner-এ নেই |
| Fresh lifecycle | [ShotPlan](../animation_studio/domain/v1/story_plan.py) completed/failed state, attempts/error/media paths অনুমোদন করে; runner শুধু schema/duration দেখে | নতুন draft-এ execution ফল থাকলেও REVIEW_REQUIRED আসতে পারে |
| Persistence guard | [PlanStore save](../animation_studio/persistence/plan_store.py) non-pending/attempts/error/media paths reject করে | downstream guard আছে; runner-এর fresh-plan guarantee নেই; API-তে runner wired নয় |

এগুলো source inspection থেকে নির্ধারিত reachable behavior; নতুন runtime probe/model
run বা পরীক্ষিত exploit দাবি নয়। REVIEW_REQUIRED মানে approval নয়; তবু fresh draft
দেওয়ার boundary-তে lifecycle metadata আগে reject করা উপযোগী।

## Cast/traits-এর পরবর্তী design সীমা

Supplied ID/name সংরক্ষণ, অতিরিক্ত cast অনুমোদন এবং absent supplied character-এর
নীতি স্পষ্ট করতে হবে। Existing injector supplied IDs-কে cast-এর subset হিসেবে
চায়; এটি exact cast equality requirement নয়। সব character প্রতি shot-এ visible
হতে হবে—এমন policy বানানো যাবে না। [Traits tests](../tests/test_character_traits.py)
visible/offscreen পার্থক্য, input preservation ও overflow rejection ধরে রাখে।

Existing injector base prompt-এ একবার প্রয়োগের জন্য; arbitrary repaired prompt-এ
অন্ধভাবে যোগ করলে duplicate traits হতে পারে। ভবিষ্যৎ cast/traits step-এ raw base
output বনাম assembled prompt ownership নির্ধারণ জরুরি। শুধু substring পাওয়া দিয়ে
semantic fidelity PASS বলা যাবে না। এই review সেই feature implement/requirement
পরিবর্তন করছে না; master/public schema অপরিবর্তিত।

## নির্বাচিত পরের ছোট implementation step

**repair_plan-এ fresh-plan lifecycle rejection যোগ করা**, existing schema ও
PlanStore অপরিবর্তিত রেখে। Cast/traits একই step-এ যোগ হবে না।

- Successful schema এবং requested-duration checks-এর পরে প্রতিটি shot পরীক্ষা:
  `status == pending`, `attempts == 0`, `error is None`, এবং `keyframe_path`,
  `raw_clip_path`, `lip_synced_clip_path` প্রত্যেকটি None হতে হবে।
- Violation-এ `RepairIssue(code='NON_FRESH_PLAN', path=('shots', index, field), ...)`;
  shot order এবং field order status/attempts/error/keyframe/raw/lip ধরে deterministic
  diagnostics। Duration mismatch থাকলে বর্তমান DURATION_MISMATCH precedence বহাল।
- একই existing max_retries budget-এ repair feedback; raw value reset/strip নয়।
  Exhaustion typed failure; repaired output-এ সব checks পুনরায়।
- `reference_inputs` input field, execution result নয়—এই step-এ blanket reject নয়।
  Opaque paths/files authorization আলাদা সীমা; filesystem access হবে না।
- Existing shared schema-তে lifecycle values নিষিদ্ধ করা যাবে না: persisted/resumed
  plans-এর বৈধ completed/failed state আছে। Freshness শুধু new-plan runner boundary।

Files: `animation_studio/providers/planner_repair.py`, `tests/test_planner_repair.py`।
Tests: প্রতিটি field independently schema-valid কিন্তু nonfresh হলে rejection,
ঠিক code/path; mixed violation order; invalid→fresh repair; all-invalid budget stop;
fresh default success; reference_inputs preserved; raw output অপরিবর্তিত; existing
provider exceptions/retry limits বহাল। Targeted repair/mock-planner/StoryPlan suites
চালাবে; API/DB/UI বা schema export change প্রয়োজন নেই।

## Outcome ও authorization

Review-তে blocker নেই। **Owner-এর পরবর্তী নির্দেশে fresh-plan guard + tests সম্পন্ন;
[checkpoint](planner-fresh-plan-checkpoint.md)।** Cast/traits fidelity, semantic acceptance, live-provider lifecycle
ও API integration বাকি থাকবে; এই guard সেগুলো সমাধান করবে না। বন্ধ model experiment
queue বহাল; run/download/retry নয়।

Docs links, RESUME <60 lines, ledger/status/scope, plan drift ও whitespace checks
PASS। Source/schema/master/assets অপরিবর্তিত; app tests পুনরায় নয়; commit হয়নি।
