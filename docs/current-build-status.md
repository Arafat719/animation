# বর্তমান কাজ ও বাকি ধাপ

দৈনন্দিন কাজ শুরু: [সংক্ষিপ্ত resume](RESUME.md) → শুধু বর্তমান phase।
[নথির সূচি](plan/INDEX.md)। এই ledger বিস্তারিত ইতিহাস; প্রতিবার পুরোটা পড়া জরুরি নয়।

তারিখ: ২০২৬-০৯-১৯। **1.17 / local Phase 1 gate PASS।**
[পূর্ণ audit ও evidence](phase-1-final-gate-2026-09-15.md)।
Master plan requirements নির্ধারণ করে; পুরোনো checkpoint-এর “next/missing” ঐতিহাসিক।

## সম্পন্ন

| কাজ | অবস্থা / প্রমাণ |
| --- | --- |
| 1.1–1.11 ভিত্তি | API, settings, SQLite migrations, React pages, fixture jobs ও polling |
| 1.12–1.13 | Artifact serve/download এবং browser preview/retry |
| 1.14 | Structured pipeline logging, context/redaction ও committed lifecycle |
| 1.15 | Incremental backend/frontend formatter gate |
| 1.16 | এক-command API/Vite startup ও cleanup |
| 1.17a–e | পাঁচ entity-র versioned persisted/API baseline ও result/provider mapping; ১৭ schema |
| 1.17f | Project status ও RenderJob state/progress NULL API/UI support; data rewrite নেই |
| 1.17 | [পূর্ণ Phase 1 local gate PASS](phase-1-final-gate-2026-09-15.md) |

## যাচাই ও সীমা

- **Local Phase 2 / 2.10 PASS**: [পূর্ণ report](phase-2-final-gate-2026-09-16.md)।
- সর্বশেষ **৩৮৬ backend tests PASS**, তিন পুরোনো warning; formatter, ১৭ schema drift ও pip check PASS।
- Manifest-driven exact replay ও audio/video timeline synchronization PASS।
- অপরিবর্তিত UI/API-এর সর্বশেষ [2.9 frontend/browser evidence](composer-errors-checkpoint.md) PASS; final gate-এ পুনরায় চালানো হয়নি।
- Linux/Python 3.12 local checks; remote CI/Python 3.11 নতুন যাচাই নয়।
- Legacy formatting debt: ২৭ Python ও ১১ frontend/helper file। Git object সমস্যা মেরামত হয়নি; commit হয়নি।
- Runtime user database খোলা হয়নি; real AI/GPU কাজ হয়নি। পূর্ণ V1 ও automatic recovery বাকি।

## Canonical contract ও পরের feature mapping

Phase 1 baseline সম্পন্ন; Section 5-এর পূর্ণ V1 fields তাদের feature চালুর আগে লাগবে।

| Contract / feature | বর্তমান | পরবর্তী ধাপ |
| --- | --- | --- |
| Project | [v1 baseline](contracts/project-v1.md), NULL response support | duration/planning 3.1/3.3; character 3.4; voice 7.10; aspect/FPS/style 9.1 |
| Character | [metadata baseline](contracts/character-v1.md), opaque reference text | traits 3.4/5.7; references/provenance/sheets 5.6–5.10 |
| Voice | [metadata baseline](contracts/voice-v1.md) | provider 7.1; consent/audio 7.6/7.7; dialogue 7.10 |
| Shot | [persisted baseline](contracts/shot-v1.md); no endpoint | StoryPlan/planning ShotPlan 3.1; state/resume 3.5–3.8; media 5.11/6.6/8.7 |
| RenderJob | [baseline/results/provider schemas](contracts/render-job-v1.md), NULL support | retry/pipeline/recovery 3.5/3.6; GPU cost/idempotency 4.3/4.4; integration 9.3 |

## পরবর্তী কাজ

