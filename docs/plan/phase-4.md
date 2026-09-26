<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

### Phase 4 — cloud GPU connection, আগে mock পরে real

**Owner-approved phase-order revision (2026-09-25):** Phase 3 integrated offline
acceptance PASS হলে Phase 4-এর local/mock steps 4.1–4.6 এগোতে পারবে; real planner
3.10 এই সীমিত কাজের prerequisite নয়। Owner-এর আগের Phase 4 implementation
অনুমোদন বহাল; একবারে একটি অসম্পূর্ণ micro-step, শুরু 4.1। এটি শুধু prerequisite
শিথিল করছে, Phase 3 সম্পূর্ণ ঘোষণা বা তার real acceptance বাদ দিচ্ছে না।
Phase 3 real adapter, strict output test set, Bengali/duration/traits/repeatability,
provider lifecycle ও real-stage recovery evidence deferred এবং এখনও বাধ্যতামূলক।
4.7 শুধু cost/action proposal; 4.8–4.10 real execution এই exception-এর বাইরে,
প্রাসঙ্গিক prerequisites ও পৃথক paid-resource approval প্রয়োজন। Phase 4-এর পূর্ণ
acceptance এবং পরের phase-এর gates অপরিবর্তিত। নতুন model run/download অনুমোদিত নয়।

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 4.1 | generic GPUProvider interface বানাবে | mock contract tests pass |
| 4.2 | fake remote GPU HTTP server বানাবে | health, submit, status, cancel pass |
| 4.3 | timeout/retry/idempotency যোগ করবে | simulated network failure tests pass |
| 4.4 | budget config ও dry-run estimator যোগ করবে | over-budget job blocked হয় |
| 4.5 | secret loading ও log redaction যোগ করবে | token test logs-এ দেখা যায় না |
| 4.6 | RunPod adapter skeleton বানাবে | mock RunPod responses-এর test pass |
| 4.7 | real GPU launch-এর exact cost/action preview দেখাবে | paid action না করে অনুমতি চাইবে |
| 4.8 | approved হলে cheapest suitable GPU-তে health test করবে | authenticated health call pass |
| 4.9 | tiny inference smoke test করবে | output download হয়; GPU time recorded |
| 4.10 | compute stop ও storage status verify করবে | billable resource status বাংলায় report |

## Phase 4 — Cloud GPU worker and cost guardrails

### Codex tasks

1. Implement a generic `GPUProvider` and a RunPod implementation.
2. Build a version-pinned GPU worker image with `/health`, `/capabilities`, `/jobs`, `/jobs/{id}`, `/cancel` and protected artifact endpoints.
3. Use authenticated HTTPS or an SSH tunnel. Never expose an unauthenticated ComfyUI/API port publicly.
4. Add connection timeouts, idempotency keys, retries with backoff and cancellation.
5. Add a dry-run cost estimator and hard configurable limits:
   - maximum GPU hourly price;
   - maximum GPU minutes per job;
   - maximum attempts per shot;
   - maximum estimated cost per render.
6. Separate compute lifecycle from persistent storage lifecycle and display both states.
7. Write shutdown instructions and a visible warning that stopped compute may still leave billable storage.
8. Test with mock HTTP first. Ask the owner before creating the first paid instance.

### Acceptance gate

- All integration tests pass against a mock worker.
- Secrets are absent from Git history and logs.
- A real GPU health check and one tiny inference smoke test pass after approval.
- The instance can be stopped/deleted using documented steps.

---
