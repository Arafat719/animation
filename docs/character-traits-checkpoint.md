# 3.4 — character traits injection

2026-09-19: bounded step PASS.

`PlannerRequest.characters` accepts explicit `PlannerCharacter` profiles with
unique IDs, names, nonempty visual traits and optional negative traits. The mock
places the supplied cast in every template shot. Empty profiles retain the prior
placeholder behavior and default IDs/seeds. Supplied profiles affect the request
fingerprint, so changing traits changes shot identity.

`inject_character_traits` returns an independent validated StoryPlan. It appends
named/ID-labelled visual traits to image and motion prompts and negative traits
to negative prompts, following visible-character order. Offscreen dialogue does
not trigger visual injection. Call once on base prompts; repeated injection is
not an edit/rebuild API. Missing profiles leave the original prompts unchanged.
Duplicate or unknown profile IDs are rejected. Final prompt length violations
raise ValidationError rather than truncating traits or user input. Provider entry
revalidates nested profiles, including unchecked/mutated request models.

No persisted Character, StoryPlan, ShotPlan or API schema changed, so no database
migration is required. Existing profile-free requests and legacy StoryPlan JSON
remain readable; the existing schema snapshot tests cover published contracts.
Traits are caller-supplied text, not extracted semantic profiles or a consistency
guarantee. Full CharacterProfile persistence/extraction belongs to Phase 5.

Checks:
- Baseline: 88 targeted tests PASS.
- Final: 99 targeted tests PASS with
  `PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_character_traits.py tests/test_mock_planner.py tests/test_story_plan.py tests/test_duration_splitter.py`.
- Coverage: exact Unicode prompt output, 30/45/60s plans, visibility, offscreen
  dialogue, input preservation, changed-trait identity, invalid/duplicate/unknown
  profiles, boundary revalidation, overflow and previous request compatibility.
- `.venv/bin/python -m scripts.export_schemas --check`: 19 snapshots PASS.
- Ruff formatting check for both touched Python files PASS.

No real AI, GPU, full regression, UI/API integration or trait storage added.
No blocker; existing dirty work preserved and no commit created.
Next authorized micro-step: 3.5 pipeline state machine; not started this turn.