**3.1 সম্পন্ন:** strict StoryPlan ও planning ShotPlan, ১৯টি published schema।
[চুক্তি ও যাচাই](contracts/story-plan-v1.md)। বর্তমান source-এর আগে থেকে থাকা
schema/tests যাচাই করা হয়েছে; schema_version-এর boolean/float coercion বন্ধ করা হয়েছে।
**3.2 সম্পন্ন:** replaceable PlannerProvider ও deterministic fixed mock।
[Checkpoint](mock-planner-checkpoint.md): 40 targeted tests, formatting ও 19 schema checks PASS।
**3.3 সম্পন্ন:** 30–60s splitter ও mock integration;
[checkpoint](duration-splitter-checkpoint.md): 88 targeted tests, formatting ও 19 schema checks PASS।
**3.4 সম্পন্ন:** caller-supplied visual/negative traits দৃশ্যমান চরিত্র অনুযায়ী
image/motion/negative prompt-এ injection; [checkpoint](character-traits-checkpoint.md)।
Baseline 88 ও final 99 targeted tests, 19 schema snapshot এবং formatting PASS।
Persisted/API schema অপরিবর্তিত; trait extraction/storage ও UI wiring হয়নি।
**3.5 সম্পন্ন:** pure shot lifecycle state machine; pending/running/failed থেকে
অনুমোদিত transition, terminal completed/cancelled, structured failure এবং retry attempts।
[Checkpoint](pipeline-state-checkpoint.md): 136 targeted tests (37 নতুন state tests),
19 schema snapshots ও দুই Python file formatting PASS।
অন্য shot/artifact অপরিবর্তিত; persisted schema বা fixture runner বদলায়নি।
**3.6 সম্পন্ন:** local dry-run `MockShotRunner`, JSON checkpoint ও explicit bounded retry।
[Checkpoint](mock-resume-checkpoint.md): 148 targeted tests PASS (12 নতুন);
নতুন process-এ failed third shot থেকে resume, আগের completed shots পুনরায় চলে না।
19 schema snapshots, formatting ও plan drift checks PASS।
Single-writer mock-only; media stages, concurrent persistence ও crash reconciliation বাকি।
**3.7 সম্পন্ন:** project workspace-এ read-only mock shot list ও
`GET /projects/{id}/mock-plan`; order, duration, prompt এবং total duration দেখা যায়।
[Checkpoint](shot-list-checkpoint.md): 53 targeted tests, frontend build/typecheck,
Chromium loading/empty/success/error/retry/mobile checks ও 19 schema snapshots PASS।
কোনো DB mutation/render request নেই; plan save/edit/approve এখনো হয়নি।
**3.8 সম্পন্ন:** saved plan revision, prompt edit/save, approval এবং server-gated mock render।
[Checkpoint](plan-approval-checkpoint.md): 68 targeted tests, frontend build/typecheck,
Chromium edit/save/approve/reload/render/invalidation, 19 schema snapshots PASS।
Migration `0004_plan_approval`; পুরোনো project/plan JSON অক্ষত।
Edit save-এ approval/result clear; stale revision ও unapproved run → 409।
**3.9 সম্পন্ন:** [local planner isolated test proposal](local-planner-test-proposal.md)।
CPU-only official Qwen3-4B Q4_K_M (~2.5 GB), মোট download cap 3.5 GB,
পাঁচ synthetic case, strict schema/semantic checks ও bounded runtime budget নির্ধারিত।
Read-only hardware/source ও document checks PASS; download/run হয়নি।
**অনুমোদিত isolated test (2026-09-20): acceptance FAIL**;
[ফল](local-planner-smoke-result.md)। Model/runtime checksum PASS; case A 300.02s timeout,
peak RSS 5.23 GiB, অসম্পূর্ণ JSON; বাকি চার case নিয়ম অনুযায়ী চালানো হয়নি।
Runtime বন্ধ; verified model ignored data directory-তে আছে, পুনরায় download নয়।
**সংশোধিত proposal সম্পন্ন (2026-09-20):**
[compact isolated test](local-planner-compact-test-proposal.md)। বিদ্যমান verified
model/runtime; শুধু A-এর এক call, compact schema একবার, 768-token cap, 300s timeout
অপরিবর্তিত; repair/retry ০। Model content বনাম deterministic fields/prompts আলাদা;
strict draft ও StoryPlan validation, semantic acceptance এবং metric comparison নির্ধারিত।
এটি documentation-only follow-up; model download/run, harness/adapter implementation,
timeout বৃদ্ধি বা completed কাজ পুনরায় হয়নি। Master requirements অপরিবর্তিত।
Doc links, RESUME <60 lines, status/scope, plan excerpt drift ও whitespace PASS;
app tests চালানো হয়নি। পুরোনো dirty edits/evidence অক্ষত; commit হয়নি।
**অনুমোদিত compact isolated test সম্পন্ন (2026-09-20): acceptance FAIL**;
[ফল ও semantic review](local-planner-compact-test-result.md)। Owner-এর পরবর্তী
“ok porer kaj suru koro” নির্দেশে এক-call harness/test চালানো হয়েছে।
Verified assets পুনর্ব্যবহার; নতুন download নয়। চার offline test methods ও compile PASS।
Sandbox socket বাধার সময় generation ০; escalation-এ একমাত্র call চালানো হয়েছে।
Model load 4.02s; generation 52.44s; prompt 133 tokens/7.688s, output 175 tokens/44.738s।
Request 10,097 → 1,749 bytes; peak RSS 5.20 GiB; memory/swap stop নেই।
Strict draft/StoryPlan PASS, ছয়টি 5s shot; semantic FAIL: notebook/return সম্পর্ক নেই,
actions অস্পষ্ট। Schema-valid candidate accepted/production plan নয়।
Runtime exit 0; auth 401 ও দুইভাবে port closure PASS। Retry/repair/timeout বৃদ্ধি হয়নি।
Doc links, RESUME size, scope/status, plan drift ও whitespace PASS; app tests নয়।
Ignored compact-v1 harness/evidence সংরক্ষিত; production source/DB অপরিবর্তিত।
**অর্থ অক্ষুণ্ণ রাখার proposal সম্পন্ন (2026-09-20):**
[সংশোধিত compact proposal](local-planner-semantic-test-proposal.md)। Owner-এর পরবর্তী
নির্দেশে documentation-only কাজ; exact system prompt-এ actor/action/object, ownership,
return direction ও resolution স্পষ্ট করা হয়েছে। Schema/assembly/768-token/300s budget
অপরিবর্তিত; এক call, repair/retry ০। Raw shots থেকে criterion-wise semantic evidence
বাধ্যতামূলক; copied logline/keyword দিয়ে success নয়। কোনো model run/download, harness
edit, app change বা আগের test rerun হয়নি। Master requirements অপরিবর্তিত।
Document links, RESUME size, scope/status, plan drift ও whitespace PASS।
**অনুমোদিত compact v2 test সম্পন্ন (2026-09-20): acceptance FAIL**;
[ফল](local-planner-semantic-test-result.md)। শুধু exact system prompt বদলেছে;
AST/request equality ও runner equality PASS। চার offline tests/compile PASS;
পুরোনো raw ও তিন synthetic semantic-negative example textual review হয়েছে।
এক call: 140.93s, load 4.43s; prompt 280 tokens/32.708s, output 336/108.208s।
Request 2,485 bytes; schema 930 bytes অপরিবর্তিত; peak RSS 5.28 GiB; resource stop নেই।
Strict PASS; পূর্ণ বাক্য/notebook/recipient এসেছে, কিন্তু courier/owner role অস্পষ্ট,
শেষ transfer shot-এ actor visible cast-এ নেই → semantic FAIL। Candidate accepted নয়।
Runtime exit 0; auth 401 ও independent port closure PASS। Retry/download/timeout বৃদ্ধি নয়।
Doc links/RESUME/status/plan drift/whitespace PASS; production source/DB অপরিবর্তিত।
**Offline failure analysis সম্পন্ন (2026-09-20):**
[Evidence ও সিদ্ধান্ত](local-planner-offline-failure-analysis.md)। দুই raw output থেকে
saved candidate হুবহু reproduce; actions অপরিবর্তিত; token/character cap exhaustion নেই।
তিন in-memory probes: empty visible/unrelated action structural accept, unknown ID reject।
Role/ownership/possession/transfer facts ও action-visible consistency structural checks-এ নেই;
assembly/parser corruption নয়। Model-এর internal cause/capability limit প্রতিষ্ঠিত নয়।
Doc links/RESUME/status/plan drift/whitespace PASS; source/harness/raw evidence অপরিবর্তিত।
Model run/download/repair/timeout বৃদ্ধি হয়নি; app tests নয়।
**Isolated semantic contract/fixture proposal সম্পন্ন (2026-09-20):**
[Reviewable specification](local-planner-semantic-contract-proposal.md)। Explicit
roles, notebook owner/holder, ছয় event kinds, custody/visibility checks ও stable
error codes নির্ধারিত। Automated PASS-এর পরে REVIEW_REQUIRED; narrative contradiction
manual review-তে FAIL, semantic success দাবি নয়। ৩ positive, ১২ negative families,
৩ review-only ও দুই legacy fixture case নির্ধারিত; implementation হয়নি।
Doc links/RESUME/status/plan drift/whitespace PASS; model/code/master অপরিবর্তিত।
**Offline semantic validator/fixtures সম্পন্ন (2026-09-21):**
[ফল](local-planner-semantic-contract-result.md)। Ignored semantic-contract-v1-এ
strict role/reference/event/custody/visibility/return checks, stable code/path এবং
REVIEW_REQUIRED boundary implemented। ৬ targeted test methods/compile PASS;
27 fixture case expected outcome PASS, input immutability/candidate mapping যাচাই।
Narrative mismatch fixtures textual review FAIL/UNRESOLVED; automated semantic PASS নয়।
Schema 1,947 bytes; schema-only comparison request 3,506 bytes; নতুন token cost অমাপা।
Model calls ০; production/পুরোনো harness/raw evidence অপরিবর্তিত; dependency install নয়।
Doc links/RESUME/status/plan drift/whitespace PASS; full app suite নয়।
**Semantic contract model-test proposal সম্পন্ন (2026-09-21):**
[Exact scope/prompt/budget](local-planner-semantic-model-test-proposal.md)। Existing
contract অপরিবর্তিত; exact request 4,222 bytes, schema 1,947 bytes। Verified asset,
এক call, 768-token/300s caps, repair/retry ০; REVIEW_REQUIRED ও narrative review
আলাদা। Schema-conversion failure-এ stop; silent fallback নয়। নতুন token cost অমাপা।
Documentation-only; model run/harness edit হয়নি। Links/status/RESUME/drift/whitespace PASS।
**Semantic contract model test সম্পন্ন (2026-09-21): acceptance FAIL**;
[ফল](local-planner-semantic-model-test-result.md)। নতুন চার harness tests/compile PASS;
এক call 222.91s, prompt 436/output 395 tokens; peak RSS 5.25 GiB; resource stop নেই।
JSON shape PASS; REFERENCE $.b[4].e.object → declared N-এর বদলে :; candidate নেই।
Diagnostic review-এ shot 1 pickup/action mismatch ও scene placeholders পাওয়া গেছে।
Runtime exit 0/auth 401/independent port closure PASS; retry/repair হয়নি।
Contract/পুরোনো evidence/production অপরিবর্তিত; doc checks PASS।
**Semantic-run offline evidence review সম্পন্ন (2026-09-21):**
[Review](local-planner-semantic-run-review.md)। Stream deltas = raw content এবং
request schema = validator SCHEMA PASS; unmodified raw-তে exact REFERENCE reproduce।
Colon bounded-string shape মেনে চলে, object equality ভাঙে; client corruption নয়।
Prompt-label copying correlation এবং shot 1 action/event mismatch পৃথক findings;
internal cause/capability দাবি নয়। Raw repair/custody bypass বা code/model run হয়নি।
Doc links/RESUME/status/drift/whitespace PASS; আগের acceptance FAIL বহাল।
**Raw failure regression সম্পন্ন (2026-09-21):**
[ফল](local-planner-failure-regression-result.md)। L3 exact model raw fixture ও
origin/source/hash/expected error path manifest-এ যোগ; generator পুনর্গঠন বজায় রাখে।
Placeholder/action-event diagnostic review আলাদা; association test semantic inference নয়।
৯ targeted methods/28 fixture outcomes/compile PASS; stream/schema equality এবং
REFERENCE rejection-before-assembly PASS। Validator ও আগের fixture bytes অপরিবর্তিত।
Doc checks PASS; model/production change হয়নি; original acceptance FAIL বহাল।
**Contract/run design review সম্পন্ন (2026-09-21):**
[Decision/specification](local-planner-contract-run-design-review.md)। পৃথক offline
request-bound policy নির্বাচন: notebook ID const + Python equality, field-specific
placeholder rejection; old semantic validator ও REVIEW_REQUIRED boundary অপরিবর্তিত।
Model/derived provenance, error precedence ও offline fixture expectations নির্ধারিত।
Event-to-text generation এখন নির্বাচিত নয়; model quality claim নয়।
Docs-only; links/RESUME/status/drift/whitespace PASS; implementation/run হয়নি।
**Request-bound policy offline implementation সম্পন্ন (2026-09-21):**
[ফল](local-planner-request-bound-policy-result.md)। নতুন isolated policy.py-এ notebook
ID const/Python equality ও field-specific exact placeholder rejection; পুরোনো validator
অপরিবর্তিত। ৬ targeted methods/17 fixture outcomes/compile PASS; rejected input
assembly-তে যায় না; mapping/immutability/schema-leaf isolation যাচাই।
Narrative mismatch REVIEW_REQUIRED; manual fixture review FAIL; model success নয়।
Schema 1,985 bytes; schema-only request 4,260 bytes, run-ready নয়।
Doc checks PASS; model calls ০; production/master/পুরোনো evidence অপরিবর্তিত।
**Exact request-bound model-test proposal সম্পন্ন (2026-09-21):**
[Scope/prompt/budget](local-planner-request-bound-test-proposal.md)। Notebook ID ও
concrete scene instructionsসহ exact request 4,588 bytes/schema 1,985 bytes।
এক call, 768-token/300s caps, repair/retry ০; policy + independent narrative rubric।
আরও narrative failure হলে owner suitability review; automatic prompt loop নয়।
Docs-only; links/RESUME/status/drift/whitespace PASS; model/harness edit হয়নি।
**Request-bound এক-call test সম্পন্ন (2026-09-22): acceptance FAIL**;
[ফল](local-planner-request-bound-test-result.md)। Owner-এর নির্দেশে exact run; চার
harness tests/compile PASS। Load 13.66s; generation 300.001s timeout, 1,648-char
incomplete JSON; final usage unavailable। Peak RSS 5.30 GiB, memory stop নেই।
Concrete scene/visible notebook IDs prefix-এ আছে; initial holder+pickup conflict ও
action/event mismatch-ও আছে। Full policy/narrative validation হয়নি; candidate নেই।
Runtime exit 0/auth 401/independent closure PASS; retry/repair/budget বৃদ্ধি নয়।
Docs checks PASS; policy/production/পুরোনো evidence অপরিবর্তিত।
**Model+CPU suitability review সম্পন্ন (2026-09-22):**
[Evidence/বিকল্প/সুপারিশ](local-planner-suitability-review.md)। Owner-এর বর্তমান
নির্দেশে পাঁচ নির্দিষ্ট run report পর্যালোচনা: accepted plan ০; দুই timeout,
দুই strict PASS/semantic FAIL, এক reference rejection। এটি reliability estimate নয়।
বর্তমান path স্থগিত রাখার সুপারিশ; owner decision pending। Quality ও latency দুই
সীমাই আছে; memory stop নেই; অন্য model/hardware-এর suitability অমাপা।
Docs-only; links/RESUME/status/scope/plan drift/whitespace PASS; app/model tests নয়।
পুরোনো evidence/assets/production/master অপরিবর্তিত; commit হয়নি।
**ছোট-model CPU alternative proposal সম্পন্ন (2026-09-22):**
[নির্দিষ্ট asset/budget/gate](local-planner-small-model-proposal.md)। Owner-এর
“porer kaj suru koro” নির্দেশে proposal তৈরি; CPU/GPU পছন্দের উত্তর না আসায়
বর্তমান CPU candidate প্রস্তাবিত, owner selection/execute approval দাবি নয়।
Official Qwen3-1.7B Q8_0 pinned revision, pointer size 1,834,426,016 bytes ও SHA256
যাচাই; model bytes download নয়। Existing request/policy/runtime reuse প্রস্তাব;
300s/768 tokens/6 GiB অপরিবর্তিত; acquisition 1.90 GB body/45 মিনিট, retry ০।
Quality/latency অমাপা; ছোট model-এ semantic regression হতে পারে।
Docs links/RESUME/status/scope/drift/whitespace PASS; app/model tests নয়।
**ছোট-model acquisition ও এক-call test সম্পন্ন (2026-09-22): acceptance FAIL।**
[ফল ও diagnostic](local-planner-small-model-result.md)। Owner-এর পরবর্তী নির্দেশে
exact proposal execute। Qwen3-1.7B Q8_0 size/SHA256 PASS; acquisition 1.83444 GB body,
25.57 মিনিট, retry ০। নতুন ৭ offline tests/compile PASS; policy baseline reuse।
Request delta শূন্য; load 5.50s, generation 215.215s, finish stop, output 692 tokens।
ROLE $.c rejection: দুই courier; full custody/StoryPlan assembly হয়নি; candidate নেই।
Raw actor-ID/possession/visibility/repeated beat সমস্যাও আছে; corrected rerun নয়।
RSS 2.78 GiB; resource stop নেই; runtime exit 0/auth 401/port closure PASS।
Docs links/RESUME/status/scope/drift/whitespace PASS; production/master অক্ষত।
Candidate স্থগিত।
**দুই-path owner decision review সম্পন্ন (2026-09-22):**
[তুলনা/ব্যয়/নির্বাচন](local-planner-owner-decision-review.md)। Owner “porer kaj koro”
নির্দেশে existing reports review: 4B-এর ৫ এবং 1.7B-এর ১ call-এ accepted ০;
reliability estimate নয়। ছোট model-এর latency/RSS কমলেও quality gate FAIL।
দুই পরীক্ষিত CPU path স্থগিত রেখে mock flow বজায় রাখার সুপারিশ; owner সিদ্ধান্ত নয়।
পরবর্তী owner নির্দেশে সিদ্ধান্তের checkpoint নিচে নথিভুক্ত।
**Delegated পথ নির্বাচন সম্পন্ন (2026-09-22):** Owner “jeta valo mone koro setai koro”
বলে Codex-কে নির্বাচন করতে বলেছেন। দুই পরীক্ষিত CPU planner experiment স্থগিত
রেখে existing mock flow বজায় রাখার পথ নির্বাচিত ও কার্যকর। Assets/evidence/markers
সংরক্ষিত; real adapter না থাকায় production configuration edit প্রয়োজন হয়নি।
Experiment queue বন্ধ; সক্রিয় next micro-step নেই। নতুন scope/hypothesis এলে
পুনর্বিবেচনা; একই review/proposal/run loop নয়। Phase 3 অসম্পূর্ণ বহাল।
Docs links/RESUME/status/scope/drift/whitespace PASS; model/source/logs/assets
অপরিবর্তিত; app/model/offline tests পুনরায় নয়; master edit/commit হয়নি।
নতুন run/download/retry/timeout বৃদ্ধি নয়; accepted plan/test-set evidence blocker;
**3.10 adapter এখনো শুরু/অনুমোদিত হয়নি**।
Phase 3-এর বাকি ধাপ অসম্পূর্ণ।

