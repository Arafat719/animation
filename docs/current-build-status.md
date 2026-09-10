# বর্তমান কাজ ও বাকি ধাপ

তারিখ: ২০২৬-০৯-১০। এটি source, tests ও dated checkpoint মিলিয়ে করা বর্তমান
planning ledger। [Master plan](../AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md)
requirements ও step IDs নির্ধারণ করে; এই নথি status/evidence ও resume queue রাখে।
পুরোনো checkpoint-এর “next/missing” তার সময়ের কথা, বর্তমান queue নয়।

২০২৬-০৯-০৯-এর plan সংশোধন সম্পন্ন ছিল। মালিকের কাজ চালানোর নির্দেশ অনুযায়ী
1.12-এর পরে **1.13 — sample preview/download UI সম্পন্ন হয়েছে।** পরবর্তী
অসম্পূর্ণ কাজ **1.14 — structured pipeline logging**। `0.1` থেকে restart নয়।
পুরো V1 এবং বিস্তারিত Phase 1 এখনো অসম্পূর্ণ।

## যাচাইয়ের সীমা

- সর্বশেষ backend checkpoint: [artifact API](artifact-api-checkpoint.md),
  ২০২৬-০৯-১০; **২০৬ backend tests পাস**, যার ৩৪টি নতুন artifact API check।
  দুটি বিদ্যমান dependency deprecation warning আছে।
- সর্বশেষ implementation ও frontend typecheck/build/lint/browser regression:
  [sample preview/download](sample-preview-checkpoint.md), ২০২৬-০৯-১০—PASS।
  Real media decoding/playback, তিন download-এর byte comparison, missing/decode
  error/retry, refresh/restart, cleanup ও mobile layout যাচাই হয়েছে। Backend
  code অপরিবর্তিত; 1.13-এ Python suite পুনরায় চালানো হয়নি।
- Browser test-এ real local API/disposable SQLite এবং controlled HTTP failures
  ব্যবহৃত হয়েছে। Browser cancellation scenarios manual legacy jobs ব্যবহার করে;
  queued/running fixture cancellation-এর আলাদা Python coverage আছে।
- Browser request forwarding production CORS যাচাই করে না। Python 3.11,
  remote CI ও বর্তমান hardware/model inventory নতুন করে যাচাই করা হয়নি।
- কোনো ব্যবহারকারীর runtime database এই কাজে খোলা বা migrate করা হয়নি।
  সর্বশেষ migration file `0003_fixture_jobs`; কোন runtime DB ইতিমধ্যে এতে
  upgrade হয়েছে তা এই নথি দাবি করে না।

## Phase 0 ও মূল Phase 1 micro-step অবস্থান

“সম্পন্ন” মানে ওই সীমিত কাজের source ও নথিভুক্ত check আছে; পুরো phase বা ভবিষ্যৎ
canonical contract সম্পূর্ণ বোঝায় না। “আংশিক” মানে implementation/check-এর কিছু
অংশ বাকি। “ঐতিহাসিক” পুরোনো evidence; নতুন verification নয়।

