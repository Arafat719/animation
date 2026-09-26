# Offline traits helper — checkpoint

2026-09-23। Owner “ok porer kaj koro” নির্দেশে [design](planner-traits-assembly-design.md)
implementation সম্পন্ন। [planner_traits.py](../animation_studio/providers/planner_traits.py)-এ
assemble_planner_traits raw base JSON ও validated profile snapshots নেয়; base_json ও
assembled_json immutable strings-সহ frozen REVIEW_REQUIRED result ফেরায়।

Supplied ID/name/duplicate profile checks; সব prompt field-এ supplied canonical blocks
আগে থাকলে TRAITS_ALREADY_PRESENT। Existing injector একবার প্রয়োগ; visible-only
visual/negative traits ও existing visibility order। Overflow-এ TRAITS_ASSEMBLY_INVALID
ও validator paths; truncation নয়। Profile mismatch typed error; invalid input-এর
ValidationError propagate। Base normalized JSON, original provider bytes নয়।

[নতুন tests](../tests/test_planner_traits.py)-এর ২১ case: visible/offscreen/extra cast,
Bengali/multiline blocks, immutable snapshots ও deterministic repeat, no-op reassembly,
helper/mock preassembled rejection, cross-field invisible-profile duplication,
profile mismatch, তিন prompt field-এর 4000 boundary/overflow ও invalid inputs।
Existing ১১১-সহ **১৩২ targeted tests PASS**:

```sh
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_planner_traits.py tests/test_character_traits.py tests/test_planner_repair.py tests/test_mock_planner.py tests/test_story_plan.py
```

Docs links/RESUME/status/scope/plan drift/whitespace PASS। Existing injector/mock,
runner/API/DB/UI/shared schema/master অপরিবর্তিত। Model run/download নয়; unrelated
edits সংরক্ষিত; commit হয়নি।

Blocker নেই। Exact reserved-block detection semantic dedup নয়; matching literal
base text-ও reject হতে পারে। Helper freshness/duration/narrative approval পরীক্ষা
করে না; runner guards পৃথক। Phase 3/3.10 অসম্পূর্ণ, CPU experiment queue বন্ধ।
পরের bounded কাজ: repair runner-এ traits assembly integration-এর error/retry policy
নির্ধারণ—raw feedback ও overflow behavior-সহ; অনুমোদন pending। API wiring নয়।
