# 5.7k — additive reviewed profile storage

2026-10-12। Owner-এর পরের কাজের নির্দেশে [5.7j](character-review-contract-checkpoint.md)
পরবর্তী bounded migration/repository সম্পন্ন; [reviewed-save design](character-reviewed-save-design.md)
এর storage অংশ অনুসৃত। API/UI writer চালু হয়নি।

## Outcome ও files

- [0006 migration](../animation_studio/persistence/migrations/versions/0006_reviewed_profiles.py)
  reviewed_character_profiles table, character FK, schema_version=2 CHECK, database-generated
  UTC created_at/reviewed_at ও no-update trigger যোগ করে। Existing v1 rows/JSON/timestamps
  rewrite হয় না; destructive downgrade নিষিদ্ধ।
- দুই table-এ insert guard এক character-এর একটিমাত্র profile রাখে। Cross-table insert এবং
  একই table-এ INSERT OR REPLACE-ও reject; পুরোনো SQL writer guard bypass করতে পারে না।
- [Reviewed repository](../animation_studio/persistence/reviewed_character_profiles.py)
  strict immutable saved wrapper, pre-open profile/context revalidation, BEGIN IMMEDIATE
  save ও snapshot transaction-এ authoritative v1/v2 read দেয়। Missing character LookupError;
  proven existing profile ProfileConflict; অন্য SQL failure conflict হিসেবে ঢাকে না।
- [Manual repository](../animation_studio/persistence/character_profiles.py) দুই table-এ
  conflict check করে; v2-only row-এ v1 reader UnsupportedProfileVersion দেয়, null নয়।
  Existing v1 schema/response shape অক্ষত। Corrupt v2 provenance/version/identity/timestamp
  অথবা দুই table-এ অবৈধ duplicate row হলে sanitized InvalidStoredProfile; fallback নয়।
- [New tests](../tests/test_reviewed_character_profiles_persistence.py),
  [DB regressions](../tests/test_db.py) ও [character compatibility](../tests/test_character_contract.py)
  current migration head অনুযায়ী update; আগের workspace changes অক্ষত।

## Checks

Prior 5.7j 118 distinct PASS baseline reused। New persistence **39 PASS**। Combined
migration/domain/manual/API/adapter/preview suite **229 PASS**, দুইটি existing TestClient
নির্ভর deprecation warning। Known sandbox TestClient limitation-এর জন্য combined suite
outside sandbox চালানো হয়েছে; নতুন repository suite sandbox-এই PASS। Command:

```sh
timeout 120s .venv/bin/python -m pytest -q tests/test_reviewed_character_profiles_persistence.py tests/test_character_review.py tests/test_character_extraction.py tests/test_character_profile.py tests/test_character_profiles_persistence.py tests/test_character_contract.py tests/test_db.py tests/test_character_profile_adapter.py tests/test_character_preview_api.py tests/test_characters_api.py
```

Verified: legacy/0001–0006 migration + repeated init, v1 JSON byte/timestamp preservation,
server timestamps, reopened read, duplicate save after committed result, both conflict
orders, two-connection concurrent manual/reviewed ও reviewed/reviewed one-winner,
SQL replace/update/FK/version guards, invalid input before DB creation, corrupt data,
failed save rollback/retry, 0005→0006 interrupted migration schema rollback/retry,
unrelated integrity error propagation ও existing v1 API/preview regressions।
Ruff on source/new tests ও updated regression tests, format on source/new tests,
plan excerpt drift, documentation links/RESUME length এবং git diff whitespace PASS।

## Limits ও next

Save একটি internal trusted-caller boundary: expected request/provider যাচাই হয়, কিন্তু
server-owned immutable draft lookup/lifetime এখনও নেই। তাই arbitrary client report
save করার endpoint হিসেবে এটি ব্যবহার করা যাবে না। No production/API call site imports
new writer; শুধু temporary test databases migrate/save হয়েছে। Existing init_db পরের
স্বাভাবিক ব্যবহারে additive migration চালাবে; user database আলাদা করে migrate করা হয়নি।

V2 writer/API/UI/adapter enable হয়নি। UnsupportedProfileVersion এখন existing v1 API-এর
InvalidStoredProfile handler-এ sanitized 500 দেয়; explicit legacy 409 mapping ও versioned
read response পরের scope। v1 API-তে v2 empty/null response হয় না। Preview-ও fail-closed;
reviewed values-এর preview ও mock-origin UI marker পরে consumer rollout প্রয়োজন।
No new install/download/model/GPU/commit। Full 5.7 ও real extraction অসম্পূর্ণ।

Next proposed **5.7l version-aware profile read API + legacy 409 guard/tests**: authoritative
v1/v2 read-এর পৃথক endpoint ও old GET-এর unsupported-version response; reviewed save,
draft lifecycle, adapter/UI integration বাদ। Owner-এর পরবর্তী next-work নির্দেশে এই
bounded implementation শুরু করা যাবে; এই turn-এ শুরু হয়নি। Trusted draft এবং consumer
prerequisites ছাড়া reviewed-save writer enable করা যাবে না।
