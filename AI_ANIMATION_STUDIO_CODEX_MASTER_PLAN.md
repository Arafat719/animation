# AI Animation Studio — Codex Master Build Plan V2.3 (Sample preview completed)

**Document type:** Implementation specification for Codex  
**Target:** Private V1, then public-ready architecture  
**Last updated:** 2026-09-10 (V2.3: step 1.13 completed; next step 1.14)  
**Owner:** Arafat Khan

---

## 1. Codex: read this first

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
4. Do not start the next phase until its prerequisites pass and the owner approves it. Existing authorization in the conversation counts; do not ask again for an already authorized action. A plan revision is not approval to implement the next feature.
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

### বর্তমান অবস্থান ও resume নিয়ম — ২০২৬-০৯-১০

- ২০২৬-০৯-০৯-এর পরিকল্পনা সংশোধন সম্পন্ন ছিল। মালিকের কাজ চালানোর নির্দেশ অনুযায়ী 1.12-এর পরে **1.13 — sample preview/download UI সম্পন্ন হয়েছে**; [checkpoint](docs/sample-preview-checkpoint.md)।
- Repository ও working web/API আগে থেকেই আছে। **`0.1` থেকে আবার শুরু করবে না।** Phase 0-এর পুরোনো discovery/installation নির্দেশ নতুন করে চালানোর আদেশ নয়।
- **বর্তমান phase: Phase 1 — PARTIAL।** 1.1–1.10-এর ভিত্তি এবং 1.11-এর পূর্ববর্তী regression check আছে; পরে settings, pages, fixture provider, runner, background dispatch ও web integration সম্পন্ন হয়েছে।
- সর্বশেষ বাস্তবায়ন: **sample preview/download UI**। সংরক্ষিত image/audio/video browser-এ দেখা, শোনা, download ও retry করা যায়। Sample media prompt-specific AI animation নয়; audio silent এবং বর্তমান video এক-frame-এর।
- সর্বশেষ frontend যাচাই: typecheck/build/lint ও পূর্ণ browser regression PASS; [sample preview checkpoint](docs/sample-preview-checkpoint.md)। সর্বশেষ backend যাচাই **২০৬ tests PASS**, যার ৩৪টি artifact API check; [1.12 checkpoint](docs/artifact-api-checkpoint.md)। 1.13-এ backend অপরিবর্তিত, Python suite পুনরায় চালানো হয়নি।
- **পরবর্তী implementation candidate: 1.14 — structured pipeline logging।** 1.12–1.13 আবার বানাবে না; বিদ্যমান dispatcher logging-এর প্রমাণ দেখে শুধু বাকি scope সম্পূর্ণ করবে।

প্রমাণ ও নির্দেশের ব্যবহার:

1. মালিকের সর্বশেষ নির্দেশ কাজের scope নির্ধারণ করে। বর্তমান source/tests বাস্তব implementation দেখায়; একটি পুরোনো checkpoint নতুন নির্দেশকে অতিক্রম করে না।
2. [বর্তমান কাজের ledger](docs/current-build-status.md) হবে সর্বশেষ completion/remaining-work তালিকা। এই master plan feature requirements, step IDs ও phase gates নির্ধারণ করে। একই পরিবর্তনে দুটিকে সামঞ্জস্যপূর্ণ রাখবে।
3. পুরোনো `*-checkpoint.md`, `phase-1-verification.md` এবং starter plan তাদের সময়ের evidence। সেগুলোর “next”, “missing” বা “wait for permission” বর্তমান কাজের queue নয়। Test ফলকে তার তারিখ ও যাচাইয়ের scope-সহ পড়বে।
4. Source, current ledger ও plan-এ অমিল পেলে আগে অমিলটি যাচাই করে status সংশোধন করবে; সুবিধামতো কোনো requirement বাদ দেবে না বা সব শুরু থেকে বানাবে না।
5. Hardware/model inventory-এর পুরোনো তথ্য নতুন করে verified বলে লিখবে না। Install/model/GPU কাজের আগে প্রয়োজনীয় পরিবর্তনশীল তথ্য তখন যাচাই করবে; অনুপস্থিত পুরোনো report পুরো Phase 0 পুনরারম্ভের কারণ নয়।

### নতুন session-এ প্রথম কাজ

