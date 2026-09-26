# Micro-step 1.17a — versioned Project baseline

Date: 2026-09-14. **1.17a PASS; full Phase 1 / 1.17 PARTIAL.** The
[opening Phase 1 audit](phase-1-audit-2026-09-14.md) identified four further entity
baselines and persisted/API compatibility gaps before the final regression gate.

Moved the existing Project request/response classes into
`animation_studio/domain/v1/project.py` and imported them in the API. Added a
strict, complete `ProjectRecord` for the seven persisted columns, preserving
nullable values and raw timestamps without imposing create-request limits on
old records. Published three matching JSON Schema files under the web app's
`/schemas/v1/` path, with a deterministic generator and read-only CI drift check.

The [Project contract](contracts/project-v1.md) explains versioning, API defaults,
coercion and title normalization, SQL defaults/nullability, strict record limits,
and future feature fields. No endpoint, API payload, default, SQL column or
migration changed. A known SQL NULL status versus non-null API status mismatch
is documented and tested; its API failure remains a prerequisite gap for 1.17.

Files changed in this step:

- `animation_studio/domain/{__init__,v1/__init__,v1/project}.py` and
  `apps/api/main.py` — versioned models and API imports.
- `scripts/export_schemas.py`, `apps/web/public/schemas/v1/*.schema.json`,
  `.github/workflows/ci.yml` — publication and drift check.
- `scripts/check_format.py`, `.prettierignore`, `.format-baseline.json` — generated
  schemas use their own check; the edited API module now passes Ruff, so its old
  checksum allowance was removed rather than refreshed.
- `tests/test_project_contract.py`, `tests/test_format_check.py` — 21 new Project
  cases and generated-schema exclusion coverage.
- README, contract/audit/checkpoint/formatting docs, master plan and status ledger.

Verification:

- Full backend suite: **274 passed**, Python 3.12.3, in 29.17 seconds. Three
  dependency deprecation warnings: the two previously known TestClient warnings
  plus an existing HTTP 422 constant newly exercised by whitespace-title coverage.
- Upgrade/read preservation from an independent legacy schema and each of the
  actual 0001/0002/0003 revisions: PASS. Repeated initialization preserved exact
  Project rows and API-readable legacy values, including out-of-create-range
  durations, raw timestamps and whitespace/long/empty titles.
- Complete typed-record defaults/nullability/strictness, API coercion/defaults,
  title trimming/rejection, input boundaries and exact response keys: PASS.
- Existing NULL-status API failure explicitly reproduced; record/SQL values
  remain unchanged. This is recorded debt, not a successful API read claim.
- Before/after full OpenAPI comparison: identical. AST comparison of the API
  against its prior source: identical executable behavior apart from relocating
  the two Project classes and adding their import. Single-file formatting was
  required by the existing modified-file gate; no unrelated source was formatted.
- Export drift check and missing/modified/unexpected-file negative checks: PASS;
  check mode did not create or rewrite files. Published API schemas match their
  OpenAPI components after accounting for omitted null-default annotations.
- Frontend lint, strict TypeScript and production build: PASS. All three schema
  files were copied byte-for-byte into `dist`.
- Actual Vite preview on an ephemeral loopback port: all three schema URLs
  returned HTTP 200, `application/json`, and exact source bytes; server stopped.
- Backend/frontend formatter checks: PASS (21 Python files checked, 28 legacy
  allowances; 6 frontend files checked, 14 allowances). `git diff --check`: PASS.

Full backend command:

```bash
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
```

Tests and Vite preview used automatically approved local execution outside the
sandbox and disposable data. No user runtime database was opened/migrated; no
dependency installation, model/GPU use, deployment or commit occurred. Existing
user UI edits were preserved. Remote CI, Python 3.11 and the complete browser
refresh/cancellation/restart gate were not rerun here; that final gate follows
the remaining baseline/compatibility work.

Next bounded step: **1.17b — Character baseline contract and matching schemas**.
Current authorization permits continuing Phase 1. The audit lists 1.17c–1.17f
and the final gate; no Phase 2 work is authorized by this checkpoint.
