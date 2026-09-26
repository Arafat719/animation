<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

### Phase 3 — prompt থেকে shot plan; mock আগে, অনুমোদিত real planner পরে

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 3.1 | সম্পন্ন: strict StoryPlan ও ShotPlan schemas | valid/invalid fixtures PASS; [contract](../../docs/contracts/story-plan-v1.md) |
| 3.2 | সম্পন্ন: fixed mock planner ও PlannerProvider | deterministic valid output PASS; [checkpoint](../../docs/mock-planner-checkpoint.md) |
| 3.3 | সম্পন্ন: duration splitter ও mock integration | 30–60s → valid 3–6s shots PASS; [checkpoint](../../docs/duration-splitter-checkpoint.md) |
| 3.4 | character traits প্রতিটি relevant shot-এ inject করবে | schema snapshot test pass |
| 3.5 | pipeline state machine বানাবে | legal/illegal transition tests pass |
| 3.6 | একটি step ইচ্ছা করে fail করাবে | resume failed step থেকেই হয় |
| 3.7 | UI-তে shot list দেখাবে | order, duration, prompt দেখা যায় |
| 3.8 | mock plan edit/approve flow বানাবে | approval ছাড়া render শুরু হয় না |
| 3.9 | local open planner model-এর ছোট isolated test proposal দেবে | download/run করার আগে অনুমতি চাইবে |
| 3.10 | approved হলে real planner adapter যোগ করবে | strict JSON output test set pass |

## Phase 3 — Prompt planner and shot state machine

### Codex tasks

1. Implement `PlannerProvider` with a deterministic mock.
2. Define a strict structured-output schema for StoryPlan.
3. Convert a user prompt into 6–10 shots of 3–6 seconds whose total is 30–60 seconds.
4. Include character traits in every relevant shot prompt.
5. Add prompt validation, repair and a maximum retry count.
6. Implement the resumable pipeline state machine. A failed shot must not invalidate completed shots.
7. Add a local open-model planner adapter only after the mock path passes. Keep the planner replaceable; it may run with `llama.cpp`/Ollama locally or on the GPU worker.

### Acceptance gate

- The same mock input produces the same valid StoryPlan.
- Invalid planner output is rejected or repaired.
- Total shot time stays within target duration.
- A deliberately failed shot resumes from the failed step.

---
