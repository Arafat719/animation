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

**GPU quote সংগ্রহের handoff (2026-09-27):** পরের কাজ শুরু করার নির্দেশে বর্তমান
4.7 prerequisites ও pending quote যাচাই। Available tools-এ owner-এর authenticated
RunPod browser access নেই; তাই actual account availability/rate সংগ্রহ অসম্পূর্ণ।
Owner-এর GPU selection screenshot অথবা GPU name/VRAM/hourly rate/region প্রয়োজন;
দেখানো storage/total estimate থাকলে সেটিও quote-এ রাখতে হবে। Deploy/payment নয়।
RESUME ও status update; whitespace/RESUME length checks PASS। Source অপরিবর্তিত,
app tests পুনরায় চালানো হয়নি। তথ্য এলে একই অনুমোদিত quote micro-step চলবে;
final paid launch-এর পৃথক approval এখনও বাকি।

**Owner budget/payment constraint (2026-09-27):** Owner জানিয়েছেন এখন GPU rental-এর
টাকা ও international payment card নেই। Paid GPU execution এবং RunPod quote/
screenshot/payment handoff স্থগিত; আগের screenshot অনুরোধ আর pending requirement নয়।
Owner পুনরায় GPU কাজ চাইলে এই পথ বিবেচিত হবে। Completed mock evidence বহাল;
real GPU acceptance অসম্পূর্ণই থাকবে। পরের কাজ বিনা খরচে local/offline অসম্পূর্ণ
scope review; নতুন phase অনুমোদন বা স্থগিত CPU experiment restart অনুমান করা নয়।
এটি operational deferral, feature requirements/acceptance gate পরিবর্তন নয়।
RESUME/status-only update; whitespace ও RESUME length checks PASS; app tests
প্রয়োজন হয়নি। কোনো install/download/payment/cloud mutation হয়নি।

**Local/offline scope review সম্পন্ন (2026-09-27):**
[Review](local-offline-scope-review.md)। Budget source/tests ও cleanup journal দেখে
নিশ্চিত: planned attempt preflight আছে, durable shot dispatch accounting নেই;
cleanup retry count এই gap পূরণ করে না। পরের micro-step ledger-only durable
shot-attempt reservation; identity conflict, duplicate key, restart, contention,
write failure ও conservative crash accounting pass criteria নির্দিষ্ট। Existing
Phase 4 local/mock authorization বহাল; নতুন phase বা paid execution নয়। Source
বদলায়নি; docs links/plan drift/whitespace/RESUME length PASS; app tests নয়।

**Local durable shot-attempt ledger সম্পন্ন (2026-09-27):**
[Checkpoint](gpu-attempt-ledger-checkpoint.md)। নতুন `gpu_attempts.py`-তে strict v1
ledger, immutable render workload/budget identity, global attempt-key replay/conflict,
planned shot cap ও fsync/atomic replace/nonblocking process lock। Raw payload persist
হয় না। No dispatch/refund; missing/corrupt state fail closed। Baseline 79 PASS;
ledger/budget/provider 100 PASS, Ruff/docs checks PASS। Spawned process exit,
concurrent last-slot ও injected durable write failure tested। Existing source/API/DB
অপরিবর্তিত; owner-এর docs edits retained। Next authorized local/mock step: guarded
mock dispatch integration, duplicate/ambiguous request-এ দ্বিতীয় submit নয়। Paid
GPU ও model experiments স্থগিত; no install/download/cloud call/commit।

**Ledger যুক্ত mock-only dispatch সম্পন্ন (2026-09-27):**
[Checkpoint](gpu-mock-dispatch-checkpoint.md)। `_reserve_once` locked freshness
থেকে fresh durable admission-এ একবার exact mock provider submit। Replay/old v1
reservation-এ `AttemptAlreadyReserved`; error/crash-এ slot consumed, automatic
resubmit নেই। Provider/subclass guard mutation-এর আগে; no live transport। New
dispatch tests সহ ledger/budget/provider 110 PASS; Ruff/docs checks PASS। Concurrent
same-key processes, crash-before-submit, accept-then-timeout ও fsync failure tested।
Schema/public reserve unchanged; existing edits retained। Success receipt এখনও
persist নয়; next authorized local/mock step minimal receipt/read-only outcome lookup।
Production gate/spend/runtime caps বাকি; no install/payment/cloud call/commit।

**Mock durable receipt/read-only lookup সম্পন্ন (2026-09-27):**
[Checkpoint](gpu-mock-receipt-checkpoint.md)। Successful guarded mock submit-এর
minimal receipt atomic/fsync writer দিয়ে persist। Lookup reservation absent/unknown/
submitted আলাদা করে; provider I/O ও write নেই। Optional v1 field backward-read
tested, legacy reservation unknown থাকে; replay কখনো resubmit নয়। Process-exit,
accept-then-timeout, receipt sync failure ও corrupt state tests সহ 119 PASS;
Ruff/docs checks PASS। Mock receipt historical acceptance মাত্র; current provider
state/completion নয়। Next same-phase authorized local step bounded offline acceptance
scenario/report। Existing edits retained; no install/paid action/commit।

**Budget→dispatch→receipt offline acceptance সম্পন্ন (2026-09-27):**
[Report](gpu-offline-acceptance.md)। Integrated two-shot scenario-তে over-budget
zero calls, accepted receipt, accept-then-timeout unknown, ledger reopen/new provider,
replay zero additional calls এবং explicit attempt cap PASS। Acceptance + receipt/
dispatch/ledger/budget/provider suite 120 PASS; Ruff/docs checks PASS। নতুন test ও
report/status মাত্র; production source/schema/UI অপরিবর্তিত। পূর্ণ Phase 4 বা real
execution acceptance নয়। Next local micro-step runtime-cap/mock lifecycle scope review;
completed slice restart নয়। No install/download/cloud call/payment/commit।

**Runtime-cap/mock lifecycle integration scope review সম্পন্ন (2026-09-27):**
[Scope](gpu-runtime-integration-scope.md)। Budget planned minutes cap এবং existing
MockSessionController elapsed deadline আলাদাভাবে আছে; guarded dispatch-এর সঙ্গে
wiring নেই। পরের same-phase authorized micro-step cooperative mock render session:
fixed budget-derived duration, pre/post submit tick, closed admission, existing
cleanup ও পৃথক storage result। Deterministic acceptance criteria নির্দিষ্ট;
watchdog restart/refactor বা live transport নয়। Source অপরিবর্তিত; docs checks PASS,
prior 120/126-test evidence retained। No install/download/payment/cloud call/commit।

**Cooperative mock render session সম্পন্ন (2026-09-27):**
[Checkpoint](gpu-mock-session-checkpoint.md)। নতুন wrapper fixed budget-derived
deadline, pre/post dispatch tick, closed admission ও existing lifecycle cleanup
যুক্ত করে। Exact mock components only; timeout/persistence failure original error
propagate, replay/cap rejection blanket cleanup নয়। Relevant suite 157 PASS;
Ruff/docs checks PASS। Caller-driven single-process সীমা; restart session deadline
এখনও durable নয়। Next local scope review deadline/closed-state persistence;
existing watchdog restart নয়। Production DB/UI/API অপরিবর্তিত, existing edits
retained; no install/download/cloud call/payment/commit।

**Mock session restart scope review সম্পন্ন (2026-09-27):**
[Scope](gpu-session-restart-scope.md)। Existing session-এর constructor deadline reset
gap ও cleanup journal-এর restart-always-cleanup semantics যাচাই। পরের bounded
implementation durable admission identity/owner lease/closed intent; restart-এ
submit disabled এবং original deadline retained। Automatic cross-boot clock resume
নয়। Legacy used render auto-enrol নয়; receipts backward read, identity/conflict/
process exit/write failure checks নির্দিষ্ট। Source অপরিবর্তিত; docs checks PASS;
157/126-test evidence retained। Same-phase local authorization বহাল; no paid action।

**Durable mock session admission সম্পন্ন (2026-09-27):**
[Checkpoint](gpu-durable-session-checkpoint.md)। Optional ledger session record-এ
identity/original deadline/closed intent/cleanup cap; explicit create/recover,
ledger-wide lifetime owner lease এবং cooperative session cleanup hook। Restart-এ
admission বন্ধ, deadline অক্ষত; existing used render create reject। Legacy read
compatible; receipts retained। 170 relevant tests PASS; Ruff/docs checks PASS।
Spawned abrupt exit, changed clock, duplicate owner, sync/intent failure, bounded
cleanup tested। Production DB/API/UI untouched; existing edits retained। Next
authorized local micro-step durable restart integrated acceptance/report। No
install/download/cloud call/payment/commit; real acceptance deferred।

**Durable restart integrated offline acceptance সম্পন্ন (2026-09-27):**
[Report](gpu-durable-offline-acceptance.md)। Spawned owner-এর প্রথম accepted receipt,
দ্বিতীয় accept-before-exit unknown, active owner rejection ও recovery এক scenario-তে
verified। Recovered deadline অপরিবর্তিত, old/new submit blocked, receipt lookup
unchanged; unknown storage complete false। Relevant suite 171 PASS; Ruff/docs checks
PASS। Source unchanged; new test/report/status only। Next local scope review durable
cleanup observation retention/recovery reuse; live state দাবি নয়। Real Phase 4
acceptance deferred; no install/download/cloud call/payment/commit।

**Cleanup outcome scope review সম্পন্ন (2026-09-27):**
[Scope](gpu-cleanup-outcome-scope.md)। Durable session result memory-only gap
verified। Next typed per-attempt observation persistence/historical reuse;
absent/auth-terminal-এ repeated cleanup নয়, stale outcome invalidation ও legacy
backward-read criteria নির্দিষ্ট। Same-phase local authorization বহাল। Source
unchanged; docs checks PASS; prior 171-test evidence retained; no paid action।

**Durable cleanup observation সম্পন্ন (2026-09-27):**
[Checkpoint](gpu-cleanup-observation-checkpoint.md)। Typed per-attempt observation
persist; next intent clears stale data। Absent/auth terminal ও cap saved outcome
reuse; source current_call/saved/unknown আলাদা, live_state_verified false। Legacy
optional field backward-read; malformed associations reject। Result-write/fsync ও
spawned crash tests সহ 183 relevant tests PASS; Ruff/docs checks PASS। Production
DB/API/UI untouched; no install/paid action। Next local step read-only session/
cleanup report scope review; completed acceptance পুনরায় নয়।

