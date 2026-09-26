<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

### Phase 8 — lip-sync; anime test ব্যর্থ হলে safe fallback

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 8.1 | LipSyncProvider mock contract বানাবে | provider tests pass |
| 8.2 | একটি close-up anime clip ও voice দিয়ে isolated MuseTalk test করবে | original preserved; result reviewable |
| 8.3 | face/landmark failure detect করবে | failure becomes status, not crash |
| 8.4 | আরও দুইটি close-up test করবে | 3-result human review table |
| 8.5 | quality fail করলে audio-driven/viseme fallback prototype করবে | fallback result compared openly |
| 8.6 | speaking-face detection rule যোগ করবে | non-speaking shot bypass হয় |
| 8.7 | UI-তে use/skip/regenerate lip-sync controls বানাবে | selected derived clip saved |

## Phase 8 — Anime lip-sync

### Codex tasks

1. Implement `LipSyncProvider` separately from video generation.
2. Benchmark MuseTalk on close-up anime faces; do not assume a model designed for human faces works well on anime.
3. If quality fails, test an audio-driven video model or a 2D mouth/viseme fallback rather than hiding the failure.
4. Apply lip-sync only to shots with visible speaking faces.
5. Preserve the original clip and save lip-sync as a derived artifact.
6. Add face/landmark failure detection and a **Skip Lip-sync** option.

### Acceptance gate

- At least three close-up anime dialogue clips pass human visual review.
- Non-speaking and off-camera dialogue shots bypass lip-sync.
- Failure does not destroy the original generated clip.

---
