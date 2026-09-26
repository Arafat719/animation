<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

### Phase 10 — stability আগে, desktop পরে

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 10.1 | five-project regression pack বানাবে | repeatable test instructions |
| 10.2 | disk cleanup preview বানাবে | confirmation ছাড়া source/final delete নয় |
| 10.3 | dependency locks ও migration tests final করবে | clean setup test pass |
| 10.4 | cold start/time/failure/cost report বানাবে | measurements documented |
| 10.5 | web version stable ঘোষণা করার gate চালাবে | all required checks pass |
| 10.6 | Tauri desktop shell skeleton বানাবে | existing web UI loads |
| 10.7 | desktop-to-local-API connection বানাবে | health/project flow pass |
| 10.8 | desktop package privacy scan করবে | secret/private asset absent |
| 10.9 | browser এবং desktop output compare করবে | equivalent manifest/output structure |

## Phase 10 — Quality, reliability and desktop packaging

### Codex tasks

1. Build a fixed regression pack of prompts, characters, voices and expected structural results.
2. Add disk cleanup rules that never delete final exports or source inputs without confirmation.
3. Add checksums, provider version checks and migration tests.
4. Measure cold start, per-shot time, failure rate and cost.
5. Package the stable web UI/API with Tauri only after the browser version passes regression tests.
6. Desktop app must still use the same provider contracts and may connect to the rented GPU worker.

### Acceptance gate

- Five end-to-end test projects complete or fail with actionable errors.
- No secret or private voice/reference asset appears in the packaged app.
- Desktop and browser builds create equivalent project manifests.

---