**Read-only session/cleanup report scope review সম্পন্ন (2026-09-27):**
[Scope](gpu-session-report-scope.md)। `recover()` cleanup চালাতে পারে এবং existing
lookup শুধু reservation পড়ে—এই gap verified। পরের authorized local micro-step:
typed atomic snapshot reader, no owner/mutation lock creation, saved/unknown
observation ও live_state_verified false। Missing/corrupt file fail-closed; absent
session None, saved deadline audit-only। Source/schema অপরিবর্তিত; docs consistency,
links, whitespace ও plan drift PASS; prior 183-test evidence retained। Blocker নেই;
no install/download/cloud call/payment/commit; real acceptance deferred।

**Read-only session/cleanup report সম্পন্ন (2026-09-27):**
[Checkpoint](gpu-session-report-checkpoint.md)। `session_report(render_id=...)`
single validated snapshot থেকে immutable typed historical report দেয়; no locks,
writes, recovery বা cleanup। Missing/legacy session None; corrupt/missing ledger
error; saved/unknown source ও live_state_verified false। Atomic replacement after
open সহ নতুন tests ও relevant regression: 201 PASS; Ruff/docs checks PASS। Direct
pytest launcher stale shebang bypass করতে existing interpreter ব্যবহার; install নয়।
Source ledger, নতুন test/checkpoint ও status docs ছাড়া পরিবর্তন নেই; persisted
schema/production API/UI/DB অপরিবর্তিত। Next authorized local micro-step remaining
mock gap review; completed work restart নয়। Blocker নেই; real acceptance deferred।

**Remaining local/mock gap review সম্পন্ন (2026-09-27):**
[Review](gpu-mock-remaining-gap-review.md)। Completed reservation/dispatch/session/
observation/report slices retained। Concrete double-failure gap reproduced: provider
 timeout-এর পরে cleanup intent write failure হলে top-level OSError, original
GPUProviderError শুধু context-এ; admission closed থাকে। Next authorized bounded fix:
original dispatch error identity/code propagate, cleanup error explicit chaining;
intent/result/dispatch persistence failure tests। Source/test unchanged; local
fixture reproduction ও docs checks PASS; prior 201-test evidence retained। Blocker
নেই; production/live/model work deferred; no install/download/cloud call/commit।

**Dispatch/cleanup double-failure fix সম্পন্ন (2026-09-27):**
[Checkpoint](gpu-double-failure-checkpoint.md)। `MockRenderSession.submit()` original
exception instance/code top-level রাখে; cleanup exception explicit cause-এ। ছয়টি
নতুন test আগে FAIL, পরে PASS; relevant regression 207 PASS; lint correction-এর পরে
ছয়টি targeted test আবার PASS। Ruff/docs checks PASS। Closed admission/no retry ও
unknown observation verified; standalone cleanup/schema অপরিবর্তিত। Next authorized
local micro-step completed mock evidence handoff/deferred gates সংক্ষেপে একত্র করা।
Blocker নেই; no install/download/cloud call/payment/commit; real acceptance deferred।

**Local/mock evidence handoff সম্পন্ন (2026-09-27):**
[Handoff](gpu-mock-handoff.md)-এ completed slices, latest 207-test evidence,
separate supervisor evidence, limitations ও deferred gates একত্র। Counts overlap
করে যোগ নয়; source/test unchanged, regression rerun নয়। Links/status/authorization,
plan drift/whitespace/RESUME checks PASS। এই bounded local ধারায় আর নির্দিষ্ট
pending implementation তালিকাভুক্ত নেই; review/feature loop নিজে থেকে নয়। Next
plan-order step 4.7 final preview owner-deferred; নতুন local scope বা explicit
restart নির্দেশে পরের কাজ নির্ধারণ। Existing local authorization বহাল; নতুন phase,
paid/model কাজ auto-start নয়। Handoff blocker নেই; real Phase 3/4 অসম্পূর্ণ।
No install/download/cloud call/payment/commit; existing owner edits retained।

**4.7 non-billable preview পুনরারম্ভ (2026-09-27):** Owner-এর repeated next-work
নির্দেশে preview path resumed; paid launch/payment authorization নয়।
[Draft](runpod-launch-preview.md)-এ official public A5000 24 GB $0.27/hr ও Pod
pricing পুনরায় যাচাই; provisional 15-minute compute $0.0675। Account quote/region/
tier/storage/tax অজানা; final approval-ready preview এখনও অসম্পূর্ণ। Existing
image/mock evidence reuse; পুরোনো next-supervisor step completed হিসেবে স্পষ্ট।
Next required input owner console quote; authenticated console access agent-এর নেই।
Docs checks PASS; app tests rerun/install/download/account mutation/payment হয়নি।

**RunPod স্থগিত ও বাংলা local report command সম্পন্ন (2026-09-27):**
Owner RunPod ছাড়া কাজের নির্দেশে quote/screenshot/payment handoff পুনরায় স্থগিত;
ওই তথ্য আর pending requirement নয়। [Command checkpoint](gpu-local-report-command.md)।
Existing session_report-এর read-only CLI বাংলায় historical compute/storage/admission
ও unknown অবস্থার বার্তা দেয়; exit 0 read-success, 1 no session, 2 error। Raw corrupt
input echo নয়। CLI/report/durable/observation 56 tests PASS; lint correction-এর পরে
7 CLI tests PASS; Ruff/docs checks PASS। Existing source/schema/production flow
অক্ষত; new script/test/docs only। Next authorized local micro-step temporary
synthetic session-এর reproducible offline demo। No install/cloud/payment/commit।

**Reproducible offline mock demo সম্পন্ন (2026-09-27):**
[ব্যবহারবিধি](gpu-offline-demo.md)। নতুন module command temporary synthetic ledger/
mock session বানিয়ে existing বাংলা report দেখায়; unknown → submitted → saved absent/
retained state। Zero fixture rate/fixed clock; real inference নয়। No existing path
input; own temporary files removed। Network-disabled/repeated run/user-file retention/
failure cleanup ও subprocess tests সহ relevant 59 PASS; direct demo exit 0;
Ruff/docs checks PASS। Source provider/API/UI/DB অপরিবর্তিত; নতুন script/test/docs।
Blocker নেই। এই demo slice complete; next owner demo/feedback বা concrete local
scope, নতুন feature/phase auto-start নয়। RunPod স্থগিত; no install/download/commit।

**Owner demo handoff ও next-plan check (2026-09-28):** Owner-এর পাঠানো output
expected unknown → queued → compute absent/storage retained/admission closed,
attempt 1/incomplete ও temporary cleanup দেখায়; reported error নেই। এটি owner
output review, নতুন test run বা real GPU evidence নয়। Rules, Phase 4/5, readiness
review ও latest ledger মিলিয়ে next plan-order step 4.7 final cost/action preview;
RunPod suspension বহাল বলে এগোনো স্থগিত। 4.8–4.10 real health/inference/cleanup
ও পূর্ণ acceptance বাকি; Phase 3 real gate-ও deferred। GPU ছাড়া prospective next
কাজ: explicit scoped phase-order revision-এর পরে 5.1 existing model local
path/size/identity/license/format inventory (missing হলে missing report), download
বা model run নয়। এই review ওই revision বা Phase 5 implementation অনুমোদন নয়।
RESUME/ledger only; requirements/source অপরিবর্তিত। Plan drift ও whitespace
checks PASS; application tests প্রয়োজন হয়নি।

**5.1 scoped local inventory সম্পন্ন (2026-09-28):** Owner recommendation অনুমোদন
দেওয়ায় master-এ শুধু 5.1 phase-order exception যোগ; generated excerpts refreshed।
[Inventory](phase-5-model-inventory.md): SDXL-Turbo revision snapshot উপস্থিত,
13,878,864,870 bytes; চার F32 safetensors-এর full hash/cache manifest/header/offset
checks PASS। Official revision card/license reviewed; কিছু media path inaccessible।
Real runtime/quality নয়; model load/install/download বা paid action হয়নি।
Next 5.2 mock ImageProvider contract, scoped exception extension প্রয়োজন; 3/4
real acceptance deferred। Docs drift/whitespace PASS; app tests প্রযোজ্য নয়।

**5.2 ImageProvider mock contract সম্পন্ন (2026-09-28):** Owner next-work নির্দেশে
master scoped exception 5.2 পর্যন্ত extended; [checkpoint](image-provider-checkpoint.md)।
New image.py: strict request/result, Protocol, image-only read-only fixture mock,
verified PNG/dimensions/hash, model/seed/mock metadata ও cancellation/error boundary।
Baseline FakeProvider 29 PASS; new 22 + regression 29 = 51 PASS; Ruff/format/plan
drift/whitespace PASS। API/UI/DB/পুরোনো providers অপরিবর্তিত; no install/download/
model run/cloud/commit। Next 5.3 workflow validation, scoped extension প্রয়োজন।

**5.3 ComfyUI offline workflow সম্পন্ন (2026-09-28):** Owner next-work নির্দেশে
scoped exception 5.3 পর্যন্ত। [Checkpoint](comfy-workflow-checkpoint.md)। Seven-node
API JSON, ImageRequest builder ও strict fixed-profile validator; SDXL-Turbo
Diffusers mapping, 512×512/batch1/step1, prompt/seed retained। Official node/API
source reviewed; DiffusersLoader deprecated, live compatibility unverified।
29 workflow + 22 image tests = 51 PASS; Ruff/format/drift/whitespace/links PASS।
No server validation/inference/install/download/cloud/API/UI/DB change। Next 5.4
real image requires runtime/model registration preflight ও execution authorization;
Phase 3/4 gates deferred, RunPod স্থগিত।

**5.4 local runtime preflight সম্পন্ন, image acceptance BLOCKED (2026-09-28):**
Owner next-work নির্দেশে existing-local-resource 5.4 scope অনুমোদিত; পুনরায় generic
execution approval নয়। [Preflight](phase-5-image-preflight.md): installed torch/
diffusers import ও pip check PASS; CUDA unavailable, ComfyUI searched roots-এ
মেলেনি; listener query permission denied। RAM ~10 GiB available বনাম existing
F32 snapshot ~12.93 GiB; safe bounded load route প্রতিষ্ঠিত নয়। Legacy app path
read only; online-capable/1024px/unseeded call চালানো হয়নি। Next resolve usable
runtime/hardware route within existing scope; install owner-only, no paid/new
download authorization। Master/excerpts/RESUME updated; docs checks PASS।
Model run/install/download/cloud call হয়নি; 5.4 incomplete, 5.5 শুরু নয়।

**5.4 reduced-precision CPU feasibility সম্পন্ন (2026-09-28):**
[Evidence](phase-5-cpu-feasibility.md)। Existing torch synthetic FP32/FP16/BF16
conv/norm/attention/interpolation finite outputs PASS under 45s/CPU/AS limits;
peak RSS ~499 MiB, model run নয়। Header-based FP16 encoder/UNet + F32 VAE weight
estimate 6.617 GiB; transient/runtime memory অমাপা। Installed loader dtype path
verified; accelerator CPU-offload method এই CPU-only route নয়। Correct process
cgroup found, shared memory.max=max and not writable; isolated hard RSS cap নেই।
Next authorized 5.4 micro-step: bounded offline load-only harness and synthetic
guard tests, then load readiness; real image acceptance still incomplete।
Docs-only updates, no model load/install/download/cloud; docs checks PASS।