**Phase 3 offline repair/retry gap review সম্পন্ন (2026-09-23):**
[ঘাটতি ও নির্দিষ্ট implementation step](planner-repair-gap-review.md)। Owner নতুন
scope অনুমোদন করেছেন: model ছাড়া gap review/step নির্বাচন। Source review-এ input
validation ও shot retry আছে; planner raw-output repair orchestration নেই।
নির্বাচিত next step: আলাদা offline runner + scripted fake tests; max_retries 0–2,
default 0; strict output/request-duration checks; success REVIEW_REQUIRED।
Implementation অনুমোদন pending; API/production/model পরিবর্তন নয়। বন্ধ experiment
queue খোলা হয়নি। Docs links/RESUME/status/scope/drift/whitespace PASS; app tests নয়।

**Offline planner repair runner সম্পন্ন (2026-09-23):**
[Checkpoint](planner-repair-checkpoint.md)। Owner implementation অনুমোদন করেছেন।
পৃথক RepairProvider/repair_plan; max_retries 0–2/default 0; request deep-copy,
strict StoryPlan ও requested-duration validation; stable issue code/path।
Exhaustion typed failure; provider exception/non-string-এ retry নয়;
success REVIEW_REQUIRED। নতুন ২৯ + existing ৪০ = ৬৯ targeted tests PASS।
Docs links/RESUME/status/scope/drift/whitespace PASS; API/DB/UI/schema অক্ষত।
Model experiment queue বন্ধ; model run/download নয়; commit হয়নি। Blocker নেই।
পরের bounded কাজ offline request-fidelity gap review; অনুমোদন pending।