| Step | বর্তমান অবস্থা | প্রমাণ / সীমা |
| --- | --- | --- |
| 0.1 | সম্পন্ন; restart নয় | মালিকের নিশ্চিতকরণ ও বর্তমান repo/Git inspection; dirty worktree-কে clean বলা হয়নি |
| 0.2–0.4 | ঐতিহাসিক discovery; পূর্ণ পুরোনো inventory report পাওয়া যায়নি | প্রয়োজন হলে নির্দিষ্ট hardware/version/disk/model তথ্য যাচাই করবে; সব row নতুন PASS নয়, পুরো Phase 0 আবার নয় |
| 0.5 | বর্তমান code/package audit করা হয়েছে | `apps`, `animation_studio`, manifests ও tests পড়া হয়েছে; reusable ও missing অংশ নিচে |
| 0.6 | প্রাথমিক minimum-install proposal অতিক্রান্ত | environment/dependencies আগেই আছে; নতুন install দরকার হলে তখন bounded proposal, পুরোনো proposal পুনরাবৃত্তি নয় |
| 1.1 | skeleton আছে; পুনরায় তৈরি নয় | [পূর্ববর্তী audit](phase-1-verification.md), `.gitignore`, `apps`, `animation_studio`; original clean diff-এর নতুন দাবি নয় |
| 1.2 | নথিভুক্ত সম্পন্ন: Python 3.12 setup | [dependency checkpoint](dependency-checkpoint.md): isolated install/import/pip check; Python 3.11/remote CI ফল দাবি নয় |
| 1.3 | সম্পন্ন; typed DB settings-ও যোগ হয়েছে | `apps/api/main.py`, `animation_studio/settings.py`, [settings checkpoint](settings-checkpoint.md) |
| 1.4 | সম্পন্ন; অতিরিক্ত pages-ও আছে | [TypeScript checkpoint](typescript-checkpoint.md), [workspace](workspace-checkpoint.md), [Characters](characters-checkpoint.md), [Voices](voices-checkpoint.md), [Settings](settings-page-checkpoint.md) |
| 1.5 | সম্পন্ন | `App.tsx` health call, [নথিভুক্ত connected-state checks](web-fixture-checkpoint.md) |
| 1.6 | initial migration সম্পন্ন; পূর্ণ domain contracts আংশিক | [migrations](migrations.md), `tests/test_db.py`; initial পাঁচটি table ছাড়াও `0002_job_results`, `0003_fixture_jobs` আছে |
| 1.7–1.8 | সীমিত Project API/form সম্পন্ন | `apps/api/main.py`, `tests/test_projects_api.py`, `App.tsx`, browser script; V1-এর সব Project fields/constraints নয় |
| 1.9–1.10 | সম্পন্ন; demo থেকে background sample flow-তে উন্নীত | [web integration](web-fixture-checkpoint.md), [dispatch](fixture-dispatch-checkpoint.md); polling read-only, queued/running cancel আছে |
| 1.11 | ঐতিহাসিক slice test gate PASS | [স্পষ্ট PASS/PARTIAL report](phase-1-verification.md); এটি পূর্ণ Phase 1 completion ছিল না। নতুন পূর্ণ gate 1.17 |
| 1.12 | সম্পন্ন | [artifact API checkpoint](artifact-api-checkpoint.md); job/kind দিয়ে verified sample serve/download, missing/invalid/path/read-only checks PASS |
| 1.13 | সম্পন্ন | [sample preview checkpoint](sample-preview-checkpoint.md); image/audio/video preview/download, loading/error/retry, refresh ও browser checks PASS |

## Phase 1-এর বিস্তারিত coverage

| অংশ | সম্পন্ন অংশ | এখনও বাকি / সীমা |
| --- | --- | --- |
| Web/API | Health, projects, New Project, Workspace, Characters, Voices, Settings | Workspace read-only; character/voice metadata project-এ assigned নয়; Settings শুধু DB path দেখায় |
| Database/contracts | SQLite/Alembic, পাঁচ initial table, result ও fixture ownership migration, typed API/settings | Section 5 canonical models/fields/versioned schemas পুরো নেই; নিচের schema ledger অনুসরণ করতে হবে |
| Fixture provider | image, silent audio, video; validated contracts, metadata/hash, timeout/cancel | fixed shared fixtures; prompt/seed/target duration দিয়ে নতুন media তৈরি হয় না |
| Runner/storage | transactional claim, progress, result/error persistence, terminal state protection | crash/storage-error-এর পর automatic recovery/resume নেই |
| Background API | queued creation, bounded worker, cancellation Event, graceful shutdown | এক API process; durable submission idempotency নেই; abrupt restart automatic re-dispatch নয় |
| Web jobs/results | Generate sample, read-only polling, result/error display, refresh/restart persistence; artifact API ও browser preview/download/retry | fixed default fixture paths; silent audio ও এক-frame sample video; real prompt-specific animation নয় |
| Logging | dispatch storage/state exception-এ job/project/shot/step context আছে | pipeline-wide structured events/configuration/checks আংশিক |
| Tooling | tests, strict TypeScript, build, Oxlint, browser regression helper | formatter ও এক-command startup নেই; Oxlint formatter নয় |

সম্পন্ন follow-ups-এর evidence:
[provider](fake-provider-checkpoint.md), [result storage](job-results-checkpoint.md),
[runner](fake-runner-checkpoint.md), [result API](job-results-api-checkpoint.md),
[dispatch](fixture-dispatch-checkpoint.md), [web integration](web-fixture-checkpoint.md),
[artifact API](artifact-api-checkpoint.md), [sample preview](sample-preview-checkpoint.md)।
এগুলোকে শুধু মূল micro-step table-এ আলাদা row ছিল না বলে আবার বানাবে না।

## Canonical contract ও recovery gap ledger

