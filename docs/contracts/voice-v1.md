# Voice metadata baseline v1

`animation_studio/domain/v1/voice.py` owns the existing API models `VoiceCreate`
and `Voice`, plus the complete strict, frozen `VoiceRecord`. Versioning is in
module paths and schema IDs; there is no new payload field or API route.

| Shape | Published URL | Generation mode |
| --- | --- | --- |
| POST `/voices` | `/schemas/v1/voice.create.schema.json` | validation |
| POST/list response | `/schemas/v1/voice.response.schema.json` | serialization |
| SQLite record | `/schemas/v1/voice.record.schema.json` | validation |

Exports use Draft 2020-12 and IDs `urn:animation-studio:contracts:v1:voice.<shape>`.
Run `.venv/bin/python -m scripts.export_schemas` to regenerate; add `--check`
for the existing CI drift gate. Nine schemas now cover Project, Character and
Voice. Vite publishes them as static metadata and copies them into builds.

## Field mapping and defaults

| Field | Persisted record / response | Create request |
| --- | --- | --- |
| `id` | Required integer; SQLite normally generates it | Forbidden |
| `name` | Required text, no trimming or length restrictions | Required; trim then validate 1–120 characters |
| `voice_type` | Required text; no SQL default or enum | Forbidden; endpoint inserts `built_in` |
| `language` | Required nullable text key; SQL default NULL | Optional nullable string, default null, trimmed, max 80 |
| `style` | Required nullable text key; SQL default NULL | Optional nullable string, default null, trimmed, max 400 |
| `created_at` | Required raw text; SQL default CURRENT_TIMESTAMP | Forbidden |

The endpoint stores blank language/style as NULL. Schemas cannot express this
endpoint normalization or Pydantic's pre-validation whitespace stripping. API
create retains its existing non-strict configuration and forbids unknown fields.
FastAPI omits null-default annotations in OpenAPI; the standalone create schema
retains them. The full existing OpenAPI remains unchanged.

The V1 target's `type` field is **not** an alias for current `voice_type`.
Stored custom, unknown, empty and padded type strings remain readable without
reinterpretation. Names need not be unique. All six record fields are required,
including nullable keys; records reject coercion and extras. SQLite can admit
values outside this intended text domain (such as BLOBs); this contract does not
add runtime validation or rewrite such rows. Response fields match the record,
with the API's existing non-strict model behavior.

No audio, consent, provider, synthesis or cloning capability is introduced.
Those fields belong to steps 7.1/7.6/7.7/7.10 before their features ship.
No migration is needed. Independent legacy and actual 0001/0002/0003 databases
are upgraded twice and reopened through the API, preserving every field exactly.
Checks include defaults, duplicates, over-create-limit and unusual text values.

Evidence: [Voice checkpoint](../voice-contract-checkpoint.md).