**Offline request-fidelity review সম্পন্ন (2026-09-23):**
[Source findings ও next step](planner-request-fidelity-review.md)। Owner review
অনুমোদন করেছেন। Duration checked; supplied cast/traits ও fresh lifecycle runner-এ
checked নয়। PlanStore downstream freshness reject করে; shared schema persisted
lifecycle অনুমোদন করে। পরের একমাত্র step: runner-local NON_FRESH_PLAN rejection
ও targeted tests; implementation অনুমোদন pending। Cast/traits পৃথক scope।
Docs links/RESUME/status/scope/drift/whitespace PASS; source/master/model অপরিবর্তিত;
app tests বা model run নয়; commit হয়নি।

**Fresh-plan lifecycle guard সম্পন্ন (2026-09-23):**
[Checkpoint](planner-fresh-plan-checkpoint.md)। Owner implementation অনুমোদন করেছেন।
Runner-local NON_FRESH_PLAN: pending/zero attempts/null error ও media paths;
stable shot/field diagnostics, duration precedence, raw output preservation ও
existing retry cap বহাল। Reference inputs/shared persisted schema অপরিবর্তিত।
১৫ নতুন case; ৪৪ repair + ৪০ existing = ৮৪ targeted tests PASS; doc checks PASS।
API/DB/UI/PlanStore/model অক্ষত; commit হয়নি। Blocker নেই। পরের bounded কাজ
supplied cast ID/name policy ও tests নির্ধারণ; অনুমোদন pending।

