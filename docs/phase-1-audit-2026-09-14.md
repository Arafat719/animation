# Phase 1 gate audit — 1.17 opening / 1.17a–b

Superseded by the [2026-09-15 final PASS gate](phase-1-final-gate-2026-09-15.md).
The opening findings below are historical.

Date: 2026-09-14. **Full Phase 1 / 1.17: PARTIAL.** This is the current opening
audit; previous dated checkpoints remain historical evidence. Current code,
tests and the master plan's Section 5 baseline requirements were compared before
selecting the first bounded contract task. This is not a Phase 2 authorization.

## Section 7 tasks

| Requirement | Current evidence / remaining work |
| --- | --- |
| Skeleton and documentation | Existing `apps`, `animation_studio`, tests/scripts/docs; preserve dirty worktree |
| Health and typed environment settings | `apps/api/main.py`, `animation_studio/settings.py`, settings tests/checkpoint |
| SQLite migrations and contracts | Three revisions and existing preservation/rollback tests; Project/Character versioned baselines added in 1.17a–b, three entity baselines still missing |
| Projects, New Project, Workspace, Characters, Voices, Settings pages | Present in `apps/web/src`; existing page/browser checkpoints. Workspace remains read-only |
| Fake image/silent audio/video provider | Existing fixture provider, runner, artifact serving and sample previews. Fixed shared fixtures, not prompt-generated animation |
| Job polling and cancellation | Existing background dispatcher, persisted state/results, polling and cancellation tests; previous browser/restart evidence |
| Structured job/project/shot/step logging | Existing observability/runner/dispatcher code and logging tests/checkpoint |
| Tests, formatters, one-command startup | Existing CI checks and `scripts/dev.py`; prior startup and formatter checkpoints, plus schema drift gate in 1.17a |

## Required contract work before closing 1.17

2026-09-15 update: 1.17a–f are complete. The NULL gaps described below were
resolved by [1.17f](null-compatibility-checkpoint.md); final Phase 1 gate remains.

| Bounded step | Scope / completion status |
| --- | --- |
| 1.17a | Project persisted/request/response baseline and matching exported schemas; implemented, see [checkpoint](project-contract-checkpoint.md) |
| 1.17b | Character persisted/request/response baseline and schemas implemented; opaque `reference_image_paths` retained, absent from API; [checkpoint](character-contract-checkpoint.md) |
| 1.17c | Completed 2026-09-15: [Voice checkpoint](voice-contract-checkpoint.md), including persisted `voice_type`, API/default differences and migration reads |
| 1.17d | Completed 2026-09-15: [Shot checkpoint](shot-contract-checkpoint.md), six persisted fields and migration reads; no Shot endpoint |
| 1.17e | Completed 2026-09-15: [RenderJob checkpoint](render-job-contract-checkpoint.md); record/request/response and existing result/provider schema publication |
| 1.17f, if needed | Resolve exposed persisted/API incompatibilities without silent data rewriting; Project SQL NULL status and RenderJob SQL NULL state/progress versus non-null API fields are known failures |
| 1.17 final gate | Reconcile all required schemas/migration reads, then run the full applicable API/frontend/browser/restart/cancellation checks and report PASS only if complete |

The first baseline revealed a real existing compatibility limit: Project rows
with SQL NULL status remain readable by the typed record but fail current API
serialization. Details and regression coverage are in the
[Project contract](contracts/project-v1.md). Publishing a schema documents this
difference; it does not resolve the API failure or satisfy the final gate alone.

## Acceptance evidence limits

Prompt → sample job, progress, refresh, cancellation and restart behavior already
have dated fixture/browser checkpoints. The full browser gate will be repeated
after the remaining contracts and compatibility gaps are closed. Code presence
and a passing backend suite do not replace that final regression gate.

Schema publication requires no model download, AI execution, paid GPU, new
dependency or runtime database migration. All current checks use disposable data.
Full V1 planning/profile fields, automatic crash recovery and remote inference
remain outside this Phase 1 baseline; their required feature-phase mappings in
the master plan and ledger remain in force.
