# RenderJob baseline checkpoint — 1.17e

Date: 2026-09-15. **1.17e complete; full Phase 1 / 1.17 remains PARTIAL.**
Next bounded step: **1.17f SQL/API compatibility fixes**.

## Implementation

- Extract JobCreate, FixtureJobCreate and RenderJob unchanged into the v1 domain.
- Add strict/frozen RenderJobRecord covering all eight persisted columns, including
  nullable state/progress and raw timestamps omitted by API responses.
- Publish four job baseline schemas and three existing saved-outcome/provider
  schemas through the existing drift registry: 17 total schemas.
- Document SQL/API defaults, legacy versus fixture requests, nested result/error
  validators and separate result/ownership storage in the [contract](contracts/render-job-v1.md).
- Preserve existing behavior. SQL NULL state/progress failures are explicitly
  reproduced and assigned to 1.17f alongside Project NULL status.

## Verification

- **335 backend tests PASS**, including **11 new RenderJob cases**, three existing
  dependency deprecation warnings; 32.85 seconds.
- Command: `DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -o faulthandler_timeout=30`.
  Approved escalation used because prior sandbox TestClient attempts stalled.
- Independent legacy and actual 0001/0002/0003 entry points upgraded/reopened twice:
  complete record and read-only list/detail preservation PASS.
- Record strictness/defaults, missing keys, immutability, request normalization,
  differing extra-key policies and supported out-of-range legacy values PASS.
- Full OpenAPI before/after snapshot identical. All 17 exported schemas match
  source models and are copied byte-for-byte to the production web build.
- Frontend lint, typecheck/build, frontend/backend incremental formatters PASS.

No migration or user runtime database operation; no new dependency or UI feature.
Previous working-tree changes were retained. Live HTTP schema publication and
browser regression were not repeated; final Phase 1 gate remains outstanding.
The previously reported Git object problem was not repaired in this step.

Baseline publication does not fix NULL compatibility, introduce durable recovery,
implement a real provider or complete the later cost/retry/pipeline contracts.
