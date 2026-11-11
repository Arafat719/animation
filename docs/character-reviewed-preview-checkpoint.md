# 5.7n — version-aware cast preview API

2026-10-12। Owner-এর পরের কাজের নির্দেশে [5.7m](character-reviewed-adapter-checkpoint.md)
এর next bounded API/tests সম্পন্ন।

## Outcome

[Cast preview API](../apps/api/character_preview.py) existing POST
`/projects/{project_id}/mock-plan`-এ authoritative v1/v2 repository ও version-aware
adapter ব্যবহার করে। Mixed cast-এর selected order বজায় থাকে; reviewed final replacement/
omission traits plan-এ যায়, original description/report/provider data prompt-এ যায় না।

Response-এ additive `profile_origins` list: প্রতিটি selected character-এর character_id,
schema_version, source ও is_mock। Manual profile-এ source=user_provided, is_mock=null
(extraction হয়নি); reviewed profile-এ source=reviewed_extraction এবং validated report-এর
মূল provider.is_mock থাকে। এই extraction marker plan-level is_mock থেকে পৃথক:
preview এখনও সর্বদা mock এবং REVIEW_REQUIRED, shots pending। Source-discriminated
response models manual/reviewed metadata shapes আলাদা রাখে। Client origin override
পাঠালে extra-forbid request validation-এ 422 হয়।

Missing character/profile এবং corrupt reviewed provenance/schema/duplicate row-এ planner
চালানোর আগে error হয়। Existing project/prompt/overflow handling ও GET mock plan অক্ষত।
Database-এ plan/profile/job save বা approval হয় না; reviewed writer/UI চালু হয়নি।

## Checks

[New tests](../tests/test_reviewed_cast_preview_api.py): **10 cases**। Combined existing
preview API, reviewed adapter ও profile read API-সহ **84 PASS**, 2 prior TestClient
warnings। Prior 5.7m 149 PASS baseline reused। Command:

```sh
timeout 120s .venv/bin/python -m pytest -q tests/test_reviewed_cast_preview_api.py tests/test_character_preview_api.py tests/test_reviewed_profile_adapter.py tests/test_character_profile_read_api.py
```

Mixed v1/v2 mapping/order/origins, selected-only metadata, mock flag true/false preservation,
plan always mock/review-only, omitted negative traits, no raw report disclosure,
deterministic repeated requests ও full SQLite dump unchanged verified। is_mock=false
case একটি synthetic metadata fixture, real extraction evidence নয়। Corrupt JSON/hash/
version/duplicate, partial selection missing character/profile ও client override rejection
verified; errors কোনো partial plan দেয় না। Existing manual/error/overflow regressions PASS।
Known TestClient sandbox limitation অনুযায়ী outside sandbox temporary databases-এ tests;
Ruff/format, plan drift, docs links/RESUME length ও whitespace PASS। No install/GPU/commit।

## Limits ও next

UI এখনও reviewed profile selection/origin marker display জানে না; backend response
field থাকাই UI support নয়। Trusted extraction draft lookup/lifetime ও reviewed-save
endpoint বাকি; full 5.7 ও real extraction অসম্পূর্ণ। Existing UI/writer files untouched।

Next proposed **5.7o cast preview UI version-aware selection/origin labels/tests**:
versioned profile read ব্যবহার করে saved v1/v2 নির্বাচন এবং response-এর per-character
manual/reviewed/mock labels দেখানো; loading/empty/error/stale-response checks। Reviewed
profile editing/save, trusted draft store, GPU এবং নতুন phase বাদ। Owner-এর পরবর্তী
next-work নির্দেশে এই bounded implementation শুরু করা যাবে; এই turn-এ শুরু হয়নি।
