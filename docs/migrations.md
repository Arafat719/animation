# SQLite migration checkpoint — micro-step 1.6

Date: 2026-09-07

## Operation

`animation_studio.persistence.db.init_db(path)` applies Alembic revisions using
a single explicit SQLite transaction. Existing API calls already invoke this
function, so no API endpoint or project schema change is required.

For an explicitly selected database, from the repository root:

```bash
.venv/bin/python -c "from animation_studio.persistence.db import init_db; print(init_db('data/animation.db'))"
```

The first revision, `0001_initial`, creates projects, characters, voices, shots,
and render_jobs. It adopts existing tables only if SQLite column metadata
(names, order, types, nullability, defaults and primary keys) matches the frozen
baseline. It does not rebuild existing tables or change their rows. Additional
indexes, triggers and table constraints are not exhaustively validated.

Schema changes and the revision marker commit together. Migration exceptions
roll back both. `BEGIN IMMEDIATE` serializes database writers; an in-process
lock also protects Alembic's shared environment context. Unknown revisions
fail without being overwritten. The API still uses its existing sqlite3 queries;
SQLModel conversion and new canonical model fields are outside this step.

## Recovery and future revisions

- Before applying a future schema change to valuable data, stop the local API
  and make a verified SQLite backup. Keep the backup outside Git.
- On an incompatible legacy schema or unknown revision, inspect the database
  and use the correct code version. Do not manually stamp an incompatible
  database or delete the version table to force an upgrade.
- A failed transaction may leave an empty database file when starting from
  scratch; it does not leave partially committed migration tables.
- Destructive downgrade is deliberately unavailable. Restore a verified backup
  with the API stopped if rollback to an older application version is needed.
- Keep `0001_initial.py` and `tests/fixtures/legacy_schema.sql` frozen. Add future
  numbered revisions under `animation_studio/persistence/migrations/versions`,
  linking `down_revision` to the previous revision. Each must have migration,
  data-preservation and failure tests.
- Migrations are invoked programmatically; there is no standalone alembic.ini,
  ORM autogeneration setup or offline SQL generation in this step.

## Verification

- Before changes: 17 tests passed.
- Migration suite: 7 tests passed, covering empty creation/version tracking,
  legacy rows and API reads, repeated initialization, rollback/retry, unknown
  revision rejection, concurrent initialization and special-character paths.
- Isolated Python 3.12 environment: pinned dependencies installed, `pip check`
  and migration imports passed; full suite: 23 passed in 3.81s, with two existing
  TestClient deprecation warnings. Remote CI and Python 3.11 were not run.
- Tests use disposable databases; no user runtime database was migrated during
  implementation. Existing TestClient warnings remain separate from this work.
- Required new dependencies are pinned in requirements.txt. No model download
  or paid GPU was used.
- No Git commit was made in the already-dirty worktree. This document records
  the checkpoint; Phase 1 as a whole is not yet complete.

References: [Alembic connection sharing](https://alembic.sqlalchemy.org/en/latest/cookbook.html#sharing-a-connection-across-one-or-more-programmatic-migration-commands)
and [SQLite transactions in SQLAlchemy](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#enabling-non-legacy-sqlite-transactional-modes-with-the-sqlite3-or-aiosqlite-driver).
