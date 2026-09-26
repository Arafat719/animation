# Fresh-plan lifecycle guard — checkpoint

2026-09-23। Owner “ok porer kaj koro” নির্দেশে [নির্দিষ্ট step](planner-request-fidelity-review.md)
অনুমোদিত ও সম্পন্ন। [repair_plan](../animation_studio/providers/planner_repair.py)
এখন schema ও requested-duration checks-এর পরে shot lifecycle পরীক্ষা করে।

প্রতিটি shot pending, attempts=0, error=None এবং keyframe/raw/lip-synced paths=None
হতে হবে। Violation-এ NON_FRESH_PLAN ও ('shots', index, field) path; shot order ও
status/attempts/error/keyframe/raw/lip field order স্থির। Raw output reset/strip নয়;
existing retry budget-এ feedback, exhaustion-এ RepairExhausted। Duration mismatch
precedence বহাল; fresh candidate-ও REVIEW_REQUIRED। Reference inputs অক্ষত থাকে।

## Checks

[Tests](../tests/test_planner_repair.py)-এ ১৫টি নতুন case: প্রতিটি nonfresh field ও
সব non-pending status, shared-schema validity, mixed diagnostic order, raw-preserving
repair, 0/1/2 retry exhaustion, duration precedence, fresh defaults/reference inputs।
৪৪ repair + ৪০ existing mock-planner/StoryPlan = **৮৪ tests PASS**:

```sh
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_planner_repair.py tests/test_mock_planner.py tests/test_story_plan.py
```

Document links/RESUME/status/scope/plan drift/whitespace PASS। Recent ৬৯-test baseline
আগের checkpoint থেকে reuse হয়েছে। Public schema/PlanStore/API/DB/UI বদলায়নি;
full app suite নয়। Model run/download/commit হয়নি; unrelated edits সংরক্ষিত।

## সীমা ও next step

Guard নতুন plan boundary-তে; persisted/resumed lifecycle schema-valid থাকে।
Supplied cast/traits fidelity, narrative/human acceptance, live timeout/cancellation
ও API wiring এখনও বাকি। এই micro-step-এ blocker নেই। পরের bounded কাজ:
supplied cast ID/name preservation-এর policy ও tests নির্ধারণ; অনুমোদন pending।
Traits injection-এর ownership/duplication আলাদা design সীমা; এখন blind injection নয়।
CPU-model experiment queue বন্ধ এবং Phase 3/3.10 অসম্পূর্ণ বহাল।
