# 3.2 — deterministic mock planner

2026-09-19: PASS for the bounded fixed-mock step.

`animation_studio/providers/planner.py` adds a synchronous `PlannerProvider`
Protocol, strict frozen `PlannerRequest`, and `MockPlanner.plan(request)`.
The request accepts a whitespace-normalized prompt (1–4000 characters) and an
unsigned 32-bit seed (default 0). Unknown fields and invalid inputs are rejected.
The provider revalidates requests and constructs schema-validated StoryPlan output.

The fixed template returns six five-second shots, one placeholder character,
empty dialogue, and the supplied prompt as logline/image prompt. It does not
interpret the story. SHA-256 of the normalized request and shot order determines
stable shot IDs and seeds; calls return independent mutable result objects.
There is no network, model download, persistence, API/UI wiring or GPU cost.

Validation: 40 tests PASS (16 mock-planner cases + 24 existing planning cases),
including Unicode/max-length input, invalid requests, mutation isolation and
repeatability in separate processes with different Python hash seeds. Formatting
of both new Python files and all 19 published contract schemas PASS.
Command: `PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_mock_planner.py tests/test_story_plan.py`.
No full application regression was run for this isolated provider addition.

Limits: custom duration splitting (3.3), character traits (3.4), output repair/
retry, pipeline state, UI approval and real adapters remain future work. The
minimal planning boundary is not the complete production provider lifecycle:
health checks, timeout/cancellation, progress/error normalization and model
metadata envelopes must be added before real-provider integration. The mock
currently executes synchronously without external I/O.

Next bounded step: 3.3 duration splitter. Phase 3 as a whole is not complete.