> এই plan, `docs/current-build-status.md` এবং সর্বশেষ প্রাসঙ্গিক checkpoint পড়ো। মালিকের বর্তমান অনুরোধ অনুযায়ী কাজ করো। সম্পন্ন step পুনরায় implement করবে না। শুধু plan review চাইলে শুধু নথি ঠিক করো; implementation চালাতে বললে ledger-এর প্রথম অসম্পূর্ণ, অনুমোদিত step ও তার prerequisite থেকে চালিয়ে যাও। `0.1`-কে default starting point ধরবে না।

---

## 2. Fixed product decisions

These decisions are already made. Do not ask again unless a technical blocker forces a change.

| Decision | V1 choice |
|---|---|
| Product | Smart AI animation studio/agent |
| Main flow | One prompt to finished scene |
| Output | 30–60 second video |
| Visual style | 2D Japanese anime |
| Character input | Text description and/or reference image |
| Character reuse | Save a character and reuse the same identity |
| Voice | Built-in voices and consented custom voice sample |
| Runtime | Hybrid: local control app plus rented cloud GPU |
| Local hardware | Must work without a local discrete GPU |
| First interface | Web app |
| Later interface | Desktop app after the web pipeline is stable |
| First audience | Owner-only private prototype |
| Build method | Codex implements the project phase by phase |

### V1 definition of done

The owner can enter one prompt, optionally select a saved character and voice, click **Generate**, watch job progress, preview individual shots, regenerate a failed shot, and export one 30–60 second MP4 with anime visuals, dialogue audio, basic lip-sync, and subtitles.

V1 does **not** require perfect movie-level motion or identity in every frame. It must instead be reliable, inspectable, resumable, and improveable.

---

## 3. Reality and core strategy

A reliable 30–60 second scene should not be generated as one long clip. V1 must build it as a sequence of short shots.

```text
User prompt
  -> structured story plan
  -> character and style references
  -> 6–10 short shot plans
  -> keyframe for every shot
  -> 3–6 second image-to-video clips
  -> dialogue audio
  -> lip-sync where a speaking face is visible
  -> FFmpeg composition
  -> final MP4
```

This shot-based design makes failed parts regenerable and keeps cloud cost under control.

---

## 4. Technical architecture

### 4.1 Components

| Component | Responsibility | Default technology |
|---|---|---|
| Web client | Projects, character/voice selection, prompt, progress, previews | React + Vite + TypeScript |
| Local API/orchestrator | Validation, jobs, state machine, provider calls, media metadata | Python + FastAPI |
| Database | Private prototype metadata and job state | SQLite + SQLModel/Alembic |
| Job runner | Executes resumable pipeline steps | In-process worker first; Redis/Celery only later if required |
| GPU worker | Image, video, TTS and lip-sync inference | Python service and/or ComfyUI API workflows |
| GPU host | On-demand NVIDIA GPU | RunPod adapter first; vendor-neutral interface |
| Media engine | Probe, normalize, concatenate, mix audio, subtitles, export | FFmpeg/ffprobe |
| Storage | Inputs, intermediates, outputs, manifests | Local filesystem in V1; object storage adapter later |
| Desktop shell | Installable version after V1 stability | Tauri, reusing the web client |

### 4.2 Required boundaries

Create these interfaces before connecting real models:

```python
class PlannerProvider: ...
class ImageProvider: ...
class VideoProvider: ...
class TTSProvider: ...
class LipSyncProvider: ...
class GPUProvider: ...
class StorageProvider: ...
```

Every provider must expose:

- `health_check()`
- validated input/output schemas;
- timeout and cancellation support;
- normalized progress events;
- normalized error codes;
- mock implementation for tests;
- model name, version and seed in result metadata.

### 4.3 Suggested repository layout

```text
ai-animation-studio/
├── apps/
│   ├── web/                    # React/Vite/TypeScript
│   └── api/                    # FastAPI orchestrator
├── workers/
│   └── gpu-worker/             # Remote inference endpoints
├── animation_studio/
│   ├── domain/                 # schemas and state machine
│   ├── pipeline/               # step orchestration
│   ├── providers/              # mock/local/runpod/model adapters
│   ├── media/                  # FFmpeg wrapper
│   └── persistence/            # database and repositories
├── workflows/
│   └── comfyui/                # versioned API-format JSON workflows
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/
├── data/                       # gitignored runtime data
├── docs/
│   ├── architecture.md
│   ├── decisions/
│   ├── model-benchmarks.md
│   └── operations.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
└── README.md
```