Section 5 হলো পূর্ণ V1 target contract, বর্তমান API/schema-এর বর্ণনা নয়। Initial
tables থাকা মানে full contracts সম্পন্ন নয়। এই সংশোধনে phase boundary স্পষ্ট হলো:

**Phase 1 baseline — 1.17 pass করার আগে আবশ্যক:**

- বর্তমান পাঁচ entity (`projects`, `characters`, `voices`, `shots`, `render_jobs`)-র
  persisted fields ও সংশ্লিষ্ট existing API shapes-এর versioned typed baseline এবং
  matching JSON Schema থাকবে; নাম/default/nullability/validation-এর পার্থক্য প্রকাশিত
  contract-এ স্পষ্ট হবে। API endpoint না থাকা `shots`-এর baseline-ও কেবল database
  table বলে পূর্ণ typed/schema contract ধরে নেওয়া যাবে না।
- migration chain ও existing-data backward reads যাচাই হবে; baseline contract
  মেলাতে schema change প্রয়োজন হলে আলাদা migration ও data-preservation checks লাগবে।
  পুরোনো `0001_initial` rewrite বা নিঃশব্দে existing row reinterpret করা যাবে না।
- source/evidence-এ এই baseline requirements এখনো আংশিক। এক contract করে bounded
  `1.17a`, `1.17b` ইত্যাদি sub-step-এ বাকি অংশ সম্পূর্ণ করতে হবে। শুধু নথিতে ভবিষ্যৎ
  phase লিখে baseline complete বলা যাবে না।

**পরবর্তী feature phases — আবশ্যক, কিন্তু Phase 1 baseline-এর সমার্থক নয়:**
Strict StoryPlan/পূর্ণ planning ShotPlan 3.1-এ; character reference/traits,
voice consent/provider এবং GPU cost/retry-এর field তাদের নিচের feature step-এ।
সেই feature চালুর আগে সংশ্লিষ্ট contract/version/migration সম্পূর্ণ হতে হবে।
Phase 1 baseline PASS হলেও এই পূর্ণ V1 contracts অসম্পূর্ণই থাকবে।

| ঘাটতি | বর্তমান প্রমাণ | প্রয়োজনীয় feature/phase সংযোগ |
| --- | --- | --- |
| Project target contract | API duration 1–600 বা unset গ্রহণ করে, V1 target 30–60; aspect ratio/FPS/language/style/character-voice relations অনুপস্থিত; DB timestamps সব API response-এ নেই | existing Project baseline: 1.17; duration contract/planner inputs: 3.1/3.3; character relation: 3.4; voice relation: 7.10; remaining aspect/FPS/language/style controls: 9.1 |
| CharacterProfile | name/description metadata আছে; full immutable traits, negative traits, sheet/adapter/provenance contract নেই | existing metadata baseline: 1.17; traits: 3.4/5.7; reference/provenance/sheet/adapter fields: 5.6–5.10 |
| VoiceProfile | metadata আছে; `voice_type` বনাম target `type`, audio/consent/provider contract নেই | existing metadata/name mapping baseline: 1.17; provider contract: 7.1; consent/audio fields: 7.6/7.7; dialogue: 7.10 |
| StoryPlan / planning ShotPlan | minimal `shots` table ও status column আছে; strict plan schema, references/artifacts/attempts/errors ও resumable state machine নেই | persisted shots baseline: 1.17; strict StoryPlan/planning ShotPlan: 3.1; state/resume: 3.5–3.8; derived media fields: 5.11/6.6/8.7 |
| RenderJob / shared schemas | minimal job API আছে; pipeline version, cost/retry/error contract ও পূর্ণ versioned schema publication নেই; browser types বর্তমান response-এর জন্য | existing job baseline/schema publication: 1.17; pipeline/retry/error contract: 3.5/3.6; GPU cost/idempotency: 4.3/4.4; integration: 9.3 |
| Recovery | saved rows/results থাকে; abrupt crash-এর orphan job reconcile/resume নেই | 3.5/3.6-এ recovery/state-machine scope, 9.3-এ API-restart end-to-end check; restart persistence-কে এখনই resume বলবে না |

## অবশিষ্ট implementation queue

1.12–1.13 সম্পন্ন; নিচের queue 1.14 থেকে শুরু। একবারে একটি bounded micro-step করবে।

