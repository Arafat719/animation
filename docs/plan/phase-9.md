<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

### Phase 9 — ছোট অংশ জোড়া দিয়ে final automatic pipeline

9.1-এর দুই-shot preview ও 9.4-এর 10–15 second scene হলো isolated smoke/integration-test scope। এগুলো production Project-এর V1 30–60 second duration contract শিথিল করে না; test-only pipeline input ব্যবহার করবে। 9.5 ও 9.8 final V1 duration যাচাই করবে।

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 9.1 | 2-shot pipeline connect করবে | prompt to combined preview pass |
| 9.2 | dialogue ও subtitle যোগ করবে | sync human review pass |
| 9.3 | failure/resume test করবে | completed shot reruns না |
| 9.4 | 10–15 second scene বানাবে | end-to-end manifest complete |
| 9.5 | 30-second scene বানাবে | budget limit এবং quality review pass |
| 9.6 | keyframe approval pause default রাখবে | approval ছাড়া costly video step blocked |
| 9.7 | assisted mode stable হলে full-auto toggle যোগ করবে | both modes tested |
| 9.8 | 60-second scene বানাবে | final MP4/SRT/thumbnail/manifest export |
| 9.9 | one-shot replace and recompose test করবে | অন্য shot regenerate হয় না |

## Phase 9 — End-to-end one-prompt pipeline

### Codex tasks

1. Connect planner, character, keyframe, video, TTS, lip-sync and composer steps.
2. Expose simple mode:
   - prompt;
   - optional saved character;
   - optional voice;
   - duration;
   - aspect ratio;
   - quality/cost preset.
3. Add a preflight screen showing shot count, estimated GPU time and maximum permitted cost.
4. Add progress by pipeline step and shot.
5. Pause for keyframe approval by default; allow full auto only after the assisted route is stable.
6. Allow retry, cancel and resume.
7. Export final MP4, SRT, thumbnail and render manifest.

### Acceptance gate

- One prompt produces a complete 30–60 second anime scene.
- Restarting the local API during a job does not lose completed-step state.
- One shot can be replaced and the final video recomposed without regenerating other shots.
- The actual GPU time and cost estimate are visible.

---