Do not introduce a monorepo framework unless it solves a demonstrated problem.

---

## 5. Canonical data contracts

These are the full V1 target contracts, not a description of the current API. Define versioned Pydantic models and publish matching JSON Schema for the web client as each contract is introduced. The Phase 1 baseline and later feature-field obligations are explicitly separated in the [contract gap ledger](docs/current-build-status.md); a baseline schema does not mean the full V1 model is complete.

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

## 6. সহজ micro-step execution map

এই table feature dependency order এবং acceptance checks নির্ধারণ করে; এটি সব row অসম্পূর্ণ আছে এমন তালিকা নয়। বর্তমান status/evidence [ledger](docs/current-build-status.md)-এ আছে। সম্পন্ন row পুনরায় করবে না; আংশিক row-এর শুধু বাকি অংশ করবে। Section 7-এর requirement row-তে সংক্ষেপে না থাকলেও তা বাদ যায় না। প্রয়োজনে একটি ঘাটতিকে আলাদা suffix-সহ micro-step-এ ভাগ করবে, তার scope/check আগে লিখবে; পুরোনো ID বদলাবে না।

Phase 2-এর কিছু media helper আগে তৈরি হয়েছে। সেগুলো মুছে বা পুনরায় তৈরি করে order মেলাবে না; Phase 1 পূর্ণ gate না পেরোনো পর্যন্ত তাদের উপস্থিতিকে Phase 2 সম্পন্ন বা নতুন phase অনুমোদিত বলবে না।

### Phase 0 — প্রাথমিক discovery; বর্তমান resume point নয়

নিচের মূল discovery checklist ঐতিহাসিক reference হিসেবে রাখা হয়েছে। `0.1` ও code inspection আগে হয়েছে; 0.2–0.4-এর সম্পূর্ণ পুরোনো inventory report এই audit-এ পাওয়া যায়নি। তাই সব row-তে নতুন PASS বসানো হয়নি। প্রয়োজনভিত্তিক inventory refresh করা যাবে; বর্তমানে 0.1 থেকে ধারাবাহিক restart বা পুরোনো minimum-install proposal পুনরায় দেওয়া লাগবে না।

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 0.1 | বর্তমান folder এবং Git status দেখবে | কোন file আছে/নেই তার সংক্ষিপ্ত বাংলা তালিকা |
| 0.2 | OS, CPU, RAM ও GPU তথ্য দেখবে | exact detected specification report |
| 0.3 | free disk space ও বড় AI file খুঁজবে | model path, name ও size report; কোনো load নয় |
| 0.4 | Python, Node, npm, Git, FFmpeg ও Docker version দেখবে | installed/missing table |
| 0.5 | existing code/package manifest পড়বে | reusable এবং missing অংশ আলাদা list |
| 0.6 | Phase 1-এর minimum install proposal দেবে | কোনো install না করে মালিকের অনুমতি চাইবে |

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

**1.1–1.11-এর বর্তমান evidence:** [ledger](docs/current-build-status.md)। পরে করা typed settings, Workspace/Characters/Voices/Settings pages, fixture provider, result persistence/API, runner, background dispatch ও web integration সংশ্লিষ্ট 1.3/1.4/1.6/1.9/1.10 এবং Section 7-এর follow-up হিসেবে সম্পন্ন। আলাদা পুরোনো step ID বানিয়ে ইতিহাস বদলাবে না।

#### Phase 1-এর follow-up micro-steps — status ledger-এ, পুরোনো IDs অপরিবর্তিত

| Step | এক ধাপের কাজ | Pass check |
|---|---|---|
| 1.12 | Saved fixture result-এর image/audio/video job ID ও artifact kind দিয়ে serve/download করার local API | valid saved artifact পড়া যায়; unknown job/result/kind, missing file ও arbitrary path access স্পষ্টভাবে rejected; job/result অপরিবর্তিত; API tests pass |
| 1.13 | 1.12 ব্যবহার করে sample preview/download UI | image/audio/video preview ও download; refresh-এ পাওয়া যায়; loading/empty/error/retry ও missing-media browser checks pass; sample সীমা স্পষ্ট |
| 1.14 | বিদ্যমান dispatcher exception log থেকে pipeline-wide structured logging সম্পূর্ণ করবে | start/progress/finish/failure/cancel-এ job/project/shot/step context এবং sensitive-data redaction যাচাই |
| 1.15 | বর্তমান backend/frontend-এর formatter configuration ও check যোগ করবে | lint থেকে পৃথক formatter check চলে; unrelated mass reformat বা dependency upgrade নয় |
| 1.16 | এক-command local startup ও usage documentation যোগ করবে | fresh local invocation-এ API/web চালু, port conflict পরিষ্কার, stop করলে দুই process বন্ধ; real AI/GPU নয় |
| 1.17 | পূর্ণ Section 7 Phase 1 scope audit ও regression gate | required tasks, migration/schema scope, 1.12–1.16 ও applicable checks সব complete; unresolved requirement থাকলে PARTIAL, Phase 2 নয় |

