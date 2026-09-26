# Offline planner repair runner — checkpoint

2026-09-23। Owner “tahole porer tai koro, offline repair runner ar jeta ase”
বলে [নির্দিষ্ট micro-step](planner-repair-gap-review.md) অনুমোদন করেছেন; সম্পন্ন।

[planner_repair.py](../animation_studio/providers/planner_repair.py)-এ পৃথক
RepairProvider protocol ও repair_plan utility আছে। Strict max_retries 0–2,
default 0; মোট provider calls সর্বোচ্চ 1 + max_retries। Request প্রথমে revalidate,
প্রতিটি call-এ independent deep copy। Invalid config/request-এ call হয় না।

Generate/repair output existing StoryPlan JSON validator পেরোয়; request duration
1e-6 absolute tolerance-এ মিলতে হয়। INVALID_JSON/INVALID_PLAN/DURATION_MISMATCH
code ও tuple path-সহ feedback এবং অপরিবর্তিত previous output repair call-এ যায়।
Runner নিজে JSON বা গল্প patch করে না। Exhaustion-এ RepairExhausted attempts/issues
রাখে; candidate দেয় না। Provider exceptions propagate; non-string output TypeError;
কোনোটিতে retry নয়। Success-এ validated plan/attempts এবং REVIEW_REQUIRED।

## Validation

[নতুন tests](../tests/test_planner_repair.py) ২৯ cases এবং existing mock-planner/
StoryPlan suites মিলিয়ে **৬৯ PASS**:

```sh
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_planner_repair.py tests/test_mock_planner.py tests/test_story_plan.py
```

First-pass success, malformed/schema/reference/timeline failure, requested-duration
mismatch, latest repair feedback, 0/1/2 retry exhaustion, invalid config/input,
generate/repair exceptions ও non-string outputs, nested mutation isolation এবং
independent success results যাচাই। Fixture output real model evidence নয়।
Document links/RESUME/status/scope/plan drift/whitespace checks PASS।

## সীমা ও recovery

API/DB/UI এবং existing provider/schema অপরিবর্তিত; নতুন utility production flow-এ
সংযুক্ত নয়। Network/persistence/backoff/real timeout enforcement নেই; narrative,
traits fidelity ও human acceptance যাচাই করে না। Frozen result-এর plan নিজে mutable;
পরে edit করলে আবার validation প্রয়োজন। Phase 3/3.10 complete নয়।
CPU-model experiment queue বন্ধ; নতুন run/download হয়নি। Existing unrelated edits
সংরক্ষিত; commit হয়নি। এই micro-step-এ blocker নেই। পরবর্তী bounded কাজ:
API wiring-এর আগে offline request-fidelity gap review (supplied cast/traits ও fresh
plan lifecycle); এখনও অনুমোদিত নয়। Live provider/retry integration পৃথক scope।
