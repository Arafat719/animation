# RenderJob baseline v1

## 1.17f compatibility update — 2026-09-15

The response now preserves SQL NULL: Project `status`, RenderJob `state` and
`progress` accept JSON null. Omitted-field defaults and create-request validation
are unchanged. Published response schemas/OpenAPI intentionally widen these three
fields. No stored row is rewritten and no migration is needed. The UI displays
`Unknown` / `Progress unknown` and no numeric progress value for null.
The historical non-null response descriptions and HTTP 500 gap below are
superseded by this update. See [compatibility checkpoint](../null-compatibility-checkpoint.md).


`animation_studio/domain/v1/render_job.py` owns the existing `JobCreate`,
`FixtureJobCreate`, `RenderJob` API models and the complete `RenderJobRecord`.
The extraction preserves full OpenAPI and endpoint behavior. Versioning is in the
module path and schema URI, without a new payload field or route.

## Published schemas

All URLs below start with `/schemas/v1/` and end in `.schema.json`. Each document
uses Draft 2020-12 and ID `urn:animation-studio:contracts:v1:<name>`.

| Name | Model / mode | Use |
| --- | --- | --- |
| `render-job.create` | JobCreate / validation | POST `/projects/{project_id}/jobs` |
| `render-job.fixture-create` | FixtureJobCreate / validation | POST `/projects/{project_id}/fixture-jobs` |
| `render-job.response` | RenderJob / serialization | Create/list/detail/tick/cancel responses |
| `render-job.record` | RenderJobRecord / validation | All eight SQLite render_jobs fields |
| `render-job.saved-outcome` | SavedOutcome / serialization | Non-null GET `/jobs/{job_id}/result` response |
| `fake-provider.request` | FakeRequest / validation | Internal fixture provider input |
| `fake-provider.result` | FakeResult / serialization | Internal provider result and nested saved result |

Run `.venv/bin/python -m scripts.export_schemas`, or add `--check` for CI drift
verification. The registry contains 17 schemas. Existing provider/outcome models
remain in their original modules; these exports version their current shapes
without duplicating their validation logic. SavedOutcome includes nested $defs
for FakeResult, Artifact and StoredError. Provider request is not a public job
request. HTTP result can also be JSON null when no outcome is saved; the standalone
saved-outcome schema describes the non-null object only. Error HTTP envelopes and
binary artifacts continue to be documented by existing routes/OpenAPI.

## Record versus API

Every persisted key is required, including nullable keys. Record validation is
strict, frozen and rejects extras. It preserves raw text and arbitrary state
strings, and does not apply positive-ID or 0–100 progress constraints.

| Field | SQLite record | RenderJob response model |
| --- | --- | --- |
| `id` | Required integer primary key | Required integer |
| `project_id` | Required integer; no SQL foreign key | Required integer |
| `current_step` | Required nullable TEXT; SQL default NULL | Nullable string, model default `queued` |
| `current_shot` | Required nullable INTEGER; SQL default NULL | Nullable integer, model default null |
| `state` | Required nullable TEXT; SQL default `queued` | Non-null string, model default `running` |
| `progress` | Required nullable INTEGER; SQL default 0 | Non-null integer, model default 0 |
| `created_at` | Required raw TEXT; SQL default CURRENT_TIMESTAMP | Omitted |
| `updated_at` | Required raw TEXT; SQL default CURRENT_TIMESTAMP | Omitted |

API response models retain Pydantic's non-strict behavior and ignore extra input
columns. Defaults apply to omitted keys, not explicit NULL. All six response keys
are emitted by existing endpoints despite four having model defaults. FastAPI
omits null-default annotations from OpenAPI; standalone schemas retain them.
SQLite affinity can store values beyond this intended INTEGER/TEXT domain; the
record rejects such values rather than coercing or rewriting them.

**Known compatibility gaps, assigned to 1.17f:** SQL NULL `state` or `progress`
passes the record contract but makes list/detail API responses fail with HTTP 500.
Tests preserve and reproduce these failures without rewriting the rows. The
previously known Project NULL status issue also remains. Publishing these
baselines alone does not close the full Phase 1 gate.

## Request and execution behavior

Legacy JobCreate accepts optional nullable `current_step` (default `queued`) and
silently ignores unknown keys. It does not trim strings. The endpoint changes
null/empty step to `queued`, inserts state `running` and progress 5. These insert
values differ from both SQL and response-model defaults.

FixtureJobCreate requires an empty object and forbids extra fields. The dispatcher
validates the stored Project prompt via FakeRequest, creates queued fixture-owned
work and returns an initial job snapshot. Existing tests cover background progress,
cancellation and terminal state protection; response schemas alone are not a
state-machine specification. Detail/fixture routes require positive IDs; legacy
create/tick/cancel use their existing unrestricted integer path parameters.

## Existing result/provider mapping

`job_results` (migration 0002) stores schema_version=1, result_json or error
code/message, and created_at. `JobResultRepository` reads these into SavedOutcome:
exactly one result/error, valid error code and nonempty bounded message, matching
artifact field/kind, absolute paths and positive audio/video durations. These
cross-field and filesystem semantics are Python validators, not fully represented
by generated JSON Schema. They still apply after export.

FakeResult identifies provider `fake` version `1`, model `fixture-media` version
`1`, seed and image/audio/video artifacts. Artifact includes kind, path, SHA-256
and optional positive duration. FakeRequest validates prompt, seed and timeout;
it does not generate prompt-specific media. Existing result/provider tests cover
validation, storage round trips and failure handling.

`fixture_jobs` (migration 0003) stores only a job ownership marker and is separate
from the eight-field render_jobs record. Result and ownership table columns are
not injected into job responses. No migration or existing reader changes here.
Full pipeline versions, retries, costs, idempotency and crash recovery remain in
3.5/3.6, 4.3/4.4 and 9.3.

Evidence: [RenderJob checkpoint](../render-job-contract-checkpoint.md).
