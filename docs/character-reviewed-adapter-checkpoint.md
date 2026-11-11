# 5.7m — version-aware pure planner adapter

2026-10-12। Owner-এর পরের কাজের নির্দেশে [5.7l](character-versioned-read-checkpoint.md)
এর next bounded adapter/tests সম্পন্ন।

## Outcome

[Adapter](../animation_studio/providers/character_profile_adapter.py) এখন exact
SavedCharacterProfile v1 ও SavedReviewedCharacterProfile v2 গ্রহণ করে। V1 mapping
অক্ষত; v2 recursively revalidate করে final reviewed values থেকে একই PlannerCharacter
shape তৈরি করে। Raw dict/draft/subclass input অনুমোদিত নয়; selected identity, version,
nested values/provenance/confirmation/evidence/origins mismatch reject।

Face/hair/eyes/outfit/color/accessory order ও negative traits final values থেকে আসে;
replacement ব্যবহার হয়, omitted fields empty থাকে। Original description, extraction
suggestion/report, provider metadata ও timestamps prompt-এ যোগ হয় না। Output list
পরিবর্তনে saved snapshot বদলায় না। Full saved snapshot-এর mock provenance অক্ষত;
caller-কে UI display-এর জন্য snapshot রাখতে হবে—PlannerCharacter provenance record নয়।
No DB/network/clock/provider execution; existing API/preview/UI wiring অপরিবর্তিত।

## Checks

[New tests](../tests/test_reviewed_profile_adapter.py): **27 cases**। Pure adapter/domain
suite **102 PASS**; preview/read API-সহ combined **149 PASS**, দুইটি existing TestClient
deprecation warning। Prior 5.7l 123 PASS baseline reused। Combined command:

```sh
timeout 120s .venv/bin/python -m pytest -q tests/test_reviewed_profile_adapter.py tests/test_character_profile_adapter.py tests/test_character_review.py tests/test_planner_traits.py tests/test_character_preview_api.py tests/test_character_profile_read_api.py
```

Exact Bengali mapping, replacements/omissions/order, independent outputs, reopened JSON,
strict version/identity/nested unchecked-copy rejection, mixed v1/v2 visible-character
selection, negative omission, no raw provenance in prompts, review-only assembly status,
reassembly rejection, oversized combined prompt rejection without truncation ও no-I/O
verified। Existing v1 tests unchanged and PASS। Pure suite sandbox-এ; combined API suite
known TestClient limitation অনুযায়ী outside sandbox, temporary DB only।
Ruff/format, plan drift, documentation links/RESUME length এবং whitespace PASS।
No install/model/GPU/server/commit; unrelated workspace changes preserved।

## Limits ও next

Preview API এখনও v1 repository reader ব্যবহার করে, তাই v2 preview fail-closed থাকে।
UI mock-origin display ও server-owned extraction draft lookup/lifetime অসম্পূর্ণ;
reviewed-save endpoint enable হয়নি। Full 5.7/real extraction অসম্পূর্ণ।

Next proposed **5.7n version-aware cast preview API/tests**: authoritative v1/v2 reader
ও adapter ব্যবহার, response-এ প্রতি-character schema/source/mock-origin metadata ধরে
রাখা, mixed cast/no-write/error regressions। UI এবং reviewed-save writer বাদ। Owner-এর
পরবর্তী next-work নির্দেশে এই bounded implementation শুরু করা যাবে; এই turn-এ নয়।
UI marker ও trusted draft prerequisites ছাড়া reviewed-save enable করা যাবে না।