**5.4 bounded load-only harness সম্পন্ন (2026-09-28):**
[Checkpoint](image-load-harness-checkpoint.md)। New isolated script: 300s wall/CPU,
24 GiB hard virtual address cap, sampled 8 GiB child RSS/2 GiB host reserve,
kill/reap, offline Python socket guard/local-files-only, exact snapshot, FP16
encoders/UNet + F32 VAE, stage/result evidence, no inference/retry। Synthetic ও
stubbed-runtime tests 16 + image/workflow 51 = 67 PASS; Ruff/docs checks PASS।
Actual model load হয়নি; AS/import/load feasibility still unmeasured; RSS guard
not hard allocation ceiling। Next authorized micro-step one bounded actual
load-only attempt after fresh memory/runtime-license preflight; 5.4 incomplete।
No install/download/cloud/commit, existing unrelated work retained।

**5.4 actual load-only attempt 1 FAIL (2026-09-28):**
[Result/preflight](image-load-attempt-1.md)। Fresh memory/disk ও runtime/license
checks-এর পরে একবার exact existing local snapshot load। 18.7836s-এ sampled RSS
8,602,546,176 bytes (~8.012 GiB) > 8 GiB guard; stage loading_pipeline; child -9
killed/reaped, subsequent /proc absent, CLI exit 1। No inference/output, retry বা
limit increase। Weight estimate excludes transient loading overhead; allocation
root cause not yet measured। Next authorized step inspect/test load-memory
reduction under same limits before another real run। Source unchanged, prior
67 tests retained; docs checks PASS। No install/download/paid action/commit।

**5.4 tensor-at-a-time loader change সম্পন্ন (2026-09-28):**
[Checkpoint](image-stream-load-checkpoint.md)। Existing unsharded loader retains
F32 source state_dict during conversion; overlap candidate, attempt-1 exact
allocation attribution unproven। New image_stream_load helper validates meta
model keys/shapes/F32, loads/copies/releases each tensor, supplies four components
to probe pipeline। Same offline/resource limits; no checkpoint rewrite/download।
10 new helper + 16 probe + 51 image/workflow = 77 PASS, including small real
UNet/VAE/CLIP config/weight roundtrip; Ruff/docs checks PASS। No full SDXL load
this turn; next authorized fresh memory check + one attempt-2 under same bounds।
Prior attempt-1 failure retained; 5.4 real image incomplete; no API/UI/DB/install。


**5.4 streaming load-only attempt 2 FAIL (2026-09-29):**
[Result/preflight](image-load-attempt-2.md)। Fresh available RAM ~11.34 GiB;
one run under unchanged bounds, attempt-1 preserved। 15.8094s, sampled peak
RSS 1,146,662,912 bytes (~1.068 GiB), child/CLI exit 1, child_failed/RuntimeError।
Supervisor waited/reaped। Previous operation/message/traceback not retained by
harness, root cause unknown। No reported memory guard breach; no full-load
success/image, retry or limit increase। Prior 77 tests reused, source unchanged;
docs checks PASS। Next proposed owner-directed step: diagnostic retention and
synthetic tests only; another real load not automatically authorized। No install,
download, paid resource, commit or API/UI/DB changes।


**5.4 bounded load diagnostics সম্পন্ন (2026-09-29):**
[Checkpoint](image-load-diagnostics-checkpoint.md)। Last operation/error message/
last 12 traceback frames retained with text bounds; no locals/source capture।
TypeError failure covered, snapshot/runtime/validation stages explicit।
80 relevant tests PASS; final handler-scope recheck 18 PASS/1 FAIL: synthetic-error
returned monitor_error:ValueError; unchanged rerun 19 PASS। Intermittent RSS/status
observation issue suspected, unresolved; no test skipped।
Ruff/docs checks PASS। No SDXL run, install/download/resource-limit change।
Attempt-2 root cause still unknown; diagnostic evidence cannot recover old errors।
Next proposed owner-directed step: synthetic monitor diagnosis/fix; attempt-3 deferred;
no automatic retry/inference; real 5.4 acceptance remains incomplete।


**5.4 RSS monitor exit race fix সম্পন্ন (2026-09-29):**
[Checkpoint](image-monitor-exit-checkpoint.md)। Synthetic child exit-এ R state
ও missing VmRSS captured; original failure snapshot unavailable। Missing RSS
এখন <=50ms/remaining-deadline bounded wait দিয়ে exit confirm করে; still-live
child monitor failure + kill/reap, completed child ordinary result classification।
Regression reproduced before fix; 84 relevant tests PASS, 30 synthetic real
subprocess success/failure exits ও cleanup PASS; Ruff/docs checks PASS।
Attempt-2 RuntimeError এখনও অজানা; no SDXL load/install/download/limit increase।
Next proposed owner-directed micro-step: fresh memory preflight + one diagnostic
attempt-3 under same limits, no automatic retry; 5.4 image acceptance incomplete।


**5.4 diagnostic load-only attempt 3 FAIL (2026-09-29):**
[Result/preflight](image-load-attempt-3.md)। Fresh RAM ~11.18 GiB, unchanged
limits, one run only। 7.7068s, sampled RSS 1,116,200,960 bytes (~1.040 GiB),
child/CLI exit 1; loading_unet RuntimeError: unable to mmap 10270077736 bytes,
Cannot allocate memory (12), header-validation safe_open line 44। No reported
RSS/host reserve/timeout guard breach; supervisor completed wait/reap।
Virtual-address pressure is a candidate, exact mappings/usage unmeasured;
not proof of physical RAM exhaustion। Diagnostics worked; no monitor error।
Prior 84 tests/30 synthetic checks reused; docs checks PASS। No retry/inference,
install/download/limit increase/paid resource/commit। Next proposed owner-directed
step: installed mapping-path inspection + bounded synthetic address-space
measurement, evidence-led adjustment/tests under same limits; 5.4 incomplete।


**5.4 pread mapping-pressure adjustment সম্পন্ন (2026-09-29):**
[Checkpoint](image-pread-checkpoint.md)। Installed safetensors supports pread;
64 MiB fixture retained mappings mmap=1/pread=0। +32 MiB virtual headroom-এ
দুটোই fail; +96 MiB-এ mmap fail/pread shape+small value PASS। Thus pread still
needs transient opening space but reduces measured pressure। Loader validation
ও per-tensor read now pread; unchanged copy/dtype/schema/offline/resource bounds।
85 relevant tests PASS, including actual mapping regression and small component
roundtrip; Ruff/docs checks PASS। No full model run/install/download/commit।
Next proposed owner-directed step: fresh memory check + one bounded attempt-4,
no auto retry; full-model load/image acceptance remains unmeasured/incomplete।


**5.4 pread load-only attempt 4 FAIL (2026-09-29):**
[Result/preflight](image-load-attempt-4.md)। Fresh available RAM ~11.16 GiB,
one run under unchanged limits। VAE/UNet load returned; loading_text_encoder
ValueError: Checkpoint/model keys differ (image_stream_load.py:36)। 53.0912s,
sampled RSS 6,447,804,416 bytes (~6.005 GiB), child/CLI exit 1, supervisor reaped।
No reported memory/timeout/monitor breach। Earlier UNet mapping blocker passed
in this run; full pipeline/inference still unproven, no image/retry। Prior 85 tests
reused; docs checks PASS। No install/download/limit increase/paid resource/commit।
Next proposed owner-directed step: encoder checkpoint header/meta-model schema
comparison and evidence-led compatibility correction/tests; no full-model run
or silent key dropping। Phase 5.4 real image acceptance remains incomplete।


**5.4 legacy CLIP key compatibility সম্পন্ন (2026-09-29):**
[Checkpoint](image-clip-keys-checkpoint.md)। Local header/meta-model comparison:
first encoder 196 keys exact match after text_model prefix removal, second 517
native matches; all shapes/F32 match। Installed Transformers conversion mapping
confirms CLIPTextModel migration। Loader permits only complete bijective legacy
prefix correspondence for exact CLIPTextModel, retaining full shape/dtype checks
and rejection of missing/extra/mixed keys; no checkpoint rewriting।
93 relevant tests PASS including 8 new compatibility/forward/rejection cases;
Ruff/docs checks PASS। No full-model load/install/download/limit change/commit।
Next proposed owner-directed step: fresh memory check + one bounded attempt-5;
no auto retry/inference; Phase 5.4 real image acceptance incomplete।


**5.4 full pipeline load attempt 5 PASS (2026-09-29):**
[Result/preflight](image-load-attempt-5.md)। Fresh RAM ~11.19 GiB; one load-only
run under unchanged bounds। Final loaded, reason null, child/CLI exit 0;
64.6570s, sampled peak RSS 8,104,144,896 bytes (~7.547 GiB), child peak
7,913,636 KiB। CPU checks passed, UNet/both encoders FP16, VAE F32; supervisor
wait/reap complete। Load feasibility proven for this run; no inference/image,
activation memory unmeasured, sampled peak margin ~0.453 GiB। Prior 93 tests
reused; docs checks PASS। No retry/install/download/paid resource/commit।
Next proposed owner-directed step: bounded single-image inference harness with
metadata/finite output/PNG validation and synthetic tests only; actual inference
needs subsequent readiness/run। 5.4 image acceptance incomplete; 5.5 not started।


**5.4 bounded inference harness সম্পন্ন (2026-09-29):**
[Checkpoint](image-inference-harness-checkpoint.md)। Explicit --infer in existing
guarded probe; same total time/memory/offline limits, no retry। Fixed 512x512,
one step/guidance 0/seed 42 anime prompt; finite latent + F32 VAE raw decode checks,
normalized RGB PNG verification/checksum/metadata; parent independently validates
artifact before success। 104 relevant tests PASS, Ruff/docs checks PASS।
Initial incomplete parent test stub corrected; no test skips। No real model run,
image inference/install/download/paid resource/API/UI changes। Load headroom only
~0.453 GiB; inference feasibility unknown। Next proposed owner-directed step:
fresh readiness + one bounded --infer attempt-1, verify and visually review if
successful; no retry/limit increase। Phase 5.4 acceptance remains incomplete।

