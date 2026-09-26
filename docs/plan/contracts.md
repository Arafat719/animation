<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

## 5. Canonical data contracts

These are the full V1 target contracts, not a description of the current API. Define versioned Pydantic models and publish matching JSON Schema for the web client as each contract is introduced. The Phase 1 baseline and later feature-field obligations are explicitly separated in the [contract gap ledger](../../docs/current-build-status.md); a baseline schema does not mean the full V1 model is complete.

### Project

- `id`, `title`, `created_at`, `updated_at`
- `master_prompt`
- `target_duration_seconds` (30–60)
- `aspect_ratio` (`16:9`, later `9:16`)
- `fps` (24 default)
- `language`
- `style_preset_id`
- `character_ids[]`, `voice_ids[]`
- `status`

### CharacterProfile

- `id`, `name`, `description`
- `reference_image_paths[]`
- `character_sheet_path`
- immutable visual traits: face, hair, eyes, outfit, colors, accessories
- `negative_traits[]`
- model-specific adapter metadata
- consent/provenance metadata for uploaded references

### VoiceProfile

- `id`, `name`, `type` (`built_in` or `custom`)
- `language`, `style`, `reference_audio_path`
- `consent_confirmed_at`
- model/provider metadata

### StoryPlan

- logline, setting, mood, visual style
- characters and dialogue
- ordered `ShotPlan[]`
- estimated total duration

### ShotPlan

- `id`, order, duration (3–6 seconds)
- camera framing and movement
- background/action/lighting
- visible characters
- dialogue and speaker
- image prompt, negative prompt, motion prompt
- seed and reference inputs
- keyframe, raw clip, lip-synced clip paths
- status, attempts and error

### RenderJob

- `id`, `project_id`, `pipeline_version`
- current step and shot
- state: `queued/running/waiting_for_gpu/failed/cancelled/completed`
- progress 0–100
- cost estimate and measured GPU seconds
- timestamps, retry count, structured error

Store a `render_manifest.json` beside every final export. It must contain all prompts, seeds, provider/model versions, source asset hashes, shot order and FFmpeg command metadata so a render can be reproduced.

---
