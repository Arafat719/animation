# Phase 3 — integrated offline acceptance

2026-09-25। Owner Phase 3-এর বাকি offline কাজ শেষ করে Phase 4 ধরতে বলেছেন;
পরবর্তী “ok kaj shesh koro” নির্দেশে interrupted verification সম্পন্ন।
**Offline integration ও acceptance PASS; পূর্ণ Phase 3 এখনও BLOCKED at real planner।**

## কী সম্পূর্ণ হয়েছে

[PlannerService](../animation_studio/providers/planner_service.py) এখন application-এর
mock preview path-এ ব্যবহৃত। MockDraftProvider unassembled base দেয়;
[MockPlanner.base_plan](../animation_studio/providers/planner.py) stable IDs/timeline
রেখে base তৈরি করে। Existing MockPlanner.plan-এর assembled behavior অক্ষত।

[Repair runner](../animation_studio/providers/planner_repair.py) schema → requested
duration → fresh lifecycle → supplied cast → traits assembly করে। Traits duplicate
বা overflow একই max_retries budget-এ feedback দেয়; provider-এর raw response-ই পরের
repair input, assembled plan নয়। Missing/impossible visible-trait room-এ cap শেষে
fail; text truncate বা traits বাদ নয়। Unexpected helper/provider failures propagate।
Result-এ normalized base_json ও independently validated assembled plan আছে;
status REVIEW_REQUIRED—automatic approval নয়।

[API](../apps/api/main.py)-র /mock-plan এবং unsaved /plan preview service ব্যবহার করে,
max_retries=1 (সর্বোচ্চ দুই mock calls)। Exhaustion → 422 PLANNER_OUTPUT_INVALID,
attempt count ও code/path; failed preview database বদলায় না। Saved-plan approval,
revision invalidation ও render gate পূর্বের মতো বহাল। কোনো live provider যুক্ত হয়নি।

## Acceptance evidence

| Gate | ফল / evidence |
| --- | --- |
| Deterministic valid mock | PASS; একই input/seed ও Bengali 30/45/60s, traits-সহ service পুরোনো mock-এর সমান |
| Invalid output reject/repair + cap | PASS; schema/traits failure chain এক budget; raw-only feedback; impossible traits bounded stop |
| Requested duration / cast / freshness | PASS; existing guard tests retained |
| Traits in relevant shots | PASS; visible-only assembly, no double injection, overflow rejection |
| Shot failure resume | PASS; checkpoint runner restart ও completed shots অক্ষত |
| API read-only/error path | PASS; repaired preview ও exhaustion 422, database unchanged |
| Save/approve/render gate | PASS; revision conflict, edit invalidation, approval ছাড়া executor call নেই |
| Browser shot-list flow | PASS; loading/empty/error/mobile, edit/save retry, approve/reload/mock-render |

**২৫২ targeted tests PASS**, ২ existing dependency deprecation warnings:

```sh
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_planner_service.py tests/test_planner_repair.py tests/test_planner_traits.py tests/test_character_traits.py tests/test_mock_planner.py tests/test_story_plan.py tests/test_duration_splitter.py tests/test_mock_plan_api.py tests/test_plan_approval.py tests/test_pipeline_state.py tests/test_mock_shot_runner.py
```

`npm run build` (apps/web): typecheck/build PASS।
`node scripts/check_shot_list.mjs`: browser acceptance PASS; controlled fixtures,
actual backend gate আলাদা TestClient tests-এ covered। Tests temporary DB ব্যবহার করে।
Touched Python files formatting PASS; targeted lint-এ দুই import-order issue সংশোধিত।
Document links/RESUME/status/scope/plan drift/whitespace PASS। Public schema বদলায়নি;
StoryPlan tests-এর schema checks PASS। Full application/media regression চালানো হয়নি।

আগের sandbox TestClient আটকে যাওয়ায় সেই process interrupted; escalation প্রথমে
usage-limit auto-review rejection পেয়েছিল। Owner-এর পুনরায় নির্দেশের পরে 2026-09-25
অনুমোদিত local execution-এ উপরোক্ত সম্পূর্ণ tests ও browser check PASS হয়েছে।

## পূর্ণ phase ও Phase 4-এর সীমা

[Phase 3](plan/phase-3.md) 3.10 real planner adapter/strict output test set এখনও হয়নি।
[দুই-model decision](local-planner-owner-decision-review.md)-এ CPU experiment বন্ধ;
ছয় observed generation-এ accepted plan ০। Offline scripted repairs real narrative
quality, Bengali model acceptance বা real adapter lifecycle-এর প্রমাণ নয়।
Real-provider timeout/cancellation/health/progress/error normalization ও real-stage
recovery এখনও বাকি; local mock synchronous, external I/O নেই। Model/GPU/download/
API provider নতুন করে চালানো হয়নি। Phase 3 সম্পূর্ণ বা Phase 4 শুরু হয়েছে দাবি নয়।

Owner-এর Phase 4 implementation অনুমোদন সংরক্ষিত। 2026-09-25-এ owner পথ
নির্বাচন Codex-কে দেওয়ার পর [master-derived Phase 4](plan/phase-4.md)-এ সীমিত
phase-order revision গৃহীত: এই offline PASS দিয়ে local/mock 4.1–4.6 এগোতে পারবে,
3.10 deferred থাকবে। পরের micro-step 4.1; implementation এখনও শুরু হয়নি।
Real planner acceptance, real-resource approval ও পূর্ণ phase gates বহাল। দুই CPU
experiment স্থগিত; নতুন offline policy loop বা model run/download অনুমোদন নয়।

## Recovery

Changed: planner.py, planner_repair.py, new planner_service.py, API main.py,
repair/API tests, new test_planner_service.py এবং এই checkpoint/RESUME/ledger।
Existing helper/model evidence ও unrelated working-tree edits অক্ষত; commit হয়নি।