**5.4 existing inference attempt-1 reconciliation (2026-09-30):**
[Evidence](image-inference-attempt-1.md)। Fresh readiness found attempt-1 already
exists, so no model run/retry occurred. Saved result reports timeout at denoising,
300.8881s, sampled peak 8,114,016,256 bytes (~7.557 GiB), returncode -9; stage agrees.
No PNG/metadata exists. Prior execution not observed this turn; root cause beyond
reported timeout unknown. RAM 12,318,494,720 bytes available; expected weights
present; ignored evidence preserved. Source unchanged; prior 104 tests reused.
Next proposed step: read-only timeout diagnosis, no retry/limit increase.
Phase 5.4 real image acceptance incomplete; 5.5 not started.

**5.4 read-only inference timeout diagnosis (2026-09-30):**
[Findings/proposal](image-inference-timeout-diagnosis.md)। `denoising` wraps the
whole pipeline call, including text encoding; UNet entry is not established.
300s budget includes imports/load/inference; prior load-only timing cannot be
used as this run's timing. Atomic last-stage record has no event history/CPU
timings. Root bottleneck unresolved; no dtype/thread/budget change justified.
Next proposed micro-step: bounded timing log and temporary component hooks,
synthetic/stub tests only, preserving all inference settings/guards. No real
run/retry/source edit/install occurred. Prior 104 tests reused; docs checks PASS.
5.4 real image acceptance remains incomplete; 5.5 not started.

**5.4 bounded inference timing সম্পন্ন (2026-09-30):**
[Checkpoint](image-inference-timing-checkpoint.md)। Additive elapsed/process CPU
timing in stage.json; exclusive payload-free events.jsonl capped at 128 entries.
Temporary encoder/UNet hooks and explicit pipeline/latent/decode markers, with
cleanup on exceptions/partial registration; no tensor replacements. Existing
settings/limits/offline/artifact checks unchanged. 109 relevant tests PASS;
Ruff/docs checks PASS. No real load/inference/install/download/commit.
Next proposed owner-directed step: fresh readiness + one instrumented attempt-2
under unchanged bounds, no automatic retry. 5.4 real acceptance incomplete.


**5.4 instrumented inference attempt-2 FAIL (2026-09-30):**
[Evidence](image-inference-attempt-2.md)। One authorized run; timeout 300.5893s,
child -9/CLI 1, sampled RSS ~7.5565 GiB. Load and both encoders completed;
UNet entered 75.7511s without return. 17 events agree with final evidence;
no PNG/metadata. No retry/limit change. Prior 109 tests reused; docs checks PASS.
Next proposed: read-only UNet CPU-path/hardware review. 5.4 incomplete; 5.5 not started.


**5.4 read-only UNet CPU review (2026-09-30):**
[Review/proposal](image-unet-cpu-review.md)। i7-4790S, 4 cores/8 threads, AVX2;
PyTorch reports no AVX512 FP16/BF16 or AMX FP16/BF16, MKLDNN enabled. Local
UNet config/source reviewed; exact executed kernel and slow operator unknown.
Full F32 UNet payload alone exceeds 8 GiB guard; no speculative dtype switch.
Next proposed: bounded synthetic representative conv/linear dtype benchmark,
with tested guards, no checkpoint/full model load. No inference/source change;
prior 109 tests reused, docs checks PASS. 5.4 incomplete; 5.5 not started.


**5.4 guarded operator probe (2026-09-30):**
[Checkpoint](image-operator-probe-checkpoint.md)। Harness added using existing guards;
114 tests PASS, Ruff/docs checks PASS. Actual suite stopped after F32 conv PASS
(warm ~0.047s) and FP16 first-call SIGXCPU (-24); no BF16/linear or retry.
Some regression tests overlapped FP16 case: no uncontended speed ratio claim.
No model load/image/install. Next proposed: isolated bounded synthetic
FP16-storage/F32-conv wrapper comparison/tests; full UNet fit unproven.
5.4 remains incomplete; 5.5 not started.


**5.4 synthetic mixed convolution PASS (2026-09-30):**
[Checkpoint](image-mixed-conv-checkpoint.md)। Added --mixed two-case guarded suite;
116 tests PASS before actual isolated run. F32/mixed both PASS (~0.054/~0.053s
warm), mixed relative L2 0.000359475; conversion included. Process memory and
explicit conversion payload recorded with limits on attribution. No full UNet
fit/latency/quality claim. Next proposed: opt-in Conv2d adapter/tests and local
shape inventory; no full model run. Ruff/docs checks PASS; 5.4 incomplete.


**5.4 opt-in mixed Conv2d adapter সম্পন্ন (2026-09-30):**
[Checkpoint](image-mixed-adapter-checkpoint.md)। Temporary CPU F32 conv compute
with unchanged FP16 storage; semantic/cleanup/rejection tests and explicit
--infer-mixed harness/metadata wiring. 128 relevant cases PASS over completed
runs; Ruff/docs checks PASS. Header-only inventory: 51 conv weights; largest
F32 weight+bias ~112.505 MiB, full-model fit unproven. No real model run.
Next proposed: fresh readiness + one bounded mixed attempt-3, no retries/limit
increase. Phase 5.4 incomplete; 5.5 not started.


**5.4 mixed inference attempt-3 FAIL at decode RSS guard (2026-09-30):**
[Evidence](image-inference-attempt-3.md)। One authorized run under unchanged
limits. UNet completes ~102.87s, finite latents PASS; decode starts ~176.27s.
RSS guard stops run at 188.64s, sampled peak 8,591,810,560 bytes; child -9/CLI 1.
No PNG/metadata. 21 events consistent; prior 128 tests reused, docs checks PASS.
No retry/limit increase. Next proposed: decode object-lifetime/options review
and one synthetic-tested memory reduction; no full run. 5.4 incomplete.


**5.4 release denoisers before decode সম্পন্ন (2026-09-30):**
[Checkpoint](image-decode-release-checkpoint.md)। Loader/validation aliases dropped;
timing/mixed contexts close before clearing pipeline UNet/encoders and collecting
cycles. Single-use pipeline; VAE math/settings unchanged. 131 tests PASS including
weakref collection before decode and failure handling; Ruff/docs checks PASS.
No full run; real RSS reduction unmeasured. Next proposed: fresh readiness plus
one bounded mixed attempt-4, same limits/no retry. 5.4 incomplete; 5.5 not started.


**5.4 mixed inference attempt-4 FAIL at decode RSS guard (2026-09-30):**
[Evidence](image-inference-attempt-4.md)। Fresh readiness PASS; one authorized
run with unchanged limits. UNet ~104.05s, finite latents and denoisers_released
event PASS; decode still crosses RSS guard at 210.043s. Sampled peak
8,592,891,904 bytes; child -9/CLI 1. All 22 events agree, no PNG/metadata.
Release-path execution is not proof of real object collection/OS memory return;
no per-stage RSS attribution. Prior 131 tests reused; docs checks PASS.
No source edit, retry, install/download, paid resource or commit. Next proposed:
read-only decode memory diagnosis before another change/run. 5.4 incomplete;
5.5 not started, awaiting owner direction.


**5.4 read-only decode memory review সম্পন্ন (2026-09-30):**
[Review](image-decode-memory-review.md)। No new obvious permanent denoiser
owner found in reviewed paths; runtime collection/storage release unproven.
Batch-1 slicing inactive; default tile threshold 128 exceeds 64x64 latents,
so enabling tiling alone is ineffective. Third upsample F32 tensor payload
256 MiB, not total peak attribution. Existing event JSONL drops extra values;
next proposed: bounded persistent RSS/weakref/VAE-stage diagnostics with
synthetic tests only. No source change/full run/retry/install. Docs checks PASS;
prior 131 tests reused. 5.4 incomplete; next step awaits owner direction.

**5.4 VAE memory diagnostics সম্পন্ন (2026-10-01):**
[পূর্ণ ফল](image-decode-diagnostics.md)। Owner-এর diagnostics-only নির্দেশে scalar
RSS/HWM/anonymous/file-backed JSONL, denoiser root/parameter/buffer weakrefs ও
VAE leaf hooks যোগ। Isolated existing F32 VAE/zero latents PASS: before
1.0055 GiB, sampled peak 1.9641 GiB, after 1.0267 GiB; সবচেয়ে বড় HWM jump
তৃতীয় upsampler convolution-এ (~511 MiB)। VAE payload 319.11 MiB।
Fresh readiness-এর পরে এক full mixed run: ~6.31 GiB denoiser tracked tensors
ও roots dead, কিন্তু RSS 7.5642→7.2246 GiB; anonymous 6.9269 GiB থাকে।
সম্ভাব্য allocator/native retention + decoder workspace pressure; exact native
allocation ownership অপ্রমাণিত। Full decode mid-block-এ SIGXCPU (-24), CPU
~300s; supervisor reason monitor_error:ValueError (existing exit race)।
Full after-decode/peak জানা যায়নি; isolated result দিয়ে প্রতিস্থাপন করা হয়নি।
138 relevant tests PASS; Ruff lint/format, excerpt drift ও whitespace PASS।
কোনো limit/algorithm change, major fix, retry, download/install/paid কাজ নয়।
Phase 5.4 incomplete; next proposed retained-native-memory/isolated real-latent
investigation; 5.5 বা major fix শুরু নয়। Existing unrelated edits preserved।

**5.4 owner-requested diagnostic retry সম্পন্ন (2026-10-01):**
“ok try again” নির্দেশে same-code/limits attempt-6; readiness PASS। UNet দ্রুত
শেষ হলেও decode CPU budget-এ SIGXCPU (-24), 217.36s; third up-block-এর
resnets.2.conv2 সর্বশেষ event। Pre-decode RSS 7.2248 GiB, recorded decode
boundary maximum 7.6003 GiB; after-decode unavailable। Denoiser roots ও tracked
tensors আবার dead, VAE 319.11 MiB; native/allocator retention hypothesis বহাল।
[মাপ/সীমা](image-decode-diagnostics.md)। No further retry/fix; unchanged-code
138-test evidence reused। Next: পৃথক real-latent decode/native memory diagnosis,
owner নির্দেশ প্রয়োজন; Phase 5.4 অসম্পূর্ণ।

**5.4 one split-process experiment সম্পন্ন; real outcome incomplete (2026-10-01):**
[পূর্ণ checkpoint](image-split-process-experiment.md)। Owner একটি experiment-এর
নির্দেশ দিয়েছেন। Temporary latent-only save + separate VAE decode harness,
checksum/provenance ও parent/combined RAM sampling যোগ; production architecture
অপরিবর্তিত। Generation successful exit/reap ছাড়া decoder শুরু হয় না।
146 distinct relevant tests PASS (145-suite + 1 নতুন branch test); Ruff PASS।
এক real run: initial readiness PASS, generation UNet-এ available host RAM 2 GiB
reserve-এর নিচে নামায় `host_memory`, child -9/reaped, 129.275s। Generation peak
7.6732 GiB, supervisor 18.46 MiB, combined 7.6912 GiB; 8 GiB guard ভাঙেনি।
Real latent/image নেই, decode subprocess শুরু হয়নি; decode RAM/সফলতা অজানা।
এক-experiment scope মেনে retry/guard reduction/install/download/major fix নয়।
Next: বেশি available host RAM-এ owner-directed নতুন attempt; 5.4 incomplete।