**Supplied cast policy/test specification সম্পন্ন (2026-09-23):**
[Policy](planner-cast-policy.md)। Required supplied ID/name subset; extras/reorder,
empty request এবং offscreen/unused cast allowed। CAST_MISSING/CAST_NAME_MISMATCH
path/order এবং schema→duration→fresh→cast precedence নির্ধারিত। Nested mutation
fixture-এর cast সংশোধন প্রয়োজন চিহ্নিত; test skip নয়। পরের bounded কাজ guard/tests
implementation; অনুমোদন pending। Traits/semantic/API আলাদা scope। Blocker নেই।
Docs checks PASS; source/master/model অপরিবর্তিত; app tests পুনরায় নয়; commit হয়নি।

**Supplied cast guard সম্পন্ন (2026-09-23):**
[Checkpoint](planner-cast-checkpoint.md)। Owner implementation অনুমোদিত। Required
ID/name subset; CAST_MISSING/CAST_NAME_MISMATCH, stable order/path এবং পূর্ববর্তী
guard precedence। Extra/reordered/offscreen cast allowed; raw rewrite নয়।
১৬ নতুন cases; mutation fixture corrected, assertions preserved। চার targeted
suites-এ ১১১ PASS; doc checks PASS। API/schema/master/model অপরিবর্তিত; commit নয়।
Blocker নেই; পরের bounded কাজ traits assembly ownership/duplication design review;
অনুমোদন pending। Phase 3/3.10 অসম্পূর্ণ।

**Traits assembly design review সম্পন্ন (2026-09-23):**
[Ownership/duplicate/overflow design](planner-traits-assembly-design.md)। Owner review
অনুমোদিত। পৃথক offline helper নির্বাচন: immutable base/assembled JSON, existing
injector একবার; exact canonical block preflight reject, overflow-এ truncation নয়।
Conservative literal detection, semantic dedup নয়। Helper/tests implementation
পরের bounded কাজ; অনুমোদন pending। Runner/API wiring পৃথক scope।
Docs checks PASS; source/master/model অপরিবর্তিত; app tests পুনরায় নয়; commit হয়নি।

**Offline traits helper সম্পন্ন (2026-09-23):**
[Checkpoint](planner-traits-checkpoint.md)। Owner implementation অনুমোদন করেছেন।
Immutable base/assembled JSON; profile ID/name checks; exact reserved blocks reject;
existing visible-only injector একবার, overflow typed failure/no truncation।
২১ নতুন + ১১১ existing = ১৩২ targeted tests PASS; docs checks PASS। Existing
injector/runner/API/schema/master/model অপরিবর্তিত; commit নয়। Blocker নেই।
পরের bounded কাজ runner–traits integration error/retry policy নির্ধারণ;
অনুমোদন pending। Phase 3/3.10 অসম্পূর্ণ, CPU experiment queue বন্ধ।

**Phase 3 integrated offline acceptance সম্পন্ন (2026-09-25):**
[পূর্ণ evidence ও সীমা](phase-3-offline-acceptance.md)। Owner বাকি offline integration
শেষ ও পরে Phase 4 ধরার অনুমোদন দিয়েছেন। PlannerService/API preview wiring,
raw-base mock draft, traits assembly+bounded repair integrated; 422 exhaustion,
read-only DB ও approval/revision gates verified। ২৫২ targeted tests PASS,
web build/typecheck/browser PASS; formatting/doc checks PASS। আগের usage-limit
approval rejection resolved; temporary DB/local browser execution সম্পন্ন।
Offline queue শেষ; পূর্ণ Phase 3 BLOCKED at real planner/3.10/lifecycle evidence।
Phase 4 prerequisite-সাপেক্ষে অনুমোদিত, শুরু হয়নি। নতুন policy loop নয়; viable real
planner path অথবা explicit phase-order revision প্রয়োজন। Model run/download নয়;
public schema/unrelated edits অক্ষত; commit হয়নি।

**Phase-order revision সম্পন্ন (2026-09-25):** Owner “তুমি যেটা ভালো মনে করো”
বলে প্রস্তাবিত পথ নির্বাচনের দায়িত্ব দিয়েছেন; Phase 4 mock-first পথ গৃহীত।
Master ও generated rules/Phase 4-এ সীমিত exception: Phase 3 offline PASS দিয়ে
local/mock 4.1–4.6 এগোবে; 3.10 ও real lifecycle/recovery acceptance deferred,
বাদ নয়। আগের Phase 4 implementation অনুমোদন বহাল; পরের step 4.1 generic
GPUProvider/mock contract, এখনও শুরু হয়নি। 4.7 proposal মাত্র; real execution,
paid resource ও বড় download-এর approval rules অপরিবর্তিত। এটি উপরোক্ত পুরোনো
prerequisite blocker-কে শুধু mock scope-এ supersede করে। RESUME/offline report sync;
excerpt drift, links/scope ও whitespace PASS; docs-only বলে app tests চালানো হয়নি।
Unrelated work অক্ষত; commit/model run/download/paid action হয়নি।

