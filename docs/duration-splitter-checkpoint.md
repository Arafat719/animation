# 3.3 — duration splitter

2026-09-19: bounded step PASS.

`animation_studio/domain/duration.py` validates finite numeric 30–60 second
requests and returns equal durations for max(6, ceil(total / 6)) shots. This
produces 6–10 shots, each 3–6 seconds, without rounding or clamping the request.
Floating-point totals satisfy StoryPlan's 1e-6 second tolerance; these are planning
seconds, not frame-quantized media durations.

`PlannerRequest.duration_seconds` defaults to 30. The mock planner uses the
splitter, extending its middle placeholder beat for longer plans and retaining
its closing beat. Default 30-second IDs/seeds and six five-second shots remain
compatible with step 3.2. Different requested durations affect plan identity.
No persisted schema or API payload changed; no migration is needed.

Validation: 88 targeted tests PASS (48 duration tests plus 40 prior planner/schema
cases). The tests sweep all 30,001 millisecond targets, check immediate floating
neighbors at shot-count boundaries, valid StoryPlan round trips and deterministic
outputs across requested durations, invalid values, and default compatibility.
Command: `PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_duration_splitter.py tests/test_mock_planner.py tests/test_story_plan.py`.
Formatting of three touched Python files and 19 published schema checks PASS.
Full app regression was not rerun for this isolated planning change.

No real AI, GPU, API/UI integration or production provider lifecycle added.
Next: 3.4 character traits injection; Phase 3 remains incomplete.
