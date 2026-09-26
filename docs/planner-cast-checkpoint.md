# Supplied cast guard — checkpoint

2026-09-23। Owner “ok porer kaj koro” নির্দেশে [policy](planner-cast-policy.md)
implementation সম্পন্ন। [repair runner](../animation_studio/providers/planner_repair.py)
এখন supplied ID/name subset সংরক্ষণ যাচাই করে। Missing ID → CAST_MISSING,
changed name → CAST_NAME_MISMATCH; request order ও output-index paths স্থির।
Schema→duration→fresh lifecycle→cast precedence বহাল। Extra/reordered cast,
empty request এবং offscreen/unused supplied cast গ্রহণযোগ্য। Existing whitespace
normalization ছাড়া fuzzy/case matching নেই; raw output edit নয়। একই retry cap;
success REVIEW_REQUIRED, exhaustion typed failure।

[Tests](../tests/test_planner_repair.py): ১৬ নতুন cases; nested mutation test-এর
fixture requested cast দিয়ে ঠিক করা হয়েছে, assertions অক্ষত। Missing/mixed/name
errors, Bengali/case/whitespace, extra/order/visibility, repaired output ও budget,
আগের checks-এর precedence covered। **১১১ targeted tests PASS**:

```sh
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_planner_repair.py tests/test_mock_planner.py tests/test_story_plan.py tests/test_character_traits.py
```

Docs links/RESUME/status/scope/plan drift/whitespace PASS। Existing ৮৪-test baseline
পূর্ববর্তী checkpoint থেকে reuse। API/DB/UI/shared schema/master অপরিবর্তিত;
model run/download নয়; unrelated edits সংরক্ষিত; commit হয়নি।

Blocker নেই। Traits injection/duplication ও narrative acceptance এখনও বাকি;
Phase 3/3.10 অসম্পূর্ণ। পরের bounded কাজ: raw base prompts ও caller traits assembly-এর
ownership নির্ধারণ, duplicate injection/overflow policy-সহ design review; অনুমোদন
pending। Runner live provider/API-তে সংযুক্ত নয়; CPU experiment queue বন্ধ।
