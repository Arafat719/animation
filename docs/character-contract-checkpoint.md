# Micro-step 1.17b — versioned Character baseline

Date: 2026-09-14. **1.17b PASS; full Phase 1 / 1.17 PARTIAL.**

Extracted the existing Character request/response models into
`animation_studio/domain/v1/character.py` and kept the API using those exact
shapes. Added a strict complete five-field `CharacterRecord`, including opaque
nullable `reference_image_paths` text and unparsed timestamp text. The shared
exporter now publishes three Character schemas alongside the three unchanged
Project schemas. Existing schema-drift CI coverage applies to all six.

The [Character contract](contracts/character-v1.md) records defaults, nullability,
required response keys, trimming before length validation, empty-description
normalization, extra-field rejection, duplicate names and the reference field's
absence from current API shapes. This is the current metadata baseline, not
character uploads, immutable traits, provenance or a project assignment feature.

Files changed in this step:

- `animation_studio/domain/v1/character.py`, `apps/api/main.py` — models/imports.
- `scripts/export_schemas.py` and
  `apps/web/public/schemas/v1/character.{create,response,record}.schema.json` —
  registered contracts and generated exports.
- `tests/test_character_contract.py` — 22 contract/migration/API cases.
- README, Character contract/checkpoint, opening audit, master plan and current
  build ledger — usage, evidence and remaining scope.

Validation:

- Full backend suite: **296 passed**, Python 3.12.3, in 33.70 seconds; the same
  three dependency deprecation warnings as 1.17a.
- Unversioned legacy schema and each actual 0001/0002/0003 revision upgraded
  through the current chain twice: exact Character rows preserved. Typed records
  and API list reads after reopening preserve supported legacy values, including
  zero ID, empty/long names, long/empty/whitespace descriptions, duplicate names,
  unusual timestamps and NULL/empty/plain-path/JSON-looking/malformed reference text.
- Complete record defaults/strictness/required keys/frozen behavior, create
  normalization and boundaries, exact response shape, extra-field rejection and
  invalid-input rejection before opening SQLite: PASS.
- Published schemas match their models; API schemas also match OpenAPI after
  accounting for omitted null-default annotations. Missing and modified Character
  exports fail read-only drift checks without being written back.
- Full before/after OpenAPI: identical. API AST: unchanged except moving the two
  Character classes into the versioned module and importing them. Project schema
  files remained byte-for-byte unchanged.
- Backend formatter: PASS, 23 checked and 28 unchanged legacy allowances.
  Frontend formatter: PASS, 6 checked and 14 unchanged legacy allowances.
- Frontend lint, strict TypeScript and production build: PASS. All six schema
  files copied byte-for-byte into the web build.
- Actual Vite preview on an ephemeral loopback port: all six schema URLs returned
  HTTP 200, `application/json` and exact source bytes. Preview stopped afterward.
- `git diff --check`: PASS.

Full suite command:

```bash
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
```

Tests and preview used automatically approved local execution outside the sandbox.
All databases were disposable; no user runtime database was opened or migrated.
No migration, dependency, formatter allowance, existing UI source, model/GPU
resource or deployment changed. No commit was created in the existing dirty
worktree. Python 3.11, remote CI and the complete browser regression gate were
not rerun.

No new incompatibility was found for supported Character text/null records.
SQLite values outside that typed domain are not silently converted or repaired.
The previously recorded Project NULL-status API failure remains; schema
publication does not resolve it.

Next bounded step: **1.17c — Voice baseline contract and matching schemas**.
Current authorization allows continuing Phase 1. Shot, RenderJob, compatibility
resolution and the final 1.17 gate remain outstanding before Phase 2.