**বর্তমান completion:** 1.12–1.13-এর checks PASS; [artifact API](docs/artifact-api-checkpoint.md) ও [preview UI](docs/sample-preview-checkpoint.md)। 1.14–1.17 অসম্পূর্ণ।

**1.17-এর schema সীমা:** initial পাঁচটি table ও migration আছে, কিন্তু Section 5-এর পূর্ণ canonical contracts নেই। Phase 1-এ বর্তমান persisted/API fields-এর versioned typed baseline, matching JSON Schema, এবং migration/backward-read guarantees যাচাই করতে হবে; শুধু table আছে বা পরে করব লেখা এই check পাস করায় না। baseline-এর অবশিষ্ট কাজ এক contract করে `1.17a`, `1.17b` ইত্যাদি sub-step-এ বন্ধ করে 1.17 rerun করবে। Strict StoryPlan এবং planning ShotPlan 3.1-এ; character/voice/provider-dependent fields তাদের feature phase-এ। [নির্দিষ্ট baseline ও পরবর্তী field mapping](docs/current-build-status.md) অনুসরণ করবে; এটি full V1 contract সম্পন্ন হওয়ার ঘোষণা নয়।

### Phase 2 — AI ছাড়া video জোড়া দেওয়া

বর্তমান scope: 2.1/2.3-এর helper ও tests আছে; 2.2 provenance এবং 2.4 normalization acceptance আংশিক; 2.5-এর সাধারণ concat/duration check আছে, path handling উন্নতি বাকি। 2.6–2.10 gate সম্পন্ন নয়। Phase 1-এর পর এগোনোর অনুমতি পেলে আগে এই gaps বন্ধ করবে, তারপর 2.6 onward। Background audio/fades ও insufficient-disk handling Section 7 অনুযায়ী যথাক্রমে 2.6/2.9-এর আলাদা sub-step-এ রাখবে; ছোট row দেখে সেগুলো বাদ দেবে না।

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 2.1 | FFmpeg/ffprobe wrapper ও version check বানাবে | unit test pass; shell string interpolation নেই |
| 2.2 | ছোট legal fixture image/audio/video যোগ করবে | fixture source documented এবং files probe হয় |
| 2.3 | একটি image থেকে test video বানাবে | playable MP4 output |
| 2.4 | দুইটি fixture clip একই format-এ normalize করবে | resolution/FPS/codec match |
| 2.5 | দুইটি clip concatenate করবে | duration expected value-এর ±0.5 second |
| 2.6 | একটি dialogue audio track mix করবে | sound plays এবং duration ঠিক থাকে |
| 2.7 | SRT subtitle তৈরি ও optional burn করবে | subtitle timing test pass |
| 2.8 | thumbnail ও `render_manifest.json` বানাবে | output দ্বিতীয়বার reproduce করা যায় |
| 2.9 | corrupt/missing input error handle করবে | crash নয়; পরিষ্কার বাংলা UI error |
| 2.10 | Phase 2 regression test চালাবে | Phase 1-এর test-ও pass থাকে |

