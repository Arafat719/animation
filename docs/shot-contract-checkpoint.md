# Persisted Shot checkpoint — 1.17d

Date: 2026-09-15. **1.17d complete; full Phase 1 / 1.17 remains PARTIAL.**
Next bounded step: **1.17e RenderJob baseline**.

## Implementation

- Add versioned `ShotRecord` for all six existing SQLite columns, strict/frozen,
  with required nullable status and finite numeric durations.
- Publish `shot.record.schema.json` through the existing registry and drift gate;
  ten schemas now cover Project, Character, Voice and persisted Shot.
- Preserve current SQL semantics: raw prompts/status, non-positive durations,
  duplicate order indexes and project IDs without referential constraints.
- Document SQL defaults, numeric boundaries and future planning scope in the
  [Shot contract](contracts/shot-v1.md). No API endpoint or migration was added.

## Verification

- **324 backend tests PASS**, including **17 new Shot cases**, with three existing
  dependency deprecation warnings; 30.32 seconds.
- Command: `DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -o faulthandler_timeout=30`.
- Independent legacy and actual 0001/0002/0003 revision fixtures: repeated upgrades,
  reopened reads, exact field preservation and JSON serialization PASS.
- Defaults, missing keys, immutability, strict types, extra fields, non-finite
  numeric rejection and missing/stale schema detection PASS.
- All ten schemas match models and are copied byte-for-byte into the web build.
- Frontend lint, typecheck/build, frontend/backend incremental formatters PASS.
- Initial sandbox suite stalled in existing TestClient startup and was interrupted;
  the complete suite above passed with the approved sandbox escalation.

No UI/API source changed in this step. Live schema HTTP and browser regression
were not repeated; they remain part of the final Phase 1 gate. User runtime
SQLite files were not opened or migrated. Earlier Voice changes remain in the
working tree. The previously reported Git object issue was not repaired here.

This completes a persisted baseline only. RenderJob baseline, Project NULL-status
compatibility and the final regression gate remain. Strict StoryPlan/ShotPlan,
shot APIs and resumable planning behavior belong to their later feature steps.
