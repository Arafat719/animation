# Phase 1 follow-up — typed settings checkpoint

Date: 2026-09-08

Added a frozen Pydantic Settings model in animation_studio/settings.py using
existing dependencies. ANIMATION_DB_PATH is loaded explicitly from the process
environment, without an implicit .env loader or cache. The current settings
scope is the database path; future settings should be added with validation.

Both API connections and init_db now use the same path resolver. The default
is repository-relative data/animation.db, independent of the working directory.
Explicit relative environment paths retain working-directory semantics for
compatibility. An explicit init_db(path) overrides the environment. Existing
databases elsewhere are not moved; configure their absolute path to reuse them.

Validation rejects blank/null-byte paths, existing directories, in-memory SQLite
and SQLite URIs. API lifespan checks configuration before serving requests.
Settings loading and health checks create no database or directory. Invalid
configuration does not silently fall back to the default database.

Verification:

- Baseline: 25 backend tests passed.
- Final suite: 36 passed in 4.54s; two existing TestClient deprecation warnings.
- Added checks for default-path independence from cwd, shared API/migration
  environment overrides, fresh environment reads, legacy relative paths,
  explicit precedence, invalid paths, and startup/health without file creation.
- The null-byte test was corrected to use explicit path input because the OS
  rejects null bytes in environment variables before application validation.
- git diff --check passed. No schema or frontend change; browser tests were not
  rerun in this step. Python 3.11 and remote CI were not run.

Files changed: animation_studio/settings.py, animation_studio/persistence/db.py,
apps/api/main.py, tests/test_settings.py, README.md and this checkpoint.
No install, user database migration, model download, GPU action or Git commit.

This closes the typed database-settings gap identified in the Phase 1 audit.
The remaining detailed requirements still include Project Workspace,
Characters/Voices/Settings pages, the fixture-returning fake provider,
structured logging, formatters and one-command startup. Handle each as a
separate approved step before declaring the full phase complete.