### Phase 3 — prompt থেকে shot plan; mock আগে, অনুমোদিত real planner পরে

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 3.1 | StoryPlan ও ShotPlan schema বানাবে | valid fixture accepted, invalid fixture rejected |
| 3.2 | fixed mock planner বানাবে | same input gives same output |
| 3.3 | duration splitter বানাবে | 30–60 seconds becomes valid 3–6 second shots |
| 3.4 | character traits প্রতিটি relevant shot-এ inject করবে | schema snapshot test pass |
| 3.5 | pipeline state machine বানাবে | legal/illegal transition tests pass |
| 3.6 | একটি step ইচ্ছা করে fail করাবে | resume failed step থেকেই হয় |
| 3.7 | UI-তে shot list দেখাবে | order, duration, prompt দেখা যায় |
| 3.8 | mock plan edit/approve flow বানাবে | approval ছাড়া render শুরু হয় না |
| 3.9 | local open planner model-এর ছোট isolated test proposal দেবে | download/run করার আগে অনুমতি চাইবে |
| 3.10 | approved হলে real planner adapter যোগ করবে | strict JSON output test set pass |

### Phase 4 — cloud GPU connection, আগে mock পরে real

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

### Phase 5 — প্রথম real anime image, তারপর character consistency

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 5.1 | আগে উল্লেখ করা প্রায় 13 GB model এখনও পাওয়া গেলে তার exact path/size/identity/license/format verify করবে; না পেলে missing হিসেবে report করবে | উপস্থিতি অনুমান নয়; duplicate download নয়; findings documented |
| 5.2 | ImageProvider mock contract বানাবে | provider tests pass |
| 5.3 | ComfyUI API-format minimal image workflow বানাবে | workflow validates |
| 5.4 | একটি text prompt থেকে একটি low-cost anime image বানাবে | valid image; model/seed recorded |
| 5.5 | 1.12/1.13-এর artifact delivery/preview ব্যবস্থায় real image result যুক্ত করবে | refresh-এর পর real image artifact থাকে; fixture সীমা আরোপ করে real output ভুল দেখানো নয় |
| 5.6 | reference image upload validation যোগ করবে | wrong type/size rejected |
| 5.7 | description থেকে character profile বানাবে | traits database-এ save হয় |
| 5.8 | reference conditioning দিয়ে দ্বিতীয় pose বানাবে | একই character recognizably থাকে |
| 5.9 | five-pose character sheet বানাবে | hair/eyes/outfit checklist human review pass |
| 5.10 | approve/regenerate/edit prompt/lock seed controls বানাবে | approved keyframe immutable থাকে |
| 5.11 | পাঁচটি shot keyframe test করবে | video generation-এর আগে সব approved |

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

### Phase 7 — voice; built-in আগে, clone পরে

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 7.1 | TTSProvider mock contract বানাবে | provider tests pass |
| 7.2 | একটি built-in voice ও একটি supported language select/verify করবে | license/language documented |
| 7.3 | এক line dialogue generate করবে | clear audio and metadata |
| 7.4 | timing/duration record করবে | dialogue timeline-এ বসে |
| 7.5 | UI-তে built-in voice preview বানাবে | select and play works |
| 7.6 | custom sample upload validation ও consent checkbox বানাবে | consent ছাড়া save/use blocked |
| 7.7 | sample normalization ও private storage বানাবে | public URL দিয়ে access করা যায় না |
| 7.8 | একটি consented custom voice isolated test করবে | owner human-review result records |
| 7.9 | Delete Voice Data feature বানাবে | active copy deletion verified |
| 7.10 | multiple dialogue lines generate করবে | speaker/order/timing correct |

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

## 7. Detailed phase requirements

নিচের অংশ target requirements; কোনো “Create/Add/Implement” বাক্য নিজে থেকে বর্তমান কাজটি missing প্রমাণ করে না। বাস্তব status ledger-এ আছে। Phase 1-এর বর্তমান coverage সেখানে আলাদা দেওয়া হয়েছে। Canonical schema gap, planner repair/retry (Phase 3), pinned worker/capabilities/artifact authentication ও compute/storage lifecycle (Phase 4)-এর মতো detail Section 6-এ সংক্ষিপ্ত থাকলেও পূর্ণ gate-এ বাদ যাবে না।

## Phase 0 — Discovery and feasibility report

### Codex tasks

1. Locate existing animation folders, virtual environments, downloaded weights and code.
2. Record, without exposing secrets:
   - OS/version;
   - CPU and RAM;
   - disk size and free space;
   - GPU and VRAM, if any;
   - Python/Node/npm/Git/FFmpeg/Docker versions;
   - existing model names, exact paths and sizes;
   - existing package manifests and Git status.
3. If the previously reported approximately 13 GB model can still be located, identify its exact path, size, format and completeness. If absent or unverified, record that fact; do not assume it exists, load it or download a replacement as part of discovery.
4. Create a concise gap analysis and recommend only the prerequisites needed for Phase 1.
5. Estimate disk requirements separately for source code, model cache, intermediates and final media.