**5.4 CUDA source preparation সম্পন্ন (2026-10-01):**
[পরিবর্তন/হ্যান্ডঅফ](image-cuda-preparation.md)। Auto CUDA selection ও device-only
pipeline/VAE transfer; seeded generator/latent device matching; F32 VAE বহাল;
CPU-only mixed convolution CUDA-তে bypass; CPU fallback বজায়। Split experiment-এর
real decode-ও device-aware; device metadata/JSONL এবং local snapshot env override।
Existing 8 GiB RSS/2 GiB reserve/24 GiB AS/300s/offline/cleanup guards অক্ষত।
152 distinct lightweight tests PASS (151 regression + expanded 12-case subset,
একটি নতুন parameter case); Ruff/format/plan drift/whitespace PASS। No heavy model
load/generation, actual CUDA allocation, install/download/deploy/paid GPU।
Source প্রস্তুত; first RunPod launch unconditional ready নয়: CUDA runtime/model
preflight এবং unchanged RLIMIT_AS compatibility verification বাকি; paid approval
নেই। GPU VRAM cap/peak measurement যোগ হয়নি। Phase 5.4 acceptance incomplete।

**5.4 RunPod preflight review সম্পন্ন (2026-10-01): NOT READY।**
[সম্পূর্ণ findings/sources](image-runpod-preflight-review.md)। Source/guards অপরিবর্তিত;
কোনো heavy load/generation/deploy/install/cloud call নয়। Local torch 2.14.0+cu130,
diffusers 0.40.0 ও pipeline imports/pip check PASS; CUDA unavailable। Model headers,
sizes/configs/tokenizers PASS; weight symlinks remote copy-তে targets লাগবে।
Blockers: unconditional pre-import 24 GiB RLIMIT_AS-এর GPU compatibility অপ্রমাণিত;
selected CUDA image/dependency lock/driver match (cu130 হলে normal driver 580+);
paid-test CUDA-required allocation gate ও actual Pod memory/VRAM preflight;
remote full F32 snapshot provisioning/verification। NVIDIA old 40-bit reservation
example আধুনিক GPU-তে নিশ্চিত failure-এর প্রমাণ হিসেবে ব্যবহার করা হয়নি।
152 existing lightweight tests reused; source unchanged। Docs/drift/whitespace
checks PASS। Next owner-directed blocker resolution; Phase 5.4 incomplete।

**5.4 CUDA-specific AS policy সম্পন্ন (2026-10-02):**
[পূর্ণ checkpoint](image-cuda-address-policy.md)। Explicit `--address-policy cuda`
application RLIMIT_AS cap বসায় না; inherited finite soft/hard limit হলে fail,
বাইরের limit বাড়ায় না। Guarded child-এ model load-এর আগে CUDA required latch;
GPU unavailable হলে CPU fallback নয়। Default cpu policy আগের 24 GiB soft/hard
cap imports-এর আগে বসায়। CPU-only modes-এ CUDA-policy bypass rejected।
Supervisor/CLI→child এবং split experiment-এর দুই child-এ policy forward/persist।
8 GiB RSS/2 GiB reserve/CPU+wall time/core/offline/kill-wait guards অপরিবর্তিত।
167 lightweight tests PASS (14.78s), Ruff lint/format, plan drift/whitespace PASS।
Private PROT_NONE virtual reservation test কোনো physical 32 GiB allocation নয়;
CUDA runtime mocked; real hardware/generation/deployment/paid GPU হয়নি।
Application AS blocker policy-তে resolved; next pinned CUDA runtime/driver ও tiny
allocation preflight; Pod resources/remote snapshot-ও বাকি। Phase 5.4 incomplete।

**5.4 CUDA runtime definition সম্পন্ন (2026-10-02):**
[Runtime checkpoint](image-cuda-runtime.md) এবং `requirements-sdxl-cu130.lock` যোগ।
বর্তমান torch 2.14.0+cu130/diffusers 0.40.0/transformers 5.16.1/accelerate 1.14.0/
safetensors 0.8.0 অপরিবর্তিত; Python 3.12/Linux amd64, Ubuntu 24.04 RunPod base
CUDA 13.0.0 image registry digest verified। Wheel toolkit 13.0.3.0/runtime
13.0.96; নির্বাচিত Linux host driver >=580.126.20। 62 wheel version/hash pin এবং
95 active dependency constraints PASS; tiny 84-byte safetensors pread tensor/slice
read ও pipeline import PASS। Public metadata-only network review; কোনো binary,
model/image download, install, deployment বা GPU allocation/generation হয়নি।
Torch sidecar HTTP 403; dependency evidence installed/PyPI metadata, cu130 binary
পুনরায় extract নয়। Clean install/resolver ও hardware compatibility এখনো unverified।
Source/architecture/guards অপরিবর্তিত। Next clean locked install, tiny CUDA
operation/library/resource preflight, এরপর remote snapshot verification;
paid launch-এর অনুমোদন নেই। Phase 5.4 acceptance incomplete।

**5.4 snapshot portability সম্পন্ন (2026-10-02):**
[Checkpoint/copy recipe](image-snapshot-portability.md), 18-file SHA256 manifest
ও explicit copy list যোগ। Existing revision 71153311d3dbb46851df1931d3ca6e939de83304:
18 symlink-এর সব target present; full content 13,878,864,870 bytes (~12.926 GiB)।
সব file streaming SHA256, JSON parse ও চার F32 safetensors header/shape/offset/
length PASS; weight hashes existing blob/inventory identity-র সঙ্গে মেলে।
Portable `rsync -aL --files-from` recipe blob dependency দূর করে remote final copy
বানাবে; কোনো local huge duplicate/cache edit/custom loader নয়। Tiny fixture-এ
dereference copy, source blob ছাড়া checksum PASS, corruption/missing rejection PASS।
Manifest/list coverage ও docs checks PASS। REMOTE READY মানে verified copy source;
remote transfer/checksum হয়নি। কোনো download/deploy/GPU/heavy generation হয়নি।
Next clean locked runtime install + tiny CUDA/library/resource preflight এবং remote
destination checksum; paid resource authorization নেই। Phase 5.4 incomplete।

**5.4 remaining original plan — Step 1 runtime specification সম্পন্ন (2026-10-02):**
[ComfyUI checkpoint](comfy-runtime.md), machine-readable source manifest ও additive
`requirements-comfy-cu130.lock` যোগ। v0.38.0 commit
`6b747c0428c343e1417219641db93a4fb7cb69ae` pinned; built-in deprecated
DiffusersLoader ও সাত workflow node present; custom nodes নেই। Existing 62-package
CUDA/torch lock অপরিবর্তিত, 45 additional wheels/version/hash pinned। 182 active
metadata checks/Python constraints/platform wheel availability PASS; exact official
torch ও torchvision cu130 sidecars PASS (আগের r2 403 metadata সীমা resolved)।
Source isolated fixture checks: schema/alias/path rejection/four weight filenames
PASS; actual CLIPTokenizer import PASS; existing workflow/provider 51 tests PASS।
Source/metadata compatibility verified; clean install, native ABI/server/GPU/model
execution unverified। Step 1 definition complete; full Phase 5.4 incomplete।
কোনো install/binary/model download/ImageProvider edit/RunPod/heavy generation হয়নি।
Next Step 2 ImageProvider request-এর বাইরে; owner install ও tiny runtime preflight
pending, paid resource authorization নেই।

**5.4 runtime prerequisite check BLOCKED (2026-10-03):** Owner next-work নির্দেশে
[local preflight](comfy-local-preflight.md) করা হয়েছে। Existing `.venv` Python
3.12.3-এ torch import PASS/CUDA build 13.0; torchvision, comfy-kitchen, comfy-aimdo
ও frontend package metadata নেই; comfy import spec ও পাঁচটি expected install path
অনুপস্থিত। CUDA available False/device count 0; nvidia-smi PATH-এ নেই; inherited
AS unlimited। Probe exit 0, runtime acceptance নয়। Native/server/tiny CUDA checks
blocked; owner-installed runtime path প্রয়োজন। Install/download/model load,
paid deployment ও adapter implementation হয়নি। Next pending runtime verification;
Phase 5.4 real image acceptance অসম্পূর্ণ।

**5.4 offline ComfyImageProvider adapter সম্পন্ন (2026-10-03):** Owner GPU ছাড়া
করা যায় এমন development চালানোর অনুমোদন দিয়েছেন। [Checkpoint](comfy-image-adapter-checkpoint.md)।
Injected executor → existing graph → verified bounded 512x512 PNG → unique saved
ImageResult; seed/model/checksum ও explicit mock provenance retained। Unsupported
request, timeout, execution/save I/O failure ও cancellation handled; retries নেই।
Baseline 51 PASS; shared mock/adapter contracts ও workflow/failure tests 74 PASS;
Ruff lint/format ও plan drift PASS। Install/download/live executor/GPU generation
হয়নি; next bounded transport with fake HTTP tests existing offline scope-এ।
Runtime preflight GPU আসা পর্যন্ত deferred; Phase 5.4 real acceptance অসম্পূর্ণ।

**5.4 bounded mock Comfy HTTP transport সম্পন্ন (2026-10-03):**
[Checkpoint](comfy-http-checkpoint.md)। New `comfy_http.py` executor exact injected
MockTransport-only; one submit, bounded history polling, verified node 7 output
download। 1 MiB JSON/16 MiB image caps, MIME/path/receipt/history validation,
cooperative deadlines/cancellation ও stream closure; no retry/redirect/live network।
Full fake HTTP→ImageProvider path mock provenance ও valid saved PNG verified।
123 tests PASS (49 new transport tests), Ruff lint/format, plan drift ও docs checks
PASS। Local cancellation server work stop করে না; ambiguous outcome/restart
recovery deferred। Next prompt-scoped cancellation/receipt handling, offline
owner-authorized scope। No install/GPU/model load; Phase 5.4 incomplete।

**5.4 prompt-scoped Comfy cancellation/receipt সম্পন্ন (2026-10-03):**
[Checkpoint](comfy-cancellation-checkpoint.md)। Validated immutable in-memory
receipt retained on execution errors; cancellation/timeout sends one targeted
`/api/jobs/{id}/cancel` with independent 5s cooperative cleanup budget। Strict
dispatch/no-op/unknown observations পৃথক, cleanup failure original error ঢাকে না।
Receipt missing/invalid হলে cancel নয়; reused executor-এ stale receipt নেই।
Submit চলাকালে local cancellation receipt read শেষ হওয়া পর্যন্ত bounded defer হয়।
123 baseline/141 final tests PASS; Ruff lint/format, plan drift ও docs checks PASS।
No live transport/install/GPU generation; acknowledgement execution stop-এর proof
নয়। Next durable submission intent/receipt recovery within approved offline scope;
Phase 5.4 real image acceptance এখনও incomplete।

