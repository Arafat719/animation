<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

### Phase 6 — একবারে একটি ছোট video clip

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 6.1 | VideoProvider mock contract বানাবে | provider tests pass |
| 6.2 | selected model-এর license/VRAM/disk verify করবে | benchmark plan ও maximum cost shown |
| 6.3 | একটি approved keyframe থেকে 3-second low-resolution clip বানাবে | playable clip; actual GPU time saved |
| 6.4 | invalid/black/corrupt output checks যোগ করবে | bad fixture correctly rejected |
| 6.5 | একই keyframe-এ motion prompt variation test করবে | best setting documented |
| 6.6 | UI-তে clip approve/regenerate controls বানাবে | অন্য shot untouched থাকে |
| 6.7 | দ্বিতীয় ও তৃতীয় clip বানাবে | তিনটি independent output pass |
| 6.8 | 3–6 second duration support করবে | ffprobe duration test pass |
| 6.9 | three clips composer-এ জোড়া দেবে | playable combined preview |

## Phase 6 — Short anime shot generation

### Codex tasks

1. Implement `VideoProvider` using image-to-video first, not pure text-to-video.
2. Use approved keyframes plus explicit motion prompts.
3. Start at 480p or the model's economical preview setting; add 720p final mode later.
4. Use a pinned, benchmarked model. First candidate: Wan2.2 TI2V-5B on a 24 GB class GPU. Keep LTX-Video/LTX-2 as a replaceable benchmark candidate.
5. Limit first tests to 3 seconds, one shot, low resolution.
6. Record generation time, GPU type, VRAM, settings, output quality and cost in `docs/model-benchmarks.md`.
7. Add per-shot regenerate and motion-strength controls.
8. Detect obvious invalid output: zero frames, wrong duration, corrupt video, black frames and missing file.

### Acceptance gate

- Three approved keyframes each produce a playable 3–6 second clip.
- Character identity does not change beyond the agreed V1 tolerance.
- Each result is traceable to its keyframe, prompt, seed and model version.
- One failed clip can be regenerated without rerendering the others.

---
