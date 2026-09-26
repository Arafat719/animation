# Semantic contract — এক-call isolated model-test proposal

2026-09-21। Proposal-এর পরে owner “ok porer kaj suru kor” বলে
এই isolated harness ও এক-call execution অনুমোদন করেছেন।
[ফল](local-planner-semantic-model-test-result.md): 222.91s, REFERENCE rejection; acceptance FAIL।
[Offline contract ফল](local-planner-semantic-contract-result.md): ৬ test methods,
27 fixture outcomes PASS। এটি model quality প্রমাণ নয়।

## প্রশ্ন ও bounded scope

Verified একই model কি explicit roles/object/events সহ ছয়টি coherent shot দিতে
পারে, যা declared-fact validator এবং পৃথক narrative review—দুটিই পেরোয়?
শুধু synthetic case A, 30s, ছয়টি 5s shot। Model cast/roles, notebook ownership,
initial holder, events, actions ও camera choices লিখবে; harness missing story পূরণ
করবে না। আগের failures-এর নির্দিষ্ট gaps মাপাই উদ্দেশ্য; general planner gate নয়।

Existing `semantic-contract-v1/contract.py` ও exported schema অপরিবর্তিত থাকবে।
Schema response constraint-এ একবার; full StoryPlan schema বা synthetic positive
fixture prompt-এ পাঠানো হবে না। আগের `size-only-request.json` run request নয়।

## Exact messages ও request construction

System message:

```text
Return only a compact semantic-draft-v1 JSON object. version=1; s=shared setting, m=mood, l=lighting; c=cast with unique short IDs, unique names and roles; o=one notebook with fixed owner and initial holder; b=exactly six ordered shots. Each shot has a=short complete action sentence, f=framing, v=camera movement, c=visible cast IDs and e=its single main event.
Declare exactly one courier and one distinct owner; an optional third character is other. o.label must be notebook, o.lost=true, and o.owner must reference the owner role. Initial holder is null (unheld) or a non-owner cast ID. Every event references o.id and known cast IDs. Choose your own names and six story beats.
For pickup: actor visible, from=null, to=actor; object must be unheld, then actor holds it. For transfer: from=actor=current holder, to a different character; actor and recipient both visible, then recipient holds it. For inspect: actor visible and current holder, from/to=null. For observe or gesture: actor visible, from/to=null, holder unchanged. For mention: from/to=null, holder unchanged; onscreen actor must be visible, offscreen actor must not be visible. All physical events are onscreen. Mentioning someone does not require that person to be visible. Never imply an unrecorded custody change.
Include a courier-to-owner transfer and finish with owner holding notebook. Keep ownership fixed. Actions must name actors, objects and transfer recipients, match their events and visible cast, establish the lost notebook and roles, and show six distinct relevant beats with a clear resolution. Preserve meaning in short sentences within 120 characters. Metadata alone is insufficient: the actions must tell the requested story. No extra subplot, dialogue lines, commentary, thinking, or repeated departure padding.
```

User message:

```text
A courier returns a lost notebook at a riverside market. 30 seconds, six 5-second shots. Style: 2D Japanese anime.
```

Request base: saved `compact-v2/request.json`-এর sampling/stream/seed/cache settings
হুবহু; উপরের দুই messages; response format `json_schema`, name `semantic_draft_v1`,
strict=true, schema existing `semantic-contract-v1/schema.json`। কোনো অতিরিক্ত
few-shot/repair message নয়। একই 768 output-token cap; temperature .7, top-p .8,
top-k 20, min-p 0, presence penalty 1.5, seed 42, cache_prompt=false।

## Asset, budget ও stop limits

- একই Qwen3-4B Q4_K_M, revision `bc640142c66e1fdd12af0bd68f40445458f3869b`,
  2,497,280,256 bytes; SHA256
  `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`।
  llama.cpp b10964 / `b29c606e2`; [verified acquisition](local-planner-smoke-result.md)
  পুনর্ব্যবহার। Asset missing/changed হলে stop, স্বয়ংক্রিয় download নয়।
- CPU generation/batch threads ৪; GPU/offload ০; এক slot, context 8192;
  `--reasoning off`; এক generation call, repair/retry ০।
- Load timeout 180s; generation timeout 300s; load+generation সর্বোচ্চ 480s।
  Runtime RSS ≤8 GiB, available RAM ≥2 GiB; persistent process swapping-এ stop;
  সব planner-smoke assets/evidence মোট ≤6 GiB disk। Billable resource নয়।
- Timeout/OOM/resource breach, incomplete/length finish, output ≥768 tokens,
  malformed draft বা validation failure-এ stop। Limit বাড়িয়ে দ্বিতীয় call নয়।
- Localhost `127.0.0.1`, ephemeral port/key, নির্দিষ্ট CORS origin; key log নয়।
  সব exit path-এ runtime shutdown ও connection/LISTEN closure check।

