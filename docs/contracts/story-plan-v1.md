# StoryPlan / planning ShotPlan v1

Step 3.1 defines planning contracts in
`animation_studio/domain/v1/story_plan.py`. These are separate from the persisted
`ShotRecord`: no database migration, planner, API or render integration is added.

Published validation schemas are `/schemas/v1/story-plan.schema.json` and
`/schemas/v1/shot-plan.schema.json`; regenerate with
`.venv/bin/python -m scripts.export_schemas`.

The story contains a version, logline, setting, mood, visual style, cast and
6–10 ordered shots totaling 30–60 seconds. Each shot lasts 3–6 seconds and
contains camera, background, action, lighting, visible cast, dialogue, prompts
and a seed. Reference inputs and media paths are opaque strings, not checked
files. Status defaults to pending, attempts to zero, and error to null; state
transitions and persistence belong to later steps.

Unknown fields, blank required text, numeric strings, nonfinite durations and
boolean integer values are rejected. Version must be the integer 1. Cast and
shot IDs must be unique, order must be contiguous and one-based, and visible
characters and dialogue speakers must belong to the cast. Offscreen speakers
are allowed. Estimated duration must match the shot sum within 1 microsecond.

JSON Schema exposes structural constraints; cross-field totals, uniqueness by
ID, references, whitespace normalization and ordering require Pydantic
validation. Consumers must validate with StoryPlan before accepting a plan.

Verification on 2026-09-19 covers valid round trips, 30/60-second boundaries,
invalid plans, strict version types and published-schema equality. The existing
implementation was retained and its Literal version coercion was corrected.
Real planning, duration splitting, edit/approval and rendering remain future work.
