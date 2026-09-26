# Semantic-run failure regression — ফল

2026-09-21। **অনুমোদিত offline regression micro-step সম্পন্ন।**
[Review-এর next step](local-planner-semantic-run-review.md) owner-এর পরবর্তী
“ok porer kaj suru kor” নির্দেশে কার্যকর। Model calls ০; validator policy অপরিবর্তিত।

## পরিবর্তন

Ignored `data/planner-smoke/semantic-contract-v1/`-এ:

- `fixtures/L3.json`: semantic-run-v1-এর original raw bytes হুবহু copy; repair নয়।
- `fixtures/manifest.json`: L3 origin, source path, SHA256, expected REFERENCE,
  `$.b[4].e.object` ও review record association যোগ; আগের expectations বহাল।
- `L3-review.json`: placeholder fields এবং shot 1 action/pickup mismatch-এর Codex
  textual diagnostic verdict FAIL; owner approval বা automated semantic inference নয়।
- `build_fixtures.py`: exact source hash যাচাই করে L3 পুনর্গঠন; manifest rebuild-এ
  নতুন fixture হারাবে না। Source bytes বদলালে silent refresh নয়, assertion failure।
- `test_contract.py`: তিন নতুন methods—provenance/stream/schema equality,
  rejection-before-assembly এবং reviewer evidence association।
- `regression-checks.json`: বর্তমান verification record; initial `checks.json`
  আগের ৬-test/27-fixture historical baseline হিসেবে অক্ষত।

## যাচাই

**৯ targeted test methods PASS; ২৮ fixture case expected outcome PASS; compile PASS।**
নতুন tests-এ exact error code/path-এর পাশাপাশি assembly function mock করে
`assert_not_called` যাচাই: invalid reference candidate পর্যন্ত যায় না। Original run-এর
candidate file অনুপস্থিত। Stream deltas পুনর্গঠন = fixture/raw bytes; saved request
schema = unchanged validator schema।

Raw SHA256:
`3ba4c1c736549957647f7f8ffca8e374029856689be909fbe7d3084d5dea05fd`

Validator ও আগের fixture file bytes hashes অপরিবর্তিত; পুরোনো manifest cases-এর
expected ফল বজায় আছে। Reviewer association test শুধু একই raw field/shot/hash-এর
সঙ্গে record মেলে কি না দেখে; narrative FAIL স্বয়ংক্রিয়ভাবে আবিষ্কার করে না।
Document links, RESUME <60 lines, scope/status, plan excerpt drift ও whitespace PASS।

## সীমা ও next step

Regression coverage PASS মানে known bad model output সঠিকভাবে reject হচ্ছে;
model quality PASS নয়। Original acceptance FAIL বহাল। Production source/API/DB/UI,
master, runtime harness ও raw experiment evidence অপরিবর্তিত। নতুন model run,
download, repair, budget বৃদ্ধি বা 3.10 adapter হয়নি; app tests পুনরায় নয়; commit নয়।

পরবর্তী bounded কাজ: reference, placeholder ও action-event সমস্যার জন্য পৃথক
contract/run design review—কোন পরিবর্তন কী মাপবে এবং model-authored বনাম derived
text-এর সীমা নির্দিষ্ট করা। Owner-এর পরবর্তী নির্দেশে
[design review সম্পন্ন](local-planner-contract-run-design-review.md); আরেক run বা validator policy পরিবর্তন
স্বয়ংক্রিয় নয়। Phase 3 real-adapter gate অসম্পূর্ণ।