**5.4 durable Comfy intent/receipt recovery সম্পন্ন (2026-10-03):**
[Checkpoint](comfy-journal-checkpoint.md)। `comfy_journal.py` mock-only wrapper
private local journal-এ intent fsync করে submit; accepted receipt persist করে poll।
Existing journal blocks re-submit, flock prevents concurrent owners; schema/hash
validation-এর পরে explicit GET-only recovery। Receipt callback failure typed
io_error with receipt; unknown/corrupt records never trigger network submission।
141 baseline/166 final tests PASS, including actual subprocess abrupt exit/restart
with one POST total; Ruff lint/format, plan drift ও docs checks PASS। Existing DB
অপরিবর্তিত, independent v1 journal। No install/live GPU; raw executor bypass করলে
durable protection নেই, caller একই job-এর journal path retain করবেন। Next durable
ImageProvider integration/verified-result acceptance within approved offline scope।

**5.4 durable ImageProvider recovery integration সম্পন্ন (2026-10-03):**
[Checkpoint](comfy-durable-image-checkpoint.md)। New `comfy_durable_image.py`
explicit generate/recover composition দিয়ে durable journal ও existing identical
PNG validation/save path যুক্ত করে। Recovery GET-only; unique verified ImageResult,
checksum/model/seed/mock provenance preserved। Corrupt media/cancellation/save
failure coverage; previous output/journal preserved, re-submit blocked। Shared
provider contracts durable implementation-এও চলে। 166 baseline/189 final tests
PASS, including abrupt subprocess exit → fresh-process verified image recovery
with one submit; Ruff lint/format, drift/docs checks PASS। No schema/install/GPU/UI
change; Phase 5.4 real image gate pending। Next node/model preflight mock contract
within existing offline scope; installed GPU/runtime validation deferred।

**5.4 Comfy node/model inventory preflight সম্পন্ন (2026-10-03):**
[Checkpoint](comfy-preflight-checkpoint.md)। New `comfy_preflight.py` validates six
unique node schemas/ports/selected model alias; HTTP executor-এর bounded read-only
preflight ও new `CheckedComfyExecutor` opt-in dispatch gate। Missing/incompatible
inventory/HTTP/timeout/cancel blocks submit; successes cached নয়। Synthetic fixture
ও checked ImageProvider flow covered। 189 baseline/219 final tests PASS, Ruff
lint/format, drift/docs checks PASS। Raw/durable path automatic gating বাকি; numeric
constraints/custom validation/GPU/weights identity proof নয়। No install/live/GPU
run। Next durable preflight integration within approved offline scope।

**5.4 durable preflight integration সম্পন্ন (2026-10-03):**
[Checkpoint](comfy-durable-preflight-checkpoint.md)। Durable executor lock-এর
মধ্যে existing-journal guard-এর পরে এবং intent fsync-এর আগে mandatory inventory
preflight চালায়; post-preflight cancellation check। Failure leaves no intent/POST,
explicit corrected retry allowed। Recovery remains history/download GET-only,
inventory unavailable হলেও blocked নয়। Shared synthetic object_info fixture দিয়ে
durable/image/real subprocess tests updated; previous raw executor behavior intact।
219 baseline/226 final tests PASS, Ruff lint/format, drift/docs checks PASS। No
schema/install/live GPU change। Next offline readiness/gap review; real Phase 5.4
acceptance/runtime/GPU gates deferred।

**5.4 offline readiness/gap review সম্পন্ন (2026-10-04):**
[Review](comfy-readiness-review.md)। Relevant source ও checkpoints মিলিয়ে mock
workflow/HTTP/image/durable/preflight completion এবং real execution-এর পাঁচটি gate
লেখা হয়েছে: installed runtime/GPU, model/server validation, live transport/durable
identity, supervision/recovery, verified real image। Latest 226 PASS evidence reused;
docs-only review-তে app tests পুনরায় নয়। Runtime/GPU সর্বশেষ evidence-এ unavailable;
owner installation ও RunPod suspension বহাল। Next authorized offline micro-step:
live transport/durable identity contract design; live enable/5.5/new phase নয়।
Local documentation links/whitespace, RESUME length ও plan excerpt drift PASS।

**5.4 live transport/durable identity offline contract সম্পন্ন (2026-10-04):**
[Design checkpoint](comfy-live-contract.md)। Explicit HTTPS/auth/provenance boundary,
v2 job/origin/deployment/runtime/model identity, deterministic same-job journal path,
v1 mock-only backward read/no implicit promotion এবং receipt-less no-resubmit policy
নির্দিষ্ট। Future acceptance matrix যোগ; source/schema/runtime পরিবর্তন হয়নি।
Existing 226 PASS mock baseline reused, নতুন app test run নয়। Next authorized
GPU-independent micro-step: offline v2 identity record/versioned reader ও tests;
writer migration/live factory/dispatch নয়। Real runtime/GPU/5.4 gates deferred।
Documentation links/whitespace, RESUME ≤60 lines ও plan excerpt drift PASS।

**5.4 offline v2 identity record/versioned parser সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-identity-checkpoint.md)। New strict/frozen v2 identity model,
HTTPS origin canonicalization ও bounded bytes version dispatcher; v1 stays v1,
no live promotion/writes/network। 72 new identity + 226 existing regressions =
298 PASS; Ruff lint/format PASS। Existing executor/v1 writer untouched, DB schema
অপরিবর্তিত। Next authorized offline context-matching helper/mismatch tests;
v2 writer/live transport/runtime/GPU integration deferred, real 5.4 incomplete।
Plan drift, documentation links/whitespace ও RESUME length checks PASS।

**5.4 offline execution-context matching সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-context-checkpoint.md)। Strict/frozen independent execution
context ও bounded v2 match helper; all seven identity fields exact-match, invalid
context পুনরায় validated, v1 rejected without promotion, intent unchanged।
39 new cases + 298 regressions = 337 PASS; Ruff lint/format PASS। No writer/DB/live
integration। Next authorized offline deterministic job-ID v2 storage/atomic writes
ও tests; execution wiring পৃথক। Real 5.4/runtime/GPU gates deferred।
Plan drift, docs links/whitespace ও RESUME length checks PASS।

**5.4 deterministic v2 mock journal storage সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-storage-checkpoint.md)। New ComfyJournalStore: private root/job-ID
path, permanent flock/thread ownership, bounded identity-matched read, create-only
intent ও intent→accepted atomic write/fsync। Existing v1/corrupt record preserved;
live rejected। 20 new + 337 prior tests = 357 PASS, including actual process exit,
fsync/replace failures ও no-recreate। Next authorized mock v2 durable executor
integration; storage এখনও dispatch-এ wired নয়, real runtime/GPU/5.4 deferred।
Ruff lint/format, plan drift, docs links/whitespace ও RESUME length PASS।

**5.4 mock v2 durable executor integration সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-v2-executor-checkpoint.md)। New v2 executor lock/preflight/intent/
single-submit/receipt persistence এবং identity-matched GET-only recovery যুক্ত করে।
V1 unchanged; live rejected, unknown intent no-resubmit। 21 new + 357 prior =
378 tests PASS, including actual process crash/restart at submit/download। Ruff
lint/format PASS। Next authorized offline v2 durable ImageProvider composition ও
verified-image tests; live/runtime/GPU/real 5.4 gates deferred।
Plan drift, docs links/whitespace ও RESUME length checks PASS।

**5.4 v2 durable ImageProvider composition সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-v2-image-checkpoint.md)। Existing durable provider exact v1/v2
executor গ্রহণ করে; একই PNG verification/save, accurate mock metadata ও GET-only
recovery। Existing v1 tests বজায় রেখে v2 parameterization/shared contracts যোগ।
378 + 23 = 401 tests PASS; actual crash/fresh-process saved-result verification,
one submit, corrupt media/cancel/save failure checks PASS। Ruff lint/format PASS।
Next authorized offline endpoint/auth configuration validation ও secret-safe tests;
client/network creation নয়। Real runtime/GPU/5.4 ও 5.5 gates deferred।
Plan drift, docs links/whitespace ও RESUME length checks PASS।

**5.4 offline endpoint/auth configuration সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-config-checkpoint.md)। New frozen ComfyEndpointConfig canonical
HTTPS origin ও explicit SecretStr validate করে; token excluded from repr/public
export/equality, fixed policy metadata ও sanitized errors। No client/network/env
loading। 39 new + 111 identity/context = 150 tests PASS; unchanged full 401 baseline
reused। Ruff lint/format PASS। Next authorized mock-only authenticated request
boundary/tests; real transport activation/runtime/GPU/5.4 gates deferred।
Plan drift, docs links/whitespace ও RESUME length PASS।

**5.4 mock-only authenticated request boundary সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-auth-checkpoint.md)। New selected-origin bearer mock client,
narrow routes, no redirects/retry/proxy discovery, sanitized status/transport errors,
16 MiB cap। Existing executors untouched; no real network。 23 new + 150 config/
identity = 173 tests PASS; previous unchanged 401 baseline reused। Ruff lint/format
PASS। Next authorized bounded workflow/auth mock integration + view validation;
live/runtime/GPU/real 5.4 deferred।
Plan drift, docs links/whitespace ও RESUME length PASS।

**5.4 authenticated mock workflow integration সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-auth-workflow-checkpoint.md)। Existing partial integration verified
and completed: selected origin binding, shared bounded HTTP parsing, mandatory safe
view parameters। Shared plain/auth HTTP contracts এবং durable auth failures cover
preflight-before-intent, one ambiguous submit/no retry, GET-only recovery, unchanged
journal and secret-free errors। 541 relevant tests PASS; Ruff lint/format PASS।
Initial new test lock misuse corrected; old byte-cap test moved to a valid inventory
route after mandatory view validation। No live network/install/GPU/model run।
Next offline readiness/gap review; additional implementation scope pending;
real 5.4/runtime/GPU and later phase gates remain deferred।

