# 5.7b — immutable profile persistence/API

2026-10-11। Owner next-work নির্দেশে অনুমোদিত GPU-free 5.7b সম্পন্ন।
User-provided traits persist হয়; description থেকে AI extraction এখনও হয়নি।

## আচরণ

- `POST /characters/{character_id}/profile`: 5.7a CharacterProfileDraft body;
  success 201-এ character_id, schema_version=1, profile ও created_at।
- `GET /characters/{character_id}/profile`: saved snapshot, অথবা existing character-এর
  profile না থাকলে 200/null। Unknown character উভয় route-এ 404। Invalid payload/ID
  422, validation DB open-এর আগে। Positive signed-64-bit character ID প্রয়োজন।
- One snapshot per character; দ্বিতীয় POST (একই body হলেও) 409। Concurrent save
  BEGIN IMMEDIATE transaction-এ serialize হয়; no overwrite/auto retry।
- Snapshot name/description explicit supplied values; এগুলো legacy characters row
  rename/update করে না। source=user_provided, semantic agreement/AI extraction নয়।
- Separate table schema_version=1/profile_json/created_at; old opaque reference text
  parse/backfill নয়। Repository revalidates draft before connect, read-এ stored JSON
  validate করে; corrupt record-এ API bounded 500, raw private content প্রকাশ নয়।
- API update/delete route নেই। SQL UPDATE trigger reject করে। Database file-এর
  trusted owner direct delete/DDL দিয়ে বদলাতে পারেন; এটি tamper-proof storage নয়।

## Files

[Migration 0005](../animation_studio/persistence/migrations/versions/0005_character_profiles.py),
[repository/response](../animation_studio/persistence/character_profiles.py),
[API](../apps/api/character_profiles.py), [registration](../apps/api/main.py),
[new tests](../tests/test_character_profiles_persistence.py)।
Existing [DB tests](../tests/test_db.py) ও [character compatibility](../tests/test_character_contract.py)
current head 0005 অনুযায়ী update; legacy/0001/0002/0003/0004/current-head preservation
ও new table empty নিশ্চিত করা হয়। নতুন migration শুধু additive table/trigger;
legacy Character v1 response/schema ও actual existing character data বদলায় না।

## Checks

5.7a 57 PASS ও prior API/DB 78 PASS baseline reused। New 12 persistence cases;
combined **148 PASS**: profile contract/traits/planner, upload, character/API, legacy
compatibility ও DB tests। Command:

```sh
timeout 120s .venv/bin/python -m pytest -q tests/test_character_profiles_persistence.py tests/test_character_profile.py tests/test_reference_images.py tests/test_characters_api.py tests/test_character_contract.py tests/test_projects_api.py tests/test_null_compatibility.py tests/test_health.py tests/test_db.py tests/test_character_traits.py tests/test_planner_traits.py
```

Save/reopen/read, duplicate/concurrent one-winner, unknown/invalid IDs, invalid input
no DB, unchecked draft revalidation, update guard, corrupt JSON sanitized failure,
unchanged legacy API/reference fields verified। Existing two TestClient/AnyIO
warnings আছে; dependency update নয়। Known sandbox TestClient limitation-এর জন্য
API suite outside sandbox; real network/server/GPU চালানো হয়নি।
Ruff on new/formatted files, format, plan drift, docs links/RESUME ও whitespace PASS।
Master requirements unchanged; existing 5.7b scope অনুযায়ী implementation।
No install/model/paid/commit; user database migrate করার command চালানো হয়নি,
শুধু temp test databases। Existing init_db next API use-এ migration প্রয়োগ করবে।

## সীমা ও next

User-authored traits database acceptance complete; full 5.7 description-to-profile
semantic extraction অসম্পূর্ণ। UI, uploaded reference persistence/conditioning,
project-cast binding এবং real image/5.5 deferred।
পরের GPU-free micro-step candidate: saved profile থেকে existing PlannerCharacter
adapter-এর mapping/identity/length contract নির্ধারণ; completed prompt injection
পুনরায় লেখা নয়। Owner-এর GPU-free কাজ চালানোর নির্দেশ বহাল; এই turn সেই integration
শুরু হয়নি। GPU/new phase/paid launch অনুমোদিত নয়।
