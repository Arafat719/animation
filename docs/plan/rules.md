<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

## 1. Codex: read this first

Routine entry: read `AGENTS.md` and `docs/RESUME.md`, then only the current phase
excerpt under `docs/plan/`. This replaces the old full-plan startup reading below.
The master remains the requirements source; regenerate excerpts after edits.

You are building a real, modular AI animation system. Do not attempt to finish the entire product in one pass.

Follow these rules:

1. Read the current owner request and the progress/resume rules below before changing anything. Inspect the relevant existing code and evidence; do not repeat all machine discovery on every turn.
2. Implement one unfinished numbered **micro-step** at a time, in dependency order, within the owner's authorized scope. Skip completed work; historical step numbers are not a command to restart. A plan-only request authorizes documentation edits only. Never implement a whole phase in one turn.
3. At the end of every implementation phase, run its applicable tests and show the owner:
   - what was built;
   - which files changed;
   - test results;
   - current limitations;
   - the next phase.
4. Do not start the next phase until its prerequisites pass and the owner approves it. Existing authorization in the conversation counts; do not ask again for an already authorized action. A plan revision is not approval to implement the next feature. The owner-approved Phase 4 mock-only prerequisite exception below applies; existing Phase 4 implementation authorization remains valid.
5. Do not activate a paid GPU, create a billable cloud resource, or download a model larger than 2 GB without explicit approval.
6. Never commit API keys, cloud tokens, personal voice samples, reference images, model weights, generated media, or `.env` files.
7. Prefer replaceable provider interfaces. No UI or orchestration code may depend directly on one AI model or one cloud vendor.
8. Make the smallest working vertical slice first. Avoid premature scaling, payments, teams, subscriptions, and public deployment.
9. Preserve existing user files and changes. Do not delete or overwrite unrelated work.
10. If the repository does not exist, create it only after Phase 0 is approved.
11. Follow Section 6 together with the current status ledger. A step is not complete until its stated check passes; a phase additionally requires every applicable Section 7 task and acceptance gate. Passing a test suite alone does not complete missing features.
12. Never mix refactoring, dependency upgrades and a new feature in the same micro-step.

### বাধ্যতামূলক ভাষার নিয়ম

Codex must communicate with the owner in **বাংলা হরফে**, not Banglish.

- ব্যাখ্যা, progress update, প্রশ্ন, warning এবং phase report বাংলায় লিখতে হবে।
- শুধু source code, terminal command, file path, package/model name এবং আসল error message ইংরেজিতে থাকবে।
- কোনো technical English word প্রয়োজন হলে বাংলা বাক্যের মধ্যে ব্যবহার করা যাবে।
- উত্তর ছোট, পরিষ্কার এবং numbered হতে হবে।
- বড় log পুরোটা দেখাবে না; দরকারি error অংশ এবং তার বাংলা ব্যাখ্যা দেখাবে।
- মালিক ইংরেজি না চাইলে পুরো উত্তর ইংরেজিতে লেখা যাবে না।



### Micro-step শেষে Codex কীভাবে থামবে

প্রতিটি micro-step শেষে Codex শুধু এই পাঁচটি জিনিস বাংলায় বলবে:

1. কোন micro-step শেষ হয়েছে;
2. কী file বদলেছে;
3. কোন test চালিয়েছে এবং ফল কী;
4. কোনো limitation/error আছে কি না;
5. পরের micro-step ও তার authorization status; আগেই অনুমোদিত হলে আবার অনুমতি চাইবে না, শুধু plan review অনুমোদিত হলে implementation শুরু করবে না।

### Bug কমানোর বাধ্যতামূলক নিয়ম

