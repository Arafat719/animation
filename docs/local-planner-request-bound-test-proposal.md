# Request-bound policy — exact one-call test proposal

2026-09-21: proposal সম্পন্ন। 2026-09-22-এ owner “ok porer kaj koro” বলে
এই exact isolated harness ও এক-call execution অনুমোদন করেছেন।
[ফল](local-planner-request-bound-test-result.md): 300s timeout; acceptance FAIL। [Offline wrapper](local-planner-request-bound-policy-result.md)
৬ test methods/17 fixture outcomes PASS; real narrative quality অপ্রমাণিত।

## নির্দিষ্ট প্রশ্ন

একই verified model কি fixed notebook ID ও concrete scene instructions মেনে,
policy/custody checks এবং independent narrative review পেরোতে পারে? শুধু case A,
30s, ছয়টি 5s shot। Known-reference ও placeholder failure কমা মাপব; schema+prompt
উভয় বদলাচ্ছে বলে কোনটির causal অবদান আলাদা প্রমাণ নয়।

Model action sentences নিজেই লিখবে। Object ID caller-defined convention; raw
বাক্য/event সংশোধন, auto-repair, fixture answer injection বা template থেকে গল্প নয়।
Existing `request-bound-policy-v1/policy.py` অপরিবর্তিত ব্যবহার হবে।

## Exact messages

System message:

```text
Return only a compact semantic-draft-v1 JSON object. version=1. Write actual scene content: s must describe the story's physical location, m its emotional tone, and l the visible light conditions. Do not copy field labels or use the literal descriptions "shared setting", "mood", or "lighting" as their values. c is cast; o is the notebook; b contains exactly six ordered shots. Each shot contains a complete action sentence a, framing f, camera movement v, visible cast IDs c, and one main event e.
The request's object ID is exactly "notebook": o.id and every e.object must equal "notebook". o.label is notebook and o.lost=true. Choose short unique cast IDs and names, exactly one courier and one distinct owner, with optional other. o.owner references the owner role. o.holder is the initial holder: null means unheld; otherwise use a non-owner cast ID. Choose your own names and six story beats.
For pickup: actor visible, from=null, to=actor; object must be unheld, then actor holds it. For transfer: from=actor=current holder, to a different character; actor and recipient both visible, then recipient holds it. For inspect: actor visible and current holder, from/to=null. For observe or gesture: actor visible, from/to=null, holder unchanged. For mention: from/to=null, holder unchanged; onscreen actor visible, offscreen actor not visible. All physical events are onscreen. Mere mention does not require the mentioned person to be visible. Every actor/from/to refers to known cast or allowed null. Never imply an unrecorded custody change.
Include a courier-to-owner transfer and finish with owner holding the notebook. Keep ownership fixed. Each action sentence must actually describe its event, including pickup when the event is pickup, and identify actor, object and transfer recipient. Actions and metadata must agree. Establish the lost item and roles; provide six distinct relevant beats and a clear resolution, without repeated departures or unrelated subplots. Use concise English sentences within 120 characters. No dialogue lines, commentary or thinking. Metadata alone does not establish the story.
```

User message:

```text
A courier returns a lost notebook at a riverside market. 30 seconds, six 5-second shots. Style: 2D Japanese anime.
```

Base request = saved `semantic-run-v1/request.json`; replace only messages and
response schema with `request-bound-policy-v1/schema.json`। Format json_schema,
name `semantic_draft_v1`, strict=true; schema একবার, prompt-এ serialize নয়।
Seed 42, temperature .7, top-p .8, top-k 20, min-p 0, presence penalty 1.5,
cache_prompt=false; streaming/usage settings আগের মতো। Output cap 768।
Saved size-only request execution input নয়; উপরের exact messages থেকে বানাতে হবে।

## অপরিবর্তিত assets ও সীমা

- Qwen3-4B Q4_K_M, revision `bc640142c66e1fdd12af0bd68f40445458f3869b`,
  2,497,280,256 bytes; SHA256
  `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`।
  llama.cpp b10964 / `b29c606e2`; [verified evidence](local-planner-smoke-result.md)
  reuse। Missing/changed asset-এ stop; নতুন download/runtime/model নয়।
- CPU generation/batch threads ৪, GPU/offload ০, এক slot, context 8192;
  reasoning off। এক generation call, repair/retry ০; baseline rerun/B–E নয়।
- Load cap 180s; generation 300s; load+generation সর্বোচ্চ 480s। Output ≥768 tokens,
  length/incomplete finish, timeout/OOM বা invalid output-এ fail/stop।
- Runtime RSS cap 8 GiB, available RAM floor 2 GiB, persistent process swapping-এ
  stop; experiment assets/evidence disk cap মোট 6 GiB। Paid resource/API নয়।