### Acceptance gate

- A report contains exact evidence, not guesses.
- No file or system change has occurred.
- The owner approves creating or modifying the project.

---

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

## Phase 2 — Deterministic media composer

### Codex tasks

1. Build a safe FFmpeg wrapper using argument arrays, never shell-concatenated user input.
2. Validate inputs with ffprobe.
3. Normalize test clips to the same resolution, FPS, codec and audio format.
4. Concatenate fixture clips, mix dialogue and background audio, add fades and burn optional subtitles.
5. Generate SRT subtitles from timed dialogue.
6. Create the render manifest and thumbnail.
7. Add failure messages for missing/corrupt media and insufficient disk.

### Acceptance gate

- Fixtures export a playable H.264/AAC MP4.
- Duration is within 0.5 seconds of the requested timeline.
- Audio remains synchronized.
- The exact export can be reproduced from its manifest.

---

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

## Phase 5 — Character creation and consistent keyframes

### Codex tasks

1. Implement `ImageProvider` and a ComfyUI-workflow adapter using API-format JSON.
2. Reuse a verified existing model if suitable; do not redownload duplicate weights.
3. Support:
   - text-only character creation;
   - reference-image-guided creation;
   - character sheet generation with front, three-quarter, side and expression views.
4. Store immutable visual traits and inject them into each shot.
5. Generate one approved keyframe per shot before any video generation.
6. Benchmark at least two consistency methods behind the provider boundary:
   - reference conditioning such as IP-Adapter/InstantID where compatible;
   - a modern image-edit/identity-preserving model such as Qwen-Image-Edit where hardware and license permit.
7. Do not train a LoRA in the first pass. Add LoRA training only if reference conditioning fails a documented consistency test.
8. Add manual **Approve**, **Regenerate**, **Edit Prompt** and **Lock Seed** controls.

### Acceptance gate

- One saved character appears recognizably consistent across at least five different shot keyframes.
- Hair, eye color, main outfit and accessories match the CharacterProfile.
- All keyframes preserve seeds and model metadata.
- No video GPU time is spent before keyframes are approved.

---

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

## Phase 7 — Built-in voice and consented voice cloning

### Codex tasks

1. Implement `TTSProvider` with separate built-in and custom voice adapters.
2. Require explicit consent confirmation before saving or using a custom voice sample.
3. Validate uploaded audio type, duration, sample rate and clipping; normalize a private working copy.
4. Start with one supported language and one built-in voice. Add languages only after a pronunciation test set passes.
5. Benchmark candidate TTS models for the required language. F5-TTS is a private-prototype candidate, not an approved dependency. Verify the exact selected code and weight licenses before use; do not assume a family-level license claim applies to every version or permits production use.
6. Generate dialogue per line with speaker, emotion hint, duration and timestamps.
7. Store private voice samples outside public/static directories and exclude them from logs and Git.
8. Provide **Delete Voice Data** and verify deletion from active local storage.

### Acceptance gate

- Built-in voice generates clear timed dialogue.
- A consented custom sample produces recognizably similar private-test speech.
- Unsupported language/model combinations fail clearly.
- Voice data is never publicly reachable.

---

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

## 8. Model policy

Models change quickly. Treat every model as a provider implementation, not the product architecture. The candidates, hardware estimates and technical links below were not revalidated in this documentation-only audit; verify exact official versions, licenses and hardware needs before selection or use.

### Initial candidates, not permanent commitments

| Need | Candidate | Use in plan |
|---|---|---|
| Visual workflow engine | ComfyUI | Versioned API-format workflows |
| Character reference | IP-Adapter / InstantID | First consistency benchmark where compatible |
| Character-aware image edit | Qwen-Image-Edit family | Second benchmark if VRAM/license allow |
| Image-to-video | Wan2.2 TI2V-5B | Initial 24 GB-class GPU candidate |
| Alternative video | LTX-Video/LTX-2 | Speed/quality benchmark candidate |
| Voice clone prototype | F5-TTS | Private test only until licensing is resolved |
| Lip-sync | MuseTalk | Anime benchmark required |
| Composition | FFmpeg | Required deterministic media layer |

Before installing or running a model, Codex must record the verified preflight information:

- official source and exact model/version;
- code license and weight license;
- commercial-use restriction;
- minimum/recommended VRAM;
- disk size and checksum;
- supported languages and resolutions;
- estimated benchmark GPU time and maximum permitted cost;
- known safety or quality limitations.

After an approved benchmark, record measured GPU time, actual cost and quality separately from estimates. A proposal cannot claim measurements from a test that has not run.

Never download an unverified executable, pickle, custom node, or model from an unknown source. Prefer safetensors and pinned official repositories.

---

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

## 13. Later roadmap

Only after V1 passes:

1. Character LoRA training and reusable style packs.
2. Better pose/control workflows and multi-character scenes.
3. Background, prop and location continuity.
4. Automatic sound effects and licensed music layer.
5. Manual timeline editor and shot transitions.
6. Bangla/English multilingual voice evaluation based on licensed models.
7. 9:16 social-video preset and 1080p upscale.
8. Public accounts, quotas, moderation, storage and billing.
9. Desktop offline mode after the owner obtains a suitable GPU.
10. Specialized fine-tuning from legally owned/authorized datasets.

---

## 14. Micro-step completion report template

Use this content after each implementation micro-step; at a phase boundary also report the full Section 7 gate. A plan-only edit reports document changes and consistency checks instead of claiming an implementation micro-step PASS:

```markdown
## Micro-step X.Y ফলাফল

অবস্থা: PASS / PARTIAL / BLOCKED

### যা করা হয়েছে
- ...

### যেসব file বদলেছে
- ...

### যাচাই
- Command: ...
- ফলাফল: ...

### সীমাবদ্ধতা বা blocker
- ...

### খরচ
- GPU সময়: ...
- আনুমানিক/প্রকৃত খরচ: ...

### পরের প্রস্তাবিত micro-step
- ...

অনুমোদনের অবস্থা: আগে থেকেই অনুমোদিত / পরের phase বা নির্দিষ্ট action-এর অনুমতি প্রয়োজন / বর্তমান অনুরোধ শুধু plan review।
নতুন অনুমতি প্রয়োজন হলেই তার নির্দিষ্ট কারণ জানাও; আগে পাওয়া অনুমতি আবার চেয়ো না।
```

---

## 15. Official technical references

- ComfyUI: https://github.com/comfy-org/comfyui
- ComfyUI API examples: https://docs.comfy.org/development/comfyui-server/api-examples
- ComfyUI API workflow format: https://docs.comfy.org/development/api-development/workflow-api-format
- Wan2.2: https://github.com/Wan-Video/Wan2.2
- LTX-Video: https://github.com/Lightricks/ltx-video
- IP-Adapter: https://github.com/tencent-ailab/IP-Adapter
- InstantID: https://github.com/instantX-research/InstantID
- Qwen-Image: https://github.com/QwenLM/Qwen-Image
- F5-TTS: https://github.com/SWivid/F5-TTS
- MuseTalk: https://github.com/TMElyralab/MuseTalk
- RunPod pricing: https://www.runpod.io/pricing

---

## 16. Immediate next action

**বর্তমান অবস্থান: 1.13 সম্পন্ন; পরবর্তী কাজ 1.14।** এই ফাইল পাওয়া মানেই কোনো step চালু করার অনুমতি নয়। মালিকের বর্তমান নির্দেশ, ledger ও প্রাসঙ্গিক evidence অনুযায়ী কাজ করবে; ২০২৬-০৯-০৯-এর plan-only scope আজকের নির্দেশকে অতিক্রম করে না।

পরে মালিক implementation চালাতে বললে ব্যবহারযোগ্য resume নির্দেশ:

> `AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md`, `docs/current-build-status.md` ও সর্বশেষ প্রাসঙ্গিক checkpoint পড়ে চলতি source-এর সঙ্গে মিলিয়ে নাও। সম্পন্ন কাজ আবার করবে না। বর্তমান planned candidate `1.14` — structured pipeline logging; ledger-এ এর পরের কোনো সম্পন্ন কাজ থাকলে সেটিও বাদ দিয়ে প্রথম অসম্পূর্ণ অনুমোদিত step বেছে নাও। একবারে একটি bounded step করো, তার checks ও সীমাবদ্ধতা বাংলায় জানাও। Phase 1 পূর্ণ হয়েছে ধরে Phase 2 বা real AI/GPU কাজ শুরু করবে না।