| ক্রম | কাজ | সম্পূর্ণ হওয়ার শর্ত |
| --- | --- | --- |
| 1.14 | Structured pipeline logging | বিদ্যমান error logging পুনরায় বানানো নয়; প্রয়োজনীয় lifecycle context/redaction সম্পূর্ণ |
| 1.15 | Formatter configuration/check | backend/frontend check; unrelated reformat নয় |
| 1.16 | এক-command startup | API/web start/stop ও port-error behavior যাচাই |
| 1.17 | বিস্তারিত Phase 1 audit ও full regression gate | Section 7 tasks, উপরের schema gap resolution/mapping ও সব applicable checks complete; নইলে PARTIAL |
| Phase 2-তে প্রবেশ | 1.17 pass ও মালিকের phase authorization-এর পরে | আগে বিদ্যমান 2.1–2.5-এর acceptance/robustness gaps, তারপর 2.6 onward; নিচের media status দেখবে |

পরবর্তী step source-এর সঙ্গে মিলিয়ে নির্বাচন করবে; এই তালিকায় পরে completion
নথিভুক্ত হলে completed row skip করবে। হারানো পুরোনো report বা পুরোনো “next”
নির্দেশের কারণে completed feature নতুন করে বানাবে না।

## Phase 2 ও পরের কাজ

| Step / অংশ | বর্তমান অবস্থা | বাকি / গ্রহণযোগ্যতার সীমা |
| --- | --- | --- |
| 2.1 | FFmpeg/ffprobe wrapper, argument arrays, version/probe tests আছে | full composer completion নয় |
| 2.2 | fixture files ও probe checks আছে; PARTIAL | পুরোনো image/video/audio-এর provenance অসম্পূর্ণ; silent WAV-এর local source/reproduction documented |
| 2.3 | image-to-video আছে; existence/duration check নথিভুক্ত | full visual playback review-এর পৃথক প্রমাণ নেই |
| 2.4 | normalize আছে; PARTIAL | test codec/FPS/dimensions assert করে না; code audio সরায়, required audio-format normalization নেই |
| 2.5 | simple concat ও ±0.5s duration check আছে | apostrophe escaping, relative paths, shared concat-list filename robustness বাকি |
| 2.6–2.8 | অসম্পূর্ণ | dialogue/background audio mixing, fades, SRT/burn-in, thumbnail, reproducible manifest |
| 2.9 | provider-এর কিছু invalid-media validation আছে; composer/UI gate অসম্পূর্ণ | corrupt/missing media ও insufficient-disk-এর পরিষ্কার বাংলা UI errors |
| 2.10 | পূর্ণ phase gate বাকি | অসম্পূর্ণ media requirements মিটিয়ে Phase 1-সহ regression |
| Phase 3 | নতুন StoryPlan planner নেই | strict schemas, deterministic planner/repair/retry, duration split, traits injection, state/resume, edit/approve |
| Phase 4 | নতুন remote worker/RunPod adapter নেই | contracts, worker/capabilities/authenticated artifacts, retry/idempotency, budget/secrets, compute/storage lifecycle, অনুমোদিত real smoke test |
| Phase 5–6 | Character metadata আছে; legacy optional image code আছে | verified models/workflows, reference upload, consistency, approved keyframes, short clips ও regeneration |
| Phase 7–8 | Voice metadata ও silent fixture আছে | TTS, consented samples, audio preview/deletion, anime lip-sync/quality review |
| Phase 9–10 | সম্পূর্ণ scene pipeline/desktop নেই | 30–60s MP4/SRT/manifest, restart/resume, quality/cost regression, cleanup, পরে desktop |

Media evidence: [wrapper source](../animation_studio/media/ffmpeg.py),
[wrapper tests](../tests/test_media_wrapper.py), [fixture provenance](../tests/fixtures/README.md)।

## Legacy starter-এর সীমা

`app.py` / `web_app.py`-এ deterministic image/storyboard/GIF ও optional FFmpeg
MP4 conversion আছে। এগুলো নতুন shot pipeline বা verified real AI নয়।
[পুরোনো starter plan](../%23%20Project%20plan%3A%20Animation%20Studio%20Starter.prompt.md)
ঐতিহাসিক reference; তার real-pipeline-first order বর্তমান queue নয়।
`apps/web/README.md`-এর পুরোনো demo/tick বর্ণনা 1.13-এ বর্তমান background sample,
preview/download ও retry নির্দেশ দিয়ে সংশোধন করা হয়েছে।

পরিকল্পনা সংশোধনের ঐতিহাসিক যাচাই: [plan reconciliation report](plan-reconciliation-2026-09-09.md)।
সর্বশেষ implementation যাচাই: [sample preview checkpoint](sample-preview-checkpoint.md)।