1. Implementation step-এর আগে প্রাসঙ্গিক baseline যাচাই করবে; একই অপরিবর্তিত code-এর সাম্প্রতিক test evidence পুনর্ব্যবহার করা যায়। শুধু plan/docs edit-এ links, status, scope ও consistency যাচাই করবে; অপ্রয়োজনে app tests/install চালাবে না।
2. এক step-এ সর্বোচ্চ একটি নতুন feature বা একটি bug fix করবে।
3. কোনো error লুকাতে test skip, exception swallow, `any` বা hard-coded success ব্যবহার করবে না। ঘোষিত mock/fixture provider এই plan-এর বৈধ test ব্যবস্থা; তার ফলকে real AI output বলে দেখাবে না।
4. একটি fix ব্যর্থ হলে error আবার পড়বে এবং root cause evidence দেখবে। একই সমস্যায় দুইবার fix ব্যর্থ হলে অনুমানভিত্তিক edit বন্ধ করে কারণ যাচাই করবে; নতুন evidence থাকলে এগোবে। ব্যবহারকারীর তথ্য বা বাহ্যিক পরিবর্তন ছাড়া এগোনো অসম্ভব হলেই blocker জানাবে।
5. প্রয়োজন ছাড়া package update করবে না। Version pin/lock করবে এবং update করলে changelog/compatibility দেখবে।
6. real provider যোগ করার আগে তার mock contract test pass করাবে।
7. backend schema বদলালে migration এবং backward-read test যোগ করবে।
8. UI change-এর সঙ্গে অন্তত loading, empty, success এবং error state পরীক্ষা করবে।
9. cloud call retry করলে idempotency নিশ্চিত করবে, যাতে একই paid job দুইবার শুরু না হয়।
10. generated output পাওয়া মানেই success নয়; ffprobe/schema/checksum দিয়ে verify করবে।
11. refactor কেবল tests pass থাকা অবস্থায় আলাদা micro-step হিসেবে করবে।
12. user-এর unrelated code বা configuration স্পর্শ করবে না।
13. command চালানোর আগে current working directory নিশ্চিত করবে।
14. বড় install/download-এর আগে size, destination, free disk এবং source দেখিয়ে অনুমতি নেবে।
15. প্রতিটি passed micro-step-এর পরে ছোট recovery checkpoint রাখবে; existing dirty worktree থাকলে নিজে থেকে commit করবে না।

## 9. Testing requirements

Implementation phases must satisfy the relevant test layers, adding meaningful coverage for new behavior and using existing coverage where it already verifies the requirement. Read-only discovery and plan-only edits require evidence/document consistency checks, not new application tests. Minimum implementation test layers:

1. **Unit:** schemas, prompt construction, state transitions, duration math, cost calculation.
2. **API:** validation, project/job CRUD, cancellation, retries and artifact authorization.
3. **Provider contract:** the same test suite runs against mocks and real adapters.
4. **Media integration:** FFmpeg output exists, probes correctly and matches duration/FPS/audio expectations.
5. **Pipeline integration:** deliberate failures resume at the correct step.
6. **Human visual review:** character consistency, motion, lip-sync and anime quality.

No phase is complete merely because the server starts.

---

## 10. Security, privacy and safety

- Bind local services to `127.0.0.1` by default.
- Require authentication for every remote GPU endpoint.
- Use short-lived tokens where supported and redact them from logs.
- Validate filenames, MIME types, dimensions, duration and size of uploads.
- Prevent path traversal and command injection.
- Use subprocess argument arrays for FFmpeg and system tools.
- Keep voice cloning owner-only and consent-based.
- Do not support cloning public figures or a third party without verified authorization.
- Encrypt transport to the GPU worker.
- Add retention settings for uploaded references, custom voices and intermediates.
- Do not send source assets to any service other than the explicitly selected GPU host.

---

## 11. Cost-control rules

1. Develop UI, orchestration, media composition and tests with mocks locally.
2. Generate and approve still keyframes before video.
3. Begin at low resolution and 3 seconds per test.
4. Cache model weights on persistent storage only when storage cost is justified.
5. Cache successful outputs by input hash.
6. Set per-job retry and cost limits.
7. Shut down compute immediately after the queue is empty.
8. Display persistent-volume status even when compute is stopped.
9. Never run an always-on GPU for the private prototype.
10. Require owner approval before a benchmark expected to exceed the configured budget.

---

## 12. Explicitly out of scope for V1

Do not build these before the end-to-end private prototype works:

- training a foundation model from scratch;
- full 5–10 minute episodes;
- 3D animation;
- multiplayer/team collaboration;
- public signup/login system;
- subscription/payment gateway;
- mobile app;
- Kubernetes or multi-region infrastructure;
- model marketplace;
- real-time editing timeline comparable to professional NLE software;
- unlimited languages/styles;
- automatic publishing to social platforms.

---
