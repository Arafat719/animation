# 3.5 — pipeline shot state machine

2026-09-19: bounded step PASS.

`animation_studio/domain/pipeline_state.py` adds a pure `transition_shot` boundary
using the existing StoryPlan/ShotPlan contract. It returns an independent,
schema-validated snapshot and never mutates its input, including on failure.

| Source | Allowed targets |
| --- | --- |
| pending | running, cancelled |
| running | completed, failed, cancelled |
| failed | running, cancelled |
| completed | none |
| cancelled | none |

Self-transitions and unknown targets raise IllegalShotTransition; unknown shot
IDs raise UnknownShotError. Failure requires a validated ShotError; other targets
reject error arguments. Every entry into running increments attempts and clears
the previous error. Other transitions preserve attempts. Cancellation clears any
failure error. Unaffected shots, prompts and artifact paths remain unchanged.
The caller explicitly requests retries; no automatic retry loop is added.

The existing fixture runner operates on persisted RenderJobs; it is unchanged.
This boundary handles planning shots only. It does not run providers, verify
media, enforce approval, save snapshots or serialize concurrent writers. Completed
means caller-reported success; callers must verify outputs before that event.
Existing schema-valid snapshots remain accepted; historical status/attempt
consistency is not retroactively migrated. Runtime transitions enforce the new
edge and error rules. Durable execution/resume is the next bounded step.

Validation:
- Reused the previous unchanged planning baseline: 99 tests PASS.
- Final 136 targeted tests PASS, including 37 new state tests: all 25 status
  pairs, explicit retry lifecycle, completed-shot/artifact preservation, invalid
  errors/targets/snapshots, unknown shots and independent result snapshots.
- Command: `PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pipeline_state.py tests/test_character_traits.py tests/test_mock_planner.py tests/test_story_plan.py tests/test_duration_splitter.py`.
- 19 published schema snapshots PASS; no schema/migration changes.
- Ruff format check for the two new Python files, plan excerpt drift and
  `git diff --check` PASS.

No full app regression, real AI/GPU or API/UI integration was run. No blocker.
Existing dirty edits preserved; no commit created.
Next authorized micro-step: 3.6 deliberate failure and failed-step resume.