**Phase 4.1 সম্পন্ন (2026-09-25):** [checkpoint](gpu-provider-checkpoint.md)।
GPUProvider Protocol ও immutable validated job models, memory-only MockGPUProvider,
health/capabilities/submit/status/cancel, explicit mock progress/failure এবং terminal
cancellation semantics যুক্ত। 50 GPU tests ও ruff format/lint PASS; docs drift,
links/RESUME length/whitespace PASS। HTTP/real timeout/retry/idempotency ও real GPU
বাকি। API/UI/DB/public schema অপরিবর্তিত; full app/media suite নয়। পরের অনুমোদিত
step 4.2 fake remote GPU HTTP server; 3.10 deferred acceptance বহাল। পুরোনো RESUME
prerequisite wording master-এর অনুমোদিত exception অনুযায়ী সংশোধিত। Commit নয়।

**Phase 4.2 সম্পন্ন (2026-09-25):** [checkpoint](mock-gpu-http-checkpoint.md)।
পৃথক authenticated mock GPU HTTP app-এ health/capabilities/submit/status/cancel।
Existing immutable GPU contract reuse; error codes normalized, raw invalid input
ফেরত নয়। Python advance test control remote endpoint নয়। 77 GPU/HTTP tests PASS;
sandbox timeout-এর পরে অনুমোদিত local execution PASS। Loopback TCP smoke PASS,
server stopped; ruff/docs drift/links/whitespace PASS। Full app/media suite নয়।
পরের অনুমোদিত 4.3 timeout/retry/idempotency; real GPU/media/paid action হয়নি।

**Phase 4.3 সম্পন্ন (2026-09-25):** [checkpoint](gpu-http-retry-checkpoint.md)।
HTTPGPUProvider-এ per-I/O timeout, elapsed retry budget, bounded exponential backoff,
normalized errors ও response identity checks। Mock server-এ atomic idempotency:
এক key/payload এক job; mismatch 409। Lost response ও concurrent replay, cancel retry,
actual socket timeout-সহ 112 tests PASS; 2 existing dependency warnings। Ruff এবং
plan drift/links/RESUME length/whitespace PASS। Existing HTTP pins runtime-এ সরানো,
upgrade/install নয়। Memory-only replay restart-safe নয়; full app/media suite নয়।
পরের অনুমোদিত 4.4 budget/dry-run estimator; real GPU/paid action/commit হয়নি।

**Phase 4.4 সম্পন্ন (2026-09-25):** [checkpoint](gpu-budget-checkpoint.md)।
Explicit BudgetConfig, validated render workload, Decimal dry-run estimate ও guarded
selected-shot submit। Hourly price/render GPU minutes/shot attempts/render cost
সীমা অতিক্রম করলে provider/HTTP call শূন্য। Reserved attempts/startup included;
upward rounding, exact boundaries ও invalid inputs verified। Budget/GPU suite
79 PASS; ruff ও docs checks PASS। Existing HTTP/server source অপরিবর্তিত; 4.3 evidence
retained। Compute-only preflight; persistent ledger/runtime caps/production wiring
বাকি। পরের অনুমোদিত 4.5 secrets/redaction; paid action বা commit হয়নি।

**Phase 4.5 সম্পন্ন (2026-09-25):** [checkpoint](gpu-secrets-checkpoint.md)।
ANIMATION_GPU_TOKEN loader/SecretStr ও client/worker env factories; missing/invalid
secret fail-closed। Existing output format রেখে known token-এর raw/escaped forms,
header/extra/traceback redact; repeated setup ও rotation covered। GPU/secrets/budget/
HTTP/retry 157 tests PASS, 2 existing dependency warnings; ruff/docs checks PASS।
Configured handlers-এর বাইরে print/raw LogRecords/unregistered secrets covered নয়।
Production deployment logging/expiry service বাকি। পরের অনুমোদিত 4.6 RunPod skeleton
mock tests; বাস্তব credentials পড়া, paid action, download বা commit হয়নি।

**Phase 4.6 সম্পন্ন (2026-09-25):** [checkpoint](runpod-skeleton-checkpoint.md)।
Mock-only RunPodGPUProvider skeleton: REST v1 Pod snapshot ও existing HTTP worker
contract, পৃথক control/worker credentials। Shared GPU boundary tests reuse; Pod
responses allowlisted, unknown/malformed/error paths covered। Live transport/env
startup disabled; provisioning/lifecycle mutations নেই। 214 targeted tests PASS,
2 existing dependency warnings; ruff/docs checks PASS। Real deployment/inference/
artifacts/storage gates বাকি। 4.7 draft; pinned deployment/real health prerequisite বাকি-only cost/action preview; paid launch
আলাদা explicit approval-সাপেক্ষ। No real API call/download/paid action/commit।

**Phase 4.7 draft প্রস্তুত, exact preview অসম্পূর্ণ (2026-09-25):**
[Launch preview](runpod-launch-preview.md)। Official public rates/storage/cleanup
যাচাই; A5000 health-only 15-minute provisional subtotal ~$0.068195 (tax বাদ),
proposed cap $0.10—অনুমোদিত/enforced নয়। Region/live quote/account costs অজানা।
Pinned worker image/digest, real GPU health, live lifecycle/timeout controls অনুপস্থিত;
তাই paid approval-ready নয়, paid permission চাওয়া হয়নি। পরের local prerequisite
worker packaging/GPU-health contract; এরপর 4.7 final। 4.8+ execution ও Phase 3 gate
বহাল। Arithmetic/docs checks PASS; docs-only, source/app tests পরিবর্তন নয়; no paid
API call/download/commit।

**Phase 4 local worker prerequisite source সম্পন্ন (2026-09-25):**
[Checkpoint](gpu-health-packaging-checkpoint.md)। Authenticated GPU device-health
worker, bounded nvidia-smi probe, honest empty inference capabilities; Docker recipe
ও digest-required allowlisted deterministic context packager। 231 GPU/health/package
regression tests PASS, 2 existing warnings; ruff/docs checks PASS। Actual probe
মূল্য tool_missing; Docker/Podman/socket নেই। Verified base/final image digest,
container build/run ও GPU execution বাকি; 4.7 final নয়। পরের local builder/base/build
smoke prerequisite; source restart নয়। No install/download/paid action/commit।

