# 5.7d — explicit saved-character mock preview API

2026-10-12। RESUME-এর অনুমোদিত bounded integration সম্পন্ন। Existing workspace draft
পুনর্লিখন ছাড়া review/verification এবং missing selection coverage সম্পন্ন।

## Behavior

- `POST /projects/{project_id}/mock-plan` accepts `{"character_ids": [1, 2]}`।
- 1–100 unique strict positive signed-64-bit IDs; caller order preserved।
- Repository থেকে saved snapshot read → existing adapter → MockDraftProvider/PlannerService।
- Unknown project/character: 404; missing profile: 409; corrupt stored profile: sanitized
  500; invalid request/project values/assembled prompt overflow: 422। No planner retry।
- Snapshot name/traits ব্যবহৃত; no auto cast/name matching। Default duration 30 seconds।
- Response `plan`, `is_mock: true`, `status: REVIEW_REQUIRED`; shots remain pending।
- Existing GET no-cast endpoint অপরিবর্তিত। No project assignment, plan save/approval,
  generation/job creation। Existing init_db migration behavior retained; unchanged-DB
  evidence applies to initialized database, not first-use migration-free operation।

## Files and checks

[Router](../apps/api/character_preview.py), [registration](../apps/api/main.py),
[17 API cases](../tests/test_character_preview_api.py)। This turn added selected-only
snapshot identity/default duration and mixed valid/unknown rejection checks to draft tests।

```sh
.venv/bin/python -m pytest -q tests/test_character_preview_api.py tests/test_character_profile_adapter.py tests/test_character_profiles_persistence.py tests/test_character_profile.py tests/test_character_traits.py tests/test_planner_traits.py tests/test_mock_plan_api.py tests/test_planner_service.py
```

**118 PASS**, 2 existing TestClient deprecation warnings। Sandbox runs blocked inside
AnyIO TestClient portal during fixture's initial project POST; interrupted all three.
Same suite passed with approved outside-sandbox execution in 4.95s, bounded by timeout 90.
Ruff check/format, plan excerpt drift and whitespace checks PASS। No dependency changes。
Tests use temporary databases; full DB dumps prove initialized persistent state unchanged
on successful preview and tested failures। Unicode, determinism, selected order, explicit
subset, saved name, no retry/partial planning, bad types/duplicates/limits, corruption,
legacy GET compatibility covered। No real inference or visual acceptance claimed。

## Next and limits

এই bounded integration সম্পন্ন। পরের candidate: GPU-free remaining-scope review to
identify the next independent micro-step; further feature implementation requires scope
approval। Description-to-traits extraction, reference conditioning, real image generation,
UI selection and persistent project assignment not completed here। Full 5.7/Phase 5
অসম্পূর্ণ; GPU gates deferred, unchanged hardware probe পুনরায় নয়।
