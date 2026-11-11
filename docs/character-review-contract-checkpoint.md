# 5.7j — pure reviewed-extraction v2 contract

2026-10-12। Owner-এর কাজ শুরুর নির্দেশে [5.7i design](character-reviewed-save-design.md)
অনুযায়ী bounded pure contract/builder সম্পন্ন।

## Outcome

- [Domain module](../animation_studio/domain/v1/character_review.py): explicit seven-field
  tagged accept/replace/omit decisions, strict confirmed=true, full canonical report SHA256,
  expected request/provider validation, immutable reviewed values ও v2 provenance envelope।
- Required missing/ambiguous suggestions accept নয়; replacements প্রয়োজন। Optional empty
  suggestions accept নয়; omit/replace explicit। Whole-list replacements existing trait bounds
  মেনে চলে; final strings existing whitespace normalization পায়, evidence report অক্ষত থাকে।
- Derived origins ও final values direct model validation-এও recompute/compare হয়। Nested
  unchecked copies, stale report, wrong character/context, non-bool confirmation ও non-int
  schema version reject। Fixture provenance edits-এর পরেও mock; REVIEW_REQUIRED history থাকে।
- Name/description unchanged request থেকে আসে। No DB/network/clock; v1 persistence,
  API/UI/provider execution untouched। v2 envelope saved record বা media approval নয়।

## Checks

[New tests](../tests/test_character_review.py): **40 PASS**। Combined review/extraction/manual
profile/persistence suite **117 PASS** before the final additional boundary/order case;
final new suite 40 PASS, মোট **118 distinct passing cases**। Combined command:

```sh
timeout 120s .venv/bin/python -m pytest -q tests/test_character_review.py tests/test_character_extraction.py tests/test_character_profile.py tests/test_character_profiles_persistence.py
```

Initial sandbox run stalled at existing TestClient boundary and was interrupted;
known limitation অনুযায়ী outside-sandbox rerun PASS (2 existing deprecation warnings)।
Ruff check/format, plan excerpt drift, local documentation links ও whitespace PASS।
No install/model/GPU/commit; unrelated existing changes preserved।

## Limits ও next

Hash integrity binding; provider attestation নয়। Future save must obtain report from
server-owned immutable draft, not trust arbitrary client provenance। Pure v2 contract
available; database table/migration/trusted draft lookup/version-aware consumers বাকি।
Full 5.7 বা real extraction complete নয়; GPU gates deferred।

Next proposed **5.7k additive v2 storage migration/repository**: cross-table immutable
single-profile conflict guards, backward-read/legacy preservation ও concurrency tests;
API/UI/live writer enable নয়। Owner-এর পরবর্তী next-work নির্দেশে এই bounded কাজ শুরু
করা যাবে; এই turn-এ শুরু হয়নি। Version-aware consumer ও trusted draft prerequisites
পূরণ ছাড়া reviewed-save endpoint enable করা যাবে না।