**Local builder readiness (2026-09-26):** [checkpoint](gpu-builder-checkpoint.md)।
Rootless namespace/mount PASS; UID helpers/Podman missing, sudo password required।
Official registry Python linux/amd64 base manifest SHA256 verified; pinned context
30,720 bytes ও embedded file hashes PASS। Actual layers/build/smoke নয়। Owner-কে
terminal-এ podman/uidmap install করতে বলা হয়েছে; automatic approval rejection নয়।
Tools পাওয়া মাত্র current source build/smoke থেকে resume; no package install,
image/model download, cloud action বা commit। Docs/drift/whitespace checks PASS।

## Phase 2 ও পরের কাজ

| Step / অংশ | বর্তমান অবস্থা | বাকি / গ্রহণযোগ্যতার সীমা |
| --- | --- | --- |
| 2.1 | FFmpeg/ffprobe wrapper, argument arrays, version/probe tests আছে | full composer completion নয় |
| 2.2 | নতুন composer pack সম্পন্ন | local shapes/tone/video generator, provenance/hash ও decode tests; পুরোনো provider fixtures অপরিবর্তিত |
| 2.3 | সম্পন্ন; frame/format/duration ও Chromium playback PASS | [checkpoint](image-video-checkpoint.md); দুই সেকেন্ড/২৪ frame, screenshot visual review |
| 2.4 | সম্পন্ন: H.264/AAC normalization | [guide](video-normalization.md); audio preservation/padding, stream/decode/timing checks |
| 2.5 | সম্পন্ন: concat path/concurrency/cleanup | [checkpoint](concat-checkpoint.md); stream/decode/duration/order ও failure preservation PASS |
| 2.6 | সম্পন্ন: dialogue/background mixing ও background fades | [guide](audio-mixing.md); synthetic signal/timing checks |
| 2.7 | সম্পন্ন: SRT ও optional burn-in | [guide](subtitles.md); timing/Unicode export/audio preservation tests |
| 2.8 | সম্পন্ন: integrated export bundle | [guide](render-bundle.md); thumbnail, manifest, same-toolchain reproduction |
| 2.9 | সম্পন্ন: composer error boundary ও sample export UI | [guide](composer-errors.md); missing/corrupt/disk error, retry ও ZIP |
| 2.10 | local gate PASS | [পূর্ণ report](phase-2-final-gate-2026-09-16.md); Phase 1-সহ regression, replay/sync acceptance |
| Phase 3 | 3.1–3.9 mock flow ও local planner proposal সম্পন্ন | real provider lifecycle, real stage recovery, approved experiment/real adapter ও real test-set evidence |
| Phase 4 | 4.1–4.6 mock HTTP/budget/secrets/RunPod skeleton PASS; 4.7 draft; pinned deployment/real health prerequisite বাকি | contracts, worker/capabilities/authenticated artifacts, retry/idempotency, budget/secrets, compute/storage lifecycle, অনুমোদিত real smoke test |
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
সর্বশেষ gate যাচাই: [পূর্ণ Phase 1 report](phase-1-final-gate-2026-09-15.md)।

**Builder readiness update (2026-09-26):** Owner Podman/uidmap install করেছেন;
rootless overlay check PASS। নতুন install preference RESUME-তে সংরক্ষিত। Current
source context প্রস্তুত; image build pip dependencies install করে বলে exact command
owner-কে দেওয়া হয়েছে। Agent build/install করেনি; পরের image inspection/smoke।

**Local image build/smoke PASS (2026-09-26):** Owner image build করেছেন; agent
exact image ID দিয়ে pull/install ছাড়াই hardened loopback container smoke চালিয়েছে।
[Evidence](../deploy/gpu-health/local-image-evidence.json): auth 401, no-GPU unhealthy,
empty capabilities, no jobs, pip-check PASS; logs token-free। Temporary container
removed/absence verified। Local image 144,892,683 bytes; manifest digest সংরক্ষিত।
No registry push/real GPU/paid action; distribution/live lifecycle prerequisites বাকি।
Docs checks PASS; source unchanged, আগের 231 tests retained।

**Image distribution preparation PASS (2026-09-26):**
[Checkpoint](gpu-image-distribution-checkpoint.md)। Tested image-এর local OCI archive
53,340,160 bytes; manifest/config/7 layer hashes ও image identity verified। Verifier
4 tests ও lint/docs checks PASS। GHCR owner-selected; namespace pending, publish
হয়নি। Image/source অপরিবর্তিত; no install/download/paid action। Next local lifecycle
deadline/cleanup mock controls; registry handoff namespace পাওয়া সাপেক্ষে।

Owner GitHub namespace দিয়েছেন: Arafat719; image target lowercase
`ghcr.io/arafat719/animation-gpu-health:health-45b4d841a9a3`। Publish এখনও হয়নি।

**Mock lifecycle controls PASS (2026-09-26):**
[Checkpoint](gpu-lifecycle-checkpoint.md)। Cooperative monotonic deadline/early exit
cleanup, scoped resource, stop failure termination fallback, failed inspection ও
retained storage-তে honest incomplete result; reconciliation tests। 99 lifecycle/
budget/GPU tests ও ruff/docs checks PASS। No live mutation/watchdog/install/publish।
Next concrete GHCR publication handoff; worker image অপরিবর্তিত।

**GHCR publication handoff প্রস্তুত (2026-09-26):**
[Concrete instructions](ghcr-publication-handoff.md): exact tested image ID ও
arafat719 destination, isolated temporary auth, push digest capture, remote config
identity verification। Official GHCR docs/installed Podman flags ও bash syntax
verified; docs checks PASS। No login/push/install; source/image unchanged। Owner
publication approval ও terminal authentication pending; paid GPU অনুমোদন নয়।

**GHCR owner publication verified (2026-09-26):** [Evidence](../deploy/gpu-health/ghcr-evidence.json)।
Owner login/push; registry-returned raw manifest SHA256 matched pushed digest ও tested
config ID। Podman single-image parse error workaround independently hash-checked;
CLI PASS দাবি নয়। No pull/install/GPU call; visibility/private access বাকি।