**5.4 post-auth readiness/gap review সম্পন্ন (2026-10-04):**
[Review](comfy-readiness-review.md) বর্তমান source/checkpoint-এর সঙ্গে মিলিয়ে
হালনাগাদ: v2 identity/storage, selected-origin auth ও workflow integration এখন
সম্পন্ন; fixed-host ও arbitrary-filename gap-এর পুরোনো বর্ণনা সংশোধিত। Previous
541 PASS evidence reused; docs-only step-এ app tests/runtime probe নয়। Real
TLS/auth/provenance, supervision/cleanup, target model registration ও native
runtime/GPU gates এখনও pending; real image নেই। Docs links, RESUME length,
whitespace ও plan excerpt drift PASS। Next proposal: owner next-work নির্দেশে
শুধু offline Comfy supervision contract design; existing runtime verification
prerequisites আসা পর্যন্ত deferred। Source/requirements বা phase scope বদলায়নি।

**5.4 offline Comfy supervision contract সম্পন্ন (2026-10-04):**
[Design](comfy-supervision-contract.md): RAM/VRAM/time capability boundaries,
separate proposed cleanup sidecar, intent-before-action/no automatic retry,
receipt-less unknown, GET-only recovery ও independent job/worker/compute/storage
stop evidence নির্দিষ্ট। Current cancellation ও existing GPU supervisor source/
checkpoint সীমা মিলিয়ে দেখা হয়েছে। Source/schema/requirements বদলায়নি। Docs
links/RESUME length/whitespace/plan drift PASS; previous 541 PASS reused, new app
run নয়। Next proposed owner-authorized micro-step: pure offline supervision
policy/observation schema validation/tests; writer/launcher/live integration নয়।
Runtime/GPU ও real 5.4 deferred; নতুন phase বা paid action অনুমোদিত নয়।

**5.4 offline supervision policy/observation schema সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-supervision-schema-checkpoint.md)। New strict/frozen pure policy
and mock-only observation models, bounded sanitized parser, original identity
matching ও independent cleanup statuses। Nested context schema, evidence digest
reference validation; evidence verification/stop proof নয়। 262 targeted tests PASS
(supervision, identity, journal, storage); Ruff lint/format, docs links/RESUME
length/plan drift/whitespace PASS। Previous unchanged 541 workflow baseline reused।
No writer/process/network/model run; current persisted formats unchanged। Next
proposed owner-directed micro-step: bounded mock sidecar storage/read compatibility,
same-job lock ও generation-journal preservation; live/runtime/GPU gates বহাল।

**5.4 mock supervision sidecar storage সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-supervision-storage-checkpoint.md)। Create-only deterministic
sidecar uses same generation job lock; absent means unknown, corrupt/mismatched
records fail closed। Bounded no-follow reads, 0600 atomic write/file+directory fsync;
v1/v2 generation bytes preserved। 275 targeted tests PASS (13 new); lint/format,
docs links/RESUME length/plan drift/whitespace PASS। No source refactor/live I/O।
Update/transition/attempt guard ও accepted receipt matching deferred to next
owner-directed micro-step; no cleanup dispatch/process launch authorization।
Real runtime/GPU/5.4 gates remain pending।

**5.4 guarded mock cleanup transitions সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-supervision-transitions-checkpoint.md)। Same-lock transition
not_requested→intent→observed/unknown, one-attempt guard, accepted generation receipt
matching, immutable primary outcome/created time ও nondecreasing update time। Atomic
writer reuse; generation bytes preserved। 287 relevant tests PASS (12 new), Ruff
lint/format এবং docs/plan checks PASS। No cleanup dispatch/live run। Next owner-
directed step: durable cancellation integration with existing mock executor;
real runtime/GPU/5.4 gates বহাল।

**5.4 mock durable cancellation integration সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-durable-cancel-checkpoint.md)। Per-call HTTP cancellation handler
V2 same-lock sidecar create/intent→single cancel→observation persist চালায়;
default fallback নেই। Pre-dispatch persistence failure zero cancel, post-dispatch
write failure primary error retain করে cleanup io_error দেয়। Recovery GET-only,
ack is not stop proof। 671 Comfy/image tests PASS (6 new), Ruff ও docs/plan checks
PASS। Next owner-directed step: local subprocess crash acceptance for cancellation;
no real runtime/GPU/live activation।

**5.4 cancellation process-crash acceptance সম্পন্ন (2026-10-04):**
[Checkpoint](comfy-cancel-crash-checkpoint.md)। Four subprocess exit boundaries:
initial/intent/ack/observed। প্রতিটির পরে দুই fresh recovery process-এ no duplicate
submit/cancel, GET-only reads, preserved journal/sidecar bytes ও lock release PASS।
56 targeted tests PASS; prior unchanged 671 baseline reused। Ruff ও docs/plan checks
PASS। Test-only changes; host crash/live stop evidence নয়। Cancellation chain done;
next authorized native runtime/GPU verification prerequisites deferred। Telemetry/
outer supervision implementation scope separately unresolved; no new phase/live run।

**5.4 next runtime prerequisite recheck (2026-10-04): BLOCKED।**
[Evidence](comfy-local-preflight.md)। চার required package metadata missing,
পাঁচ known checkout/interpreter path absent, nvidia-smi unavailable। Read-only probe
exit 0; native imports/CUDA/model execution হয়নি। Owner-installed alternate runtime
path requested; installation owner-এর দায়িত্ব। Source/test বদলায়নি; app tests নয়।
Next: supplied runtime path-এ authorized native verification; new phase নয়।

**5.4 runtime prerequisite recheck (2026-10-05): BLOCKED।**
[Evidence](comfy-local-preflight.md)। Local ComfyUI checkout এখন উপস্থিত, pinned
HEAD মেলে এবং checkout clean। Project .venv-এ চার required package এখনও missing;
বাকি চার known path absent; nvidia-smi unavailable। Metadata probe exit 0;
native/GPU/model execution হয়নি। Source/tests অপরিবর্তিত; app tests প্রয়োজন নেই।
Next: owner-installed interpreter পেলে existing authorized native preflight।

**5.4 owner-installed dependency verification (2026-10-05): dependency PASS।**
[Evidence](comfy-local-preflight.md)। 107 locked package versions match; pip check
ও torch/torchvision/comfy_kitchen/comfy_aimdo imports PASS। Pinned ComfyUI checkout
clean। Bounded import probe exit 0 (~9.1s); CUDA build 13.0 কিন্তু available False,
device count 0; nvidia-smi নেই। GPU gate BLOCKED; tiny CUDA/server/model execution
হয়নি। Alternate interpreter request resolved; no dependency/source/test changes।
Next authorized native/CUDA verification needs available GPU; paid launch নয়।

**5.4 GPU-independent resource guard design (2026-10-05): সম্পন্ন।**
[Design/checkpoint](comfy-resource-guard-design.md)। Existing policy/cancellation
পুনর্ব্যবহার করে telemetry identity/freshness/RAM/VRAM boundaries, shared monotonic
deadline এবং admission/running decisions নির্ধারিত। R1–R7 pure tests ও পৃথক future
dummy-process/integration acceptance matrix লেখা হয়েছে; tests চালানো হয়নি।
Source/requirements অপরিবর্তিত; docs links/RESUME length/plan drift/whitespace checks।
Next owner-directed micro-step: pure evaluator + R1–R7; GPU blocker এই কাজে নেই।
বর্তমান design authorization process launcher/live/new phase অন্তর্ভুক্ত করে না।

**5.4 pure resource/deadline evaluator (2026-10-05): সম্পন্ন।**
[Checkpoint](comfy-resource-guard-checkpoint.md)। Existing policy reuse, strict mock
sample identity/freshness, RAM/VRAM/reserve boundaries, shared deadlines, deterministic
deny/abort reasons; clock/I/O/process/GPU execution নেই। New 72 tests; relevant
combined 223 PASS। Ruff lint/format ও docs/plan checks PASS। No storage schema or
executor changes। Next owner-directed step: owned dummy-child supervisor/P1–P3;
durable integration/live/real image আলাদা pending।

**5.4 owned dummy-child supervisor/P1–P3 (2026-10-05): সম্পন্ন।**
[Checkpoint](comfy-dummy-supervisor-checkpoint.md)। Fixed dummy modes, synthetic
telemetry admission/abort, shared deadline, cooperative SIGTERM→SIGKILL→bounded
reap; unknown remote status, no relaunch/arbitrary PID/command। New 15 tests include
real subprocess cleanup, disappearing telemetry, unrelated child isolation, simulated
exit race/reap failure ও setup-exception cleanup। Relevant 238 PASS; Ruff/docs checks
PASS। No existing executor/journal schema edits, real GPU/model/server run নেই।
Next owner-directed step: I1 mock durable child-exit acceptance; live wiring নয়।

**5.4 I1 supervised mock child-exit recovery acceptance (2026-10-05): সম্পন্ন।**
[Checkpoint](comfy-supervised-recovery-checkpoint.md)। Actual dummy supervisor-এ
test-only fixed executor child substitution; intent/submitted/accepted/cancel-observed
boundaries-এ telemetry abort→kill/reap। Two fresh recovery processes per case;
no duplicate submit/cancel, accepted GET-only, intent-only no requests; journal/
sidecar bytes preserved। Initial relevant combined 75 PASS; strengthened new cases
4 PASS; Ruff/docs checks PASS। Production source unchanged। Next owner-directed
step: consolidated readiness/gap review; no repeated completed tests/GPU probes।

**5.4 consolidated readiness/gap review (2026-10-05): সম্পন্ন।**
[Review/next scope](comfy-readiness-review.md)। Stale missing-dependency ও non-durable
cancellation claims corrected; R1–R7/P1–P3/I1 completed evidence এবং production
composition/telemetry/enforcement gaps আলাদা। Existing 238/75/4 PASS evidence reused,
counts যোগ নয়; docs-only links/RESUME length/plan drift/whitespace checks PASS।
Next owner-directed micro-step: bounded local RAM reader/tests, owned direct-child
identity/RSS + host MemAvailable; no fake VRAM/tree coverage or live wiring।
Master requirements/source unchanged; GPU পুনরায় probe হয়নি।

**5.4 bounded local RAM telemetry reader (2026-10-05): সম্পন্ন।**
[Checkpoint](comfy-ram-telemetry-checkpoint.md)। Owned direct-child PID/parent/start
ticks, bounded procfs reads, VmRSS/MemAvailable byte conversion, explicit unknown
failure/VRAM এবং local/direct-child provenance। 37 new cases, relevant 124 PASS;
Ruff/docs checks PASS। Small child read-only measurement/exit tests; no model/GPU।
Next owner-directed scope: CPU-only dummy telemetry integration contract; no fake
VRAM/full admission, live launcher বা process-tree enforcement।

**5.4 CPU telemetry/dummy supervision contract (2026-10-05): সম্পন্ন।**
[Contract](comfy-cpu-supervision-contract.md)। Partial CPU-only guard, strict reading
validation, unknown VRAM, first-sample bootstrap, single in-flight sampler এবং
independent parent deadline/late-result/bounded-join semantics নির্ধারিত। Stuck
sampler fully-closed নয়; direct child coverage only। Source/tests/master unchanged;
124 PASS evidence reused; docs links/length/drift/whitespace PASS। Next owner-directed
scope C1 pure CPU guard/tests; C2 sampler ও C3 fixed dummy wiring পৃথক steps।

