<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

### Phase 1 — AI ছাড়া ছোট working app

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 1.1 | approved project root, `.gitignore` ও minimal folders তৈরি করবে | existing user file অপরিবর্তিত; Git diff পরিষ্কারভাবে দেখানো |
| 1.2 | Python virtual environment ও minimal pinned backend dependencies বসাবে | clean environment-এ import test pass |
| 1.3 | শুধু FastAPI `/health` endpoint বানাবে | automated test returns HTTP 200 |
| 1.4 | React + Vite + TypeScript minimal app বানাবে | browser-এ static home page দেখা যায় |
| 1.5 | web app থেকে `/health` call করবে | UI-তে API connected status দেখা যায় |
| 1.6 | SQLite connection ও প্রথম migration বানাবে | empty database create এবং migration test pass |
| 1.7 | Project create/list/get API বানাবে | API tests pass; invalid input returns 4xx |
| 1.8 | New Project form বানাবে | form থেকে project save ও reload হয় |
| 1.9 | fake job এবং fixed progress বানাবে | refresh-এর পরও progress থাকে |
| 1.10 | fake job cancel button বানাবে | cancelled job আর এগোয় না |
| 1.11 | বাস্তবায়িত Phase 1 slice-এর regression check চালাবে; পূর্ববর্তী PASS সংরক্ষিত | backend/frontend/API checks pass; এটি পূর্ণ Phase 1 completion নয়, পূর্ণ gate এখন 1.17 |

**1.1–1.11-এর বর্তমান evidence:** [ledger](../../docs/current-build-status.md)। পরে করা typed settings, Workspace/Characters/Voices/Settings pages, fixture provider, result persistence/API, runner, background dispatch ও web integration সংশ্লিষ্ট 1.3/1.4/1.6/1.9/1.10 এবং Section 7-এর follow-up হিসেবে সম্পন্ন। আলাদা পুরোনো step ID বানিয়ে ইতিহাস বদলাবে না।

#### Phase 1-এর follow-up micro-steps — status ledger-এ, পুরোনো IDs অপরিবর্তিত

| Step | এক ধাপের কাজ | Pass check |
|---|---|---|
| 1.12 | Saved fixture result-এর image/audio/video job ID ও artifact kind দিয়ে serve/download করার local API | valid saved artifact পড়া যায়; unknown job/result/kind, missing file ও arbitrary path access স্পষ্টভাবে rejected; job/result অপরিবর্তিত; API tests pass |
| 1.13 | 1.12 ব্যবহার করে sample preview/download UI | image/audio/video preview ও download; refresh-এ পাওয়া যায়; loading/empty/error/retry ও missing-media browser checks pass; sample সীমা স্পষ্ট |
| 1.14 | বিদ্যমান dispatcher exception log থেকে pipeline-wide structured logging সম্পূর্ণ করবে | start/progress/finish/failure/cancel-এ job/project/shot/step context এবং sensitive-data redaction যাচাই |
| 1.15 | বর্তমান backend/frontend-এর formatter configuration ও check যোগ করবে | lint থেকে পৃথক formatter check চলে; unrelated mass reformat বা dependency upgrade নয় |
| 1.16 | এক-command local startup ও usage documentation যোগ করবে | fresh local invocation-এ API/web চালু, port conflict পরিষ্কার, stop করলে দুই process বন্ধ; real AI/GPU নয় |
| 1.17 | পূর্ণ Section 7 Phase 1 scope audit ও regression gate | required tasks, migration/schema scope, 1.12–1.16 ও applicable checks সব complete; unresolved requirement থাকলে PARTIAL, Phase 2 নয় |

**বর্তমান completion:** 1.12–1.16-এর checks PASS; [artifact API](../../docs/artifact-api-checkpoint.md), [preview UI](../../docs/sample-preview-checkpoint.md) ও [logging](../../docs/pipeline-logging-checkpoint.md), [formatter](../../docs/formatting-checkpoint.md) ও [startup](../../docs/startup-checkpoint.md)। Formatter-এর strict legacy-debt check এখনও exit 1। 1.17a Project ও 1.17b Character baseline সম্পন্ন; [Project](../../docs/project-contract-checkpoint.md), [Character](../../docs/character-contract-checkpoint.md)। অন্য baseline/compatibility gaps-ও সমাধান হয়েছে; [পূর্ণ 1.17 local gate PASS](../../docs/phase-1-final-gate-2026-09-15.md)।

**1.17-এর schema সীমা:** initial পাঁচটি table ও migration আছে, কিন্তু Section 5-এর পূর্ণ canonical contracts নেই। Phase 1-এ বর্তমান persisted/API fields-এর versioned typed baseline, matching JSON Schema, এবং migration/backward-read guarantees যাচাই করতে হবে; শুধু table আছে বা পরে করব লেখা এই check পাস করায় না। baseline-এর অবশিষ্ট কাজ এক contract করে `1.17a`, `1.17b` ইত্যাদি sub-step-এ বন্ধ করে 1.17 rerun করবে। Strict StoryPlan এবং planning ShotPlan 3.1-এ; character/voice/provider-dependent fields তাদের feature phase-এ। [নির্দিষ্ট baseline ও পরবর্তী field mapping](../../docs/current-build-status.md) অনুসরণ করবে; এটি full V1 contract সম্পন্ন হওয়ার ঘোষণা নয়।

## Phase 1 — Local skeleton with fake generation

### Codex tasks

1. Create the repository structure and baseline documentation.
2. Create FastAPI health endpoint and typed settings loaded from environment variables.
3. Add SQLite migrations for Project, CharacterProfile, VoiceProfile, ShotPlan and RenderJob.
4. Add the React pages:
   - Projects;
   - New Project;
   - Project Workspace;
   - Characters;
   - Voices;
   - Settings.
5. Implement a fake provider that returns fixture images, silent audio and sample clips after predictable delays.
6. Implement job progress with polling first. Do not add WebSockets until polling works.
7. Add structured logging with `job_id`, `project_id`, `shot_id` and `step`.
8. Add unit tests, API tests, formatters and one-command local startup.

### Acceptance gate

- A prompt creates a fake job.
- The UI shows progress and survives a browser refresh.
- Restarting the API preserves projects/jobs.
- Cancellation works.
- Automated tests pass.
- No real AI model or paid GPU is used.

---