**Private-image access preflight সম্পন্ন (2026-09-26):**
[Checkpoint](gpu-private-access-checkpoint.md)। Anonymous GHCR token request 401;
authenticated manifest পূর্বে verified। Private-path read:packages/registry auth ও
separate worker token plan documented; visibility UI সরাসরি verified নয়। No secret
read/provider mutation/install/pull। Docs/source checks PASS; next REST lifecycle
adapter mock HTTP implementation, পুনরাবৃত্ত readiness review নয়।

**RunPod REST lifecycle mock adapter সম্পন্ন (2026-09-26):**
[Checkpoint](runpod-lifecycle-rest-checkpoint.md)। Scoped GET/POST stop/DELETE,
strict response checks, no retry/redirect/live transport; absence/desired status
কে compute/storage billing completion বলা হয় না। Relevant 67 tests PASS; lint PASS।
Initial combined TestClient run sandbox-এ stalled/interrupted; combined PASS নয়।
No install/cloud mutation/secret read। Next mock cleanup integration/recovery;
controller wiring/watchdog/live execution এখনও অসম্পূর্ণ।

**Mock REST cleanup/recovery integration সম্পন্ন (2026-09-26):**
MockRESTLifecycle bridge ও controller error handling যুক্ত; desiredStatus থেকে
stopped compute অনুমান নয়, 404-তেও storage unknown। Timeout-এর পরে next tick
আগে inspect করে; stop failure-এ termination fallback, wrong-ID rejection tested।
77 relevant tests PASS; lint/docs PASS। No install/live call। Cooperative recovery
মাত্র; independent watchdog/persistent restart recovery বাকি। Next design micro-step।

**Watchdog/restart recovery design সম্পন্ন (2026-09-26):**
[Design](gpu-watchdog-design.md): strict secret-free atomic journal, single writer,
restart-এ unfinished session close/reconcile, inspect-before-mutation, durable
attempt accounting ও unknown storage manual review নির্ধারিত। Separate runner
পরে; local power/network failure independent cloud protection নয়। No code change,
install বা paid call; docs checks PASS, prior 77-test evidence retained। Next
একটি implementation micro-step: durable mock journal/restart recovery tests।

**Durable mock session journal/restart recovery সম্পন্ন (2026-09-26):**
[Checkpoint](gpu-journal-checkpoint.md)। Strict versioned secret-field-free JSON,
0600 atomic replace/fsync, nonblocking flock, persist-before-cleanup ও restart
reconciliation implemented। Deadline preserved; attempts capped at 3; unknown
storage manual review। 93 relevant tests PASS; lint/docs PASS। No install/live I/O।
Separate autonomous runner/structured auth retry policy এখনও বাকি।

**Separate mock watchdog runner সম্পন্ন (2026-09-26):**
[Checkpoint](gpu-watchdog-checkpoint.md)। Durable arm-এর পরে READY, stdin EOF/signal
ও monotonic deadline cleanup; runner flock, restart recovery, bounded fixture
retry। Actual parent-kill/child cleanup subprocess test সহ 99 tests PASS; lint/docs
PASS। Memory-only MockLifecycle, unknown storage retained; live/REST runner নয়।
Next structured provider-error preservation/auth retry stop; external supervisor,
production admission ও paid readiness এখনও বাকি। No install/cloud call।

**Cleanup authentication retry-stop সম্পন্ন (2026-09-26):**
[Checkpoint](gpu-cleanup-auth-checkpoint.md)। CleanupResult provider_codes ও journal
last_provider_codes সংরক্ষণ করে; 401/403-এ বাকি cycle বন্ধ এবং restart-এ manual
cleanup outcome, নতুন retry নয়। Transient failure fallback অপরিবর্তিত। Optional
v1 field পুরোনো journal backward-read tested। 110 relevant tests PASS; lint/docs
PASS। Next mock REST watchdog wiring; live disabled, no install/cloud call।

**Mock REST watchdog integration সম্পন্ন (2026-09-26):**
[Checkpoint](gpu-watchdog-rest-checkpoint.md)। Fixed CLI mock scenarios দিয়ে
RunPodLifecycle→MockRESTLifecycle→durable runner যুক্ত; live transport/credentials
নেই। Parent-kill, crash/restart, 401 retry-stop, 503 attempt cap, ambiguous delete
সহ 117 tests PASS; lint/docs PASS। Fixture state process-local; real cloud state
persistence দাবি নয়। Next bounded launch-readiness gap review; no install/paid call।

**Launch-readiness gap review সম্পন্ন (2026-09-26):**
[Review](gpu-launch-readiness-review.md)। GHCR/mock watchdog completed evidence ও
live gaps পৃথক করা হয়েছে; launch draft-এর stale publication status সংশোধিত।
Next concrete local step: hung cleanup runner bounded supervisor/recovery tests।
External host, live provisioning path, Phase3/order gate, private pull ও current
quote এখনও বাকি; paid approval চাওয়া হয়নি। Docs checks PASS; prior 117-test
result retained। No source edits/test rerun/install/cloud call।

**Bounded mock supervisor সম্পন্ন (2026-09-26):**
[Checkpoint](gpu-supervisor-checkpoint.md)। Hung fixture child timeout→kill/reap;
durable attempt cap ও terminal auth preserved, no automatic restart loop। 126
relevant tests PASS; lint/docs PASS। Local callable মাত্র, live shutdown/always-on
service নয়। Owner-কে existing VPS/server availability জিজ্ঞেস করা হয়েছে; next
external execution/operator path নির্ধারণ। No install/paid call।

**Unknown-server attended health proposal প্রস্তুত (2026-09-26):**
[Proposal](gpu-attended-health-proposal.md)। Owner VPS সম্পর্কে অনিশ্চিত; recurring
server question বন্ধ। First health-only test-এর console/operator path, scoped Pod
ID, no blind create retry, stop/terminate ও storage observation handoff প্রস্তুত।
Proposal মাত্র; unattended protection/Phase3 gate/paid approval বহাল। Official
manage-Pods docs verified; docs checks PASS, prior 126 tests retained। Next account
access/non-billable configuration preview handoff। No install/account mutation।

**RunPod dashboard access owner-confirmed (2026-09-26):** account creation handoff
সম্পন্ন। Official manage-Pods flow দেখে GPU selection/rate-only handoff দেওয়া
হয়েছে; final Deploy On-Demand/top-up নয়। Account quote/private pull/paid gate
এখনও pending; কোনো agent account access বা paid action হয়নি।
