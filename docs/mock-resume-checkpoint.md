# 3.6 — deliberate mock failure and resume

2026-09-19: bounded step PASS.

`MockShotRunner` executes one local dry-run step per shot, using the 3.5
transition boundary. `create` exclusively creates a checkpoint from a pristine
pending plan. Each start, completion and deliberate failure writes a validated
StoryPlan JSON checkpoint via a flushed/fsynced temporary file and atomic rename.
The initial file is created exclusively; an existing run is never overwritten.
Checkpoint contents use the existing StoryPlan schema, not a new database model.

`MockShotExecutor(fail_shot_id=...)` deliberately fails that shot's first attempt.
The runner saves its structured failure and stops. A later explicit `run` loads
the checkpoint, skips completed shots and resumes at the failed shot. The default
limit is two total attempts per shot; exhausted attempts and cancellation stop
execution. This does not introduce automatic retries or real rendering.

The integration test fails shot three after two completions, then starts a fresh
Python process with a new runner/executor. Its call trace begins at shot three,
finishes the remaining shots, preserves the first two snapshots exactly and
records attempts [1, 1, 2, 1, 1, 1]. Running the completed plan makes zero calls.

Limits: caller must guarantee one writer for the whole run. No concurrent-job
locking, database/API integration, media-stage checkpoints, output verification
or approval flow is included. The executor is mock-only and produces no media.
Unexpected executor exceptions propagate and leave the saved running state;
resume rejects that ambiguous state pending explicit reconciliation. Storage
errors also propagate. Atomic replacement protects the previous JSON on replace
failure, but directory metadata is not fsynced: power-loss durability is not
claimed. Initial creation interrupted during writing can leave invalid JSON,
which load rejects rather than replacing it or replaying work.

Validation:
- Reused unchanged 3.5 baseline: 136 targeted tests PASS.
- Final: 148 tests PASS (12 new), including cross-process resume, retry cap,
  cancellation, interrupted/corrupt checkpoints, exclusive create, save failure,
  visible unexpected exceptions and invalid attempt limits.
- Command: `PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_mock_shot_runner.py tests/test_pipeline_state.py tests/test_character_traits.py tests/test_mock_planner.py tests/test_story_plan.py tests/test_duration_splitter.py`.
- 19 schema snapshots, both new Python files' Ruff formatting, plan excerpt drift
  and `git diff --check` PASS. No schema migration required.

No full regression or real AI/GPU run. No blocker; existing dirty work preserved,
no commit created. Next authorized micro-step: 3.7 shot-list UI.