- Server `127.0.0.1`, ephemeral port/key, নির্দিষ্ট local CORS origin; key log নয়।
  সব exit path-এ shutdown ও connection/LISTEN closure verification।

নতুন ignored destination `data/planner-smoke/request-bound-run-v1/`; exclusive
execution marker। আগের validators/fixtures/harness/raw evidence/production অক্ষত।

## অনুমোদনের পরে procedure

1. Exact request/schema/policy hashes ও asset size/mtime/checksum provenance,
   current RAM/disk verify। Existing offline suites baseline হিসেবে reuse; নতুন
   harness compile ও code/path propagation, stop-limit rejection, review-pending,
   one-call guard-এর targeted offline checks। No dependency upgrade।
2. একই runtime-এ const/schema conversion support যাচাই। Unsupported হলে setup/request
   failure report করে stop; schema weakening বা দ্বিতীয় generation নয়। Grammar
   support অনুমান করে claim নয়; Python equality check সবসময় বহাল।
3. Complete output-এ `policy.candidate(raw)`। SHAPE → REQUEST_OBJECT → PLACEHOLDER
   → existing semantic/StoryPlan checks; fail-এ raw ও code/path রেখে stop। ID
   replace বা scene default দেওয়া নয়। Candidate/sidecar/custody trace শুধু valid
   output-এ; automated status REVIEW_REQUIRED।
4. Reviewer raw actions+metadata দিয়ে rubric পূরণ করবে। Text verdict ও automated
   verdict আলাদা; FAIL/UNRESOLVED accepted নয়। Codex review owner approval নয়।
5. Request bytes, prompt/output tokens ও timings, first-content/end-to-end latency,
   finish/reasoning, RSS/RAM/swap, raw events এবং cleanup record; missing metric
   unavailable। Fixture-generated output model success হিসেবে গণনা নয়।

## Acceptance ও experiment বন্ধ করার সিদ্ধান্ত

| Criterion | প্রয়োজনীয় evidence |
| --- | --- |
| Request policy | সব object ID notebook; non-placeholder, story-relevant location/tone/light |
| Roles/ownership | courier ও owner স্পষ্ট; lost notebook প্রতিষ্ঠিত; owner আর holder গুলিয়ে যায়নি |
| Events/custody/visibility | ordered transfer সংগত; physical participants visible; hidden handover নয় |
| Action-event agreement | প্রত্যেক raw sentence event-কে বর্ণনা করে; approaches-কে pickup ধরা নয় |
| Narrative | ছয় distinct relevant beat; courier→owner return ও resolution; padding নয় |
| Fidelity/budget | raw action অপরিবর্তিত, strict candidate/limits/cleanup PASS |

সব criterion PASS হলে শুধু এক-case experiment PASS। Fixture/policy বা object-ID
success একা যথেষ্ট নয়। পুরোনো failures বহাল; Bengali, repeatability, অন্য duration,
traits ও Phase 3 gate অমাপা/অসম্পূর্ণ। 3.10 অনুমোদন নয়।

PASS → পরের bounded কাজ broader-case evaluation proposal। Narrative FAIL/UNRESOLVED
→ নতুন prompt/contract loop বন্ধ রেখে এই model+CPU path-এর suitability owner review।
Setup/resource failure হলে সেই evidence report; retry অনুমোদিত নয়। কোনো ফলেই
স্বয়ংক্রিয় দ্বিতীয় call, budget বৃদ্ধি বা model switch নয়।

## বর্তমান completion ও authorization

এই turn documentation/byte measurement only; harness edit/model/tokenizer/server
run হয়নি। Master requirements অপরিবর্তিত; document checks হবে।
পরবর্তী bounded কাজ এই exact isolated harness প্রস্তুতি ও এক-call test; অনুমোদন
owner-এর পরবর্তী নির্দেশে পাওয়া গেছে। [Phase 3 step 3.9](plan/phase-3.md)-এর “download/run করার আগে অনুমতি চাইবে”
শর্ত এই এক-call scope-এ পূরণ হয়েছে; retry বা 3.10 অনুমোদিত নয়।

## Measured request overhead

- Exact request 4,588 bytes; schema 1,985 bytes; message content
  2,232 bytes (UTF-8, compact JSON serialization)।
- আগের semantic run request 4,222 bytes; 436 prompt/395 output tokens, 222.91s।
  নতুন prompt token count/runtime cost অমাপা; bytes থেকে token অনুমান নয়।
- Fixed-ID schema মাত্র 38 bytes বড় হলেও prompt-ও বদলেছে; 300s/768-token
  budget miss হতে পারে। এই পরীক্ষার লক্ষ্য সীমার মধ্যে feasibility, সাফল্যের নিশ্চয়তা নয়।