**5.4 C1 pure CPU guard (2026-10-05): সম্পন্ন।**
[Checkpoint](comfy-cpu-guard-checkpoint.md)। Strict LocalRamReading identity/type/
provenance validation, explicit CPU-only/unknown VRAM, RAM/reserve/stale/deadline
abort, deterministic multi-reasons ও frozen result। 65 new cases, relevant combined
273 PASS; Ruff lint/format ও docs checks PASS। No existing source/schema/live changes।
Next owner-directed step: C2 single-read sampler lifecycle/tests; C3 wiring পৃথক।

**5.4 C2 RAM sampler lifecycle (2026-10-08): সম্পন্ন।**
[Checkpoint](comfy-ram-sampler-checkpoint.md)। Existing unfinished source/tests
যাচাই; serialized read, single latest slot, preserved read-start timestamp,
one-shot lifecycle, stop/late-publication suppression ও deadline-bounded join।
Late exception stop-এর পরে state বদলাত—সংশোধিত ও regression covered।
22 sampler cases; relevant combined 295 PASS, Ruff/docs checks PASS। Stuck read
unknown/manual cleanup obligation; C3 supervisor wiring নেই। No GPU/model/live run।
Next owner-directed micro-step C3 fixed dummy integration; নতুন phase নয়।

**5.4 C3 fixed CPU dummy integration (2026-10-08): সম্পন্ন।**
[Checkpoint](comfy-cpu-dummy-checkpoint.md)। Real owned-child RAM sampler/CPU guard,
bounded bootstrap, first failure retention, independent stop/kill/reap এবং
parent-confirmed normal exit। Unknown cleanup handles retained; worker cleanup
sampler join-এর আগে। Existing unfinished source সংশোধিত; 20 new tests,
combined 315 PASS; Ruff/docs checks PASS। No GPU/model/live run/install।
Next owner-directed readiness review; real 5.4 GPU gate blocked, নতুন phase নয়।

**5.4 post-C3 readiness review (2026-10-08): সম্পন্ন।**
[Review](comfy-readiness-review.md)। Reader/C1–C3 completion ও GPU/live gaps sync;
RESUME-এর stale C3-next entry সংশোধিত। Existing 315 PASS evidence reused; source/
tests cross-check-এ exceptional cleanup ownership gap: parent exception-এর পরে
unknown sampler/worker handle result দিয়ে ফেরে না; cleanup action failure-এ বাকি
cleanup বাদ পড়তে পারে। নতুন fault injection হয়নি; normal-path acceptance বহাল।
Next owner-directed একক bug fix + targeted regressions নির্ধারিত; implementation
নয়। Docs links/length/drift/whitespace PASS; no runtime probe/install/model/GPU।

**5.4 C3 exceptional cleanup ownership fix (2026-10-08): সম্পন্ন।**
[Checkpoint](comfy-cpu-cleanup-checkpoint.md)। Original exception-এ retained child/
sampler session, deadline/status/bounded codes; independent cleanup attempts,
original error identity preserved। Five regression cases, combined 320 PASS;
Ruff/docs checks PASS। Review finding closed; no install/model/GPU/live run।
Next existing-authorized GPU/native preflight available environment পর্যন্ত blocked;
একই GPU probe পুনরায় নয়; 5.5/new phase অনুমোদিত নয়।

**5.4 live transport offline contract/design (2026-10-08): সম্পন্ন।**
[Contract](comfy-live-transport-contract.md)। Owner GPU absent confirmed; offline
design authorized। Selected HTTPS/TLS/auth, narrow routes, no retry/redirect,
cooperative deadline, ownership/cleanup, ambiguous submit/GET-only recovery ও
live provenance/durable/supervision gates নির্ধারিত। Source/requirements unchanged।
Docs links/length/drift/whitespace PASS; no app test/server/network/model/GPU run।
Next owner-directed L1 pure request-policy validator/tests; implementation এখনও
অনুমোদিত নয়। Live dispatch/new phase/paid approval এতে অন্তর্ভুক্ত নয়।

**5.4 L1 pure request-policy validator (2026-10-08): সম্পন্ন।**
[Checkpoint](comfy-request-policy-checkpoint.md)। Canonical origin reuse, strict
route/method/view/payload-shape ও finite positive timeout; bounded typed errors।
64 new cases, combined 237 PASS; forbidden socket/DNS/client fixture, Ruff/docs PASS।
Existing mock/auth/executor/storage gates unchanged; no live/network/GPU/install।
Next owner-directed L2 transport factory/lifecycle offline failure tests।

**5.4 L2 explicit transport factory/lifecycle (2026-10-08): সম্পন্ন।**
[Checkpoint](comfy-transport-checkpoint.md)। Standalone verified HTTPS/no ambient
proxy/no retry factory, separate mock injection, L1 policy, response cap/deadline/
cancellation checks, retained cleanup failures। 34 new cases; combined 271 PASS;
Ruff/docs PASS। Factory construction only, requests mock; no actual network/GPU।
Existing executor/storage live gates intact। Next owner-directed L3 offline shared
executor composition/provenance tests; per-I/O timeout hard total deadline নয়।

**5.4 L3 offline executor composition/provenance (2026-10-08): সম্পন্ন।**
[Checkpoint](comfy-transport-composition-checkpoint.md)। Existing partial composition
preserved/completed; shared request policy all executor paths, bounded transport
MIME/caps, mock admission/recheck, shared JSON/media parser ও retained cleanup handle।
Baseline 520 PASS; final 590 PASS, Ruff/format/excerpt checks PASS। Initial circular
import fixed with deferred policy import। No live/network/GPU run; mock durable
recovery tested, live storage unchanged। Next owner-directed L4; implementation
শুরু হয়নি, actual target/GPU acceptance blocked।

**5.4 L4.1 standalone live-mode journal storage (2026-10-08): সম্পন্ন।**
[Checkpoint](comfy-live-storage-checkpoint.md)। Owner L4 next-work authorization-এ
প্রথম একক অংশ; explicit LiveComfyJournalStore, existing mock constructor gate,
same-job path/lock/context isolation ও atomic persistence reuse। Existing v2 schema
অপরিবর্তিত; v1 mock remains readable/no upgrade, v2 bytes no rewrite/relabel।
Baseline 242 PASS; final 290 PASS (+48); Ruff/format/drift/docs checks PASS।
No live workflow/supervision admission, network/server/GPU/model run বা install।
পূর্ণ L4 incomplete; next L4.2 offline live supervision contract/storage existing
L4 scope-এ authorized, actual target/GPU ও supervised acceptance blocked/pending।

**5.4 L4.2 offline live supervision contract/storage (2026-10-08): সম্পন্ন।**
[Checkpoint](comfy-live-supervision-checkpoint.md)। Separate live schema v2/parser/
store, strict bounded context/source validation, existing mock v1 backward-read
ও rejected cross-mode migration; same job lock/atomic writes/receipt-matched
one-attempt transitions reuse। Baseline 254, final 337 PASS (+83); শেষ validator
naming edit-এর পরে schema 147 PASS; Ruff/format/drift/docs PASS। Synthetic tests
real stop evidence নয়; no live network/GPU/dispatch। Next L4.3 offline durable
composition/failure/recovery tests existing L4 authorization-এ; full L4 incomplete।

**5.4 L4.3 owned offline durable composition (2026-10-08): সম্পন্ন।**
[Checkpoint](comfy-offline-session-checkpoint.md)। Explicit mock-only session composes
bounded transport/HTTP/durable executor; ordering, GET-only restart, one cancel,
fixture provenance ও constructor/context-exit cleanup ownership verified। 20 new
cases; combined 113 PASS; Ruff/format/drift/docs PASS। Live schemas-এ synthetic
receipt/ack লেখা হয় না; live durable integration ও remote supervision বাকি।
No install/network/GPU/model run। Next L4.4 remaining live admission/supervision
prerequisite review current L4 scope-এ; full L4 incomplete, actual GPU gate blocked।

**5.4 L4.4 live admission/remote supervision review (2026-10-08): সম্পন্ন।**
[Review](comfy-live-admission-review.md)। Stale readiness matrix corrected: standalone
live transport/storage present, HTTP/durable/session still mock-only; target runtime/
TLS/model/ownership/telemetry/enforcement ও production composition gaps explicit।
Docs links/length/drift/whitespace PASS; prior checkpoint test evidence reused,
no source/test/runtime/GPU/network change। Full L4/5.4 incomplete। Next existing-
authorized bounded native/GPU preflight blocked until selected target available;
no repeated unchanged probe, no new phase/live/paid approval implied।

**5.4 GPU-free admission scope/design (2026-10-08): সম্পন্ন।**
[Contract](comfy-admission-contract.md)। Owner next-work নির্দেশে offline কাজের scope
নির্বাচন: required capability/context/worker/device/policy/source/freshness validation;
caller claims actual attestation নয়, pure result execution permission নয়। Next A1
schema/evaluator/tests owner next-work নির্দেশে; এই turn implementation নয়।
Docs links/length/drift/whitespace PASS; no source/app tests/network/GPU changes।
Real target preflight blocked; existing live gates ও paid/new-phase limits বহাল।

**5.4 A1 pure offline admission evaluator (2026-10-08): সম্পন্ন।**
[Checkpoint](comfy-admission-checkpoint.md)। Five required capability claims,
context/worker/device/policy/source/clock-session binding, explicit freshness ও
bounded deny reasons; immutable schema/snapshot/decision, no I/O বা dispatch।
Model-copy extra field serialization gap corrected with raw mapping revalidation।
Baseline 282, 85 new tests, final combined 460 PASS; Ruff/format/drift/docs PASS।
Existing live gates/schema unchanged। Next proposed owner-directed A2 fixture-only
session admission/recheck before intent; live target/GPU acceptance blocked।

**5.4 A2 offline session admission integration (2026-10-08): সম্পন্ন।**
[Checkpoint](comfy-admission-integration-checkpoint.md)। Explicit fixture snapshot,
same-lock admission before/after preflight, no snapshot/stale/mismatch/clock failure
→ no intent/POST; accepted recovery no admission/clock and GET-only। Raw legacy
mock durable callback optional; session mandatory। 22 new session cases, final
combined 237 PASS; Ruff/format/drift/docs PASS। No live/schema/install/GPU changes।
Next proposed owner-directed A3 existing mock resource evaluator integration/recheck;
actual target evidence/remote enforcement/full L4/5.4 এখনও অসম্পূর্ণ।
