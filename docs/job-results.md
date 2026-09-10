# Persisted provider outcomes

Migration `0002_job_results` adds `job_results`, linked to existing render jobs.
The original revision and legacy schema fixture remain frozen. No existing
project, job, character, voice or shot row is rewritten by the new revision.
The migration fails on a pre-existing conflicting table instead of adopting it.
DDL and the revision marker use the existing transactional migration runner.

`JobResultRepository` requires an explicit database path and applies migrations
on construction. Its resolved absolute path stays fixed across later cwd changes.
Normal API database access already calls `init_db`, so it will also apply this
revision on the next database use. Follow the backup procedure in `migrations.md`
before applying a new revision to valuable data. No live user database was
migrated during this implementation.

```python
from animation_studio.persistence.job_results import JobResultRepository, StoredError

repository = JobResultRepository('/absolute/path/to/animation.db')
# job_id must already exist; result is the validated FakeProvider result.
saved = repository.save_success(job_id, result)
same = repository.save_success(job_id, result)  # Identical retry returns saved.
restored = repository.get(job_id)

# For a different job that failed:
repository.save_error(failed_job_id, StoredError(code='timeout', message='Deadline exceeded'))
```

Each row contains schema version 1, creation time and exactly one success result
or normalized error. Success JSON retains all image/audio/video paths, checksums,
durations, provider/model names and versions, and seed. Version 1 currently accepts
the fixture provider's `FakeResult` contract. Future provider/schema versions need
explicit compatibility work rather than silently changing stored interpretations.

The repository revalidates model instances and dictionaries. It requires matching
artifact kinds, absolute paths and positive audio/video durations. Metadata is
validated, but files are not opened, copied or rehashed by persistence. Reading a
result therefore does not prove that its source media still exists or is unchanged.
Corrupt stored JSON/schema data raises a validation error; it is not hidden or
replaced. Errors use the provider's current normalized codes and a required message
up to 2000 characters. Callers should provide appropriate diagnostic messages.

`get` returns `None` for an existing job without an outcome; unknown jobs raise
`UnknownJobError`. IDs must be positive integers. All outcomes are immutable:
identical writes return the existing record without changing its creation time;
different success/error writes raise `JobResultConflictError`. Replacing a stored
failure on a future retry needs a separate attempt design.

Save uses a short `BEGIN IMMEDIATE` transaction, a primary key on job_id and bound
SQL values. Concurrent identical retries converge on one record; conflicting
writes preserve the first committed record. Repository connections enable SQLite
foreign keys. Other direct SQLite clients must enable foreign keys themselves.
SQL constraints reject missing/both outcome branches, unknown schema versions and,
with foreign keys enabled, orphan results.

This module only stores outcomes: it does not execute providers or change job
state/progress. It accepts any existing job ID. `FakeJobRunner` now coordinates
completion/cancellation and saved outcomes atomically; see `fake-runner.md`.

## Read API

`GET /jobs/{job_id}/result` reads the stored outcome through the local FastAPI app:

- HTTP 200 with `SavedOutcome` JSON when a success or failure has been saved.
  It includes schema version, creation time, provider metadata and either the
  result or normalized error. Artifact paths serialize as strings.
- HTTP 200 with JSON `null` when an existing job has no saved outcome. This also
  applies to old completed demo jobs: completion alone does not imply media exists.
- HTTP 404 for an unknown positive job ID; HTTP 422 for invalid/nonpositive IDs.
- HTTP 500 with a Bangla message if stored outcome JSON/schema is corrupt.
  The invalid record is preserved for diagnosis, and validation details are not
  included in the response. Other storage failures propagate as server errors.

Reading does not start a provider or advance/cancel jobs. The existing database
initialization still applies outstanding migrations. Results contain local file
metadata, not public media URLs; this endpoint does not serve files, rehash them,
or establish that they still exist. This remains an owner-only local API.
Background dispatch and browser result display are now implemented. The separate
[artifact API](artifact-serving.md) checks file availability/hash and serves bytes;
browser preview/download controls now use that API (step 1.13).

Validation commands (repository root, temporary databases):

```bash
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_job_results.py tests/test_db.py
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider
```