নতুন raw evidence/harness destination `data/planner-smoke/semantic-run-v1/`;
exclusive execution marker থাকবে। পুরোনো contract/fixtures/model/raw evidence
অক্ষত; production adapter/API/UI/DB integration নয়।

## অনুমোদনের পরে execution procedure

1. Exact messages/schema/request equality, asset size/mtime ও saved checksum
   provenance, current RAM/disk যাচাই; request/harness/contract hash record।
   অপরিবর্তিত ছয়-test baseline পুনর্ব্যবহার; নতুন harness compile ও meaningful
   offline checks: contract error preserves code/path, REVIEW_REQUIRED remains
   pending, timeout/length cannot save accepted output, one-call guard।
2. Model load-এর পরে একমাত্র call। Schema conversion unsupported হলে setup/request
   error হিসেবে stop; schema silently weaken/format fallback নয়। No repair call।
3. Complete raw content-এ existing `candidate(raw)` চালানো: parsing, facts/custody,
   StoryPlan mapping এবং sidecar। Failure-এ stable code/path ও raw content সংরক্ষণ;
   candidate না থাকলে acceptance FAIL। Narrative parse সম্ভব হলে diagnostic review
   হতে পারে, কিন্তু invalid output repair বা success নয়।
4. Automated result REVIEW_REQUIRED হলে নিচের text rubric review। Raw draft,
   candidate/sidecar/custody trace এবং textual verdict পৃথক files। Automated pass
   accepted flag নয়; reviewer identity ও shot evidence বাধ্যতামূলক।
5. Prompt/output tokens ও timings, first-content/end-to-end latency, finish reason,
   reasoning/truncation, RSS/available RAM/swap, UTF-8 bytes এবং shutdown record।
   অনুপস্থিত metric `unavailable`; অনুমান করে tokens/sec নয়।

## Narrative acceptance ও সিদ্ধান্ত

| Criterion | PASS-এর evidence |
| --- | --- |
| Roles/lost object | Raw actions ও cast roles-এ courier এবং notebook owner সঙ্গত; lost item প্রতিষ্ঠিত |
| Action-event agreement | প্রতিটি action তার event actor/object/endpoints-এর সঙ্গে মেলে; reversed transfer নয় |
| Ownership/custody | Owner অপরিবর্তিত, ordered possession সংগত; hidden handover বা contradiction নেই |
| Visibility | Physical participants দৃশ্যমান; mention-only/offscreen reference-কে অকারণে cast-এ ঢোকানো নয় |
| Story quality | ছয় distinct relevant beat, notebook return-এর direction স্পষ্ট, owner পেয়ে resolution; unrelated subplot নয় |
| Assembly fidelity | Raw action অক্ষত; copied logline/derived prompts দিয়ে missing facts পূরণ হয়নি |

সব budget/structural/fact/StoryPlan checks এবং সব narrative criterion PASS হলে শুধু
**এক-case experiment PASS**। FAIL বা UNRESOLVED accepted নয়। Codex textual review
owner human approval নয়। আগের v1/v2 semantic FAIL পাল্টাবে না; Bengali, 45/60s,
traits, repeatability ও generalization অমাপা; Phase 3 gate/3.10 incomplete থাকবে।

PASS হলে পরের bounded কাজ broader-case evaluation proposal; FAIL হলে saved
code/path/narrative evidence review। এই turn বা ভবিষ্যৎ এক-call run-এর scope-এ
automatic model switch, prompt retry, larger budget বা adapter implementation নেই।

## বর্তমান checks ও authorization

এই proposal turn-এ শুধু request-এর byte হিসাব ও document checks; model/tokenizer,
fixture/app tests, harness implementation বা server run নয়। Actual byte মাপ নিচে।
[Phase 3 step 3.9](plan/phase-3.md)-এর “download/run করার আগে অনুমতি চাইবে” অনুযায়ী
পরবর্তী bounded কাজ—এই exact isolated harness প্রস্তুতি ও এক-call execution—এর
অনুমোদন owner-এর পরবর্তী নির্দেশে পাওয়া গেছে। Master requirements ও production contract অপরিবর্তিত।

## Measured overhead — execution নয়

- Schema 1,947 bytes (v2: 930); message content 1,914 bytes।
- উপরের exact request 4,222 bytes (v2: 2,485); আগের 3,506-byte size-only
  example-এর জায়গায় নতুন prompt semantics অন্তর্ভুক্ত।
- Handcrafted baseline draft 1,427 bytes; এটি output/token estimate নয়।
- নতুন token count ও latency অমাপা। বেশি event fields-এর কারণে 768-token cap বা
  300s deadline miss হতে পারে; সেটিও পরীক্ষার ফল, budget বাড়ানোর অনুমতি নয়।
- দুই পরিবর্তন—schema ও prompt—একসঙ্গে হচ্ছে; এক run থেকে কোনটির causal
  অবদান আলাদা করা যাবে না। Success-rate বা model superiority দাবি নয়।
