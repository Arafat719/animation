# 3.9 follow-up — অর্থ অক্ষুণ্ণ রাখা compact test proposal

2026-09-20। Proposal সম্পন্ন হওয়ার পরে owner-এর পরবর্তী
“ok porer kaj suru koro” নির্দেশে এই এক-call isolated test অনুমোদিত।
[Execution ফল](local-planner-semantic-test-result.md): strict PASS, semantic FAIL; run সম্পন্ন। [আগের compact ফল](local-planner-compact-test-result.md)
strict PASS হলেও semantic FAIL; সেই verdict অপরিবর্তিত।

## Evidence ও একমাত্র পরিবর্তন

আগের এক call 52.44s/175 output tokens-এ শেষ হয়েছিল। Actions ছিল `approach`,
`stop`, `open`, `handover`, `walk away`, `disappear`; notebook, মালিক ও return
সম্পর্ক raw shots-এ ছিল না। তাই এখন output cap বা timeout বাড়ানোর evidence নেই।

প্রস্তাব: **শুধু system prompt-এর action semantics স্পষ্ট করা**। Compact schema,
user story, model/runtime, sampling ও deterministic assembly আগের মতো থাকবে।
এতে পূর্ণ actor–action–object sentence এবং recipient/result তৈরি হয় কি না পরীক্ষা
হবে। এটি hypothesis; prompt পরিবর্তন যথেষ্ট হবে বা 768 tokens-এ fit হবে—দাবি নয়।
প্রতি shot-এ নতুন subject/object field যোগ করা হচ্ছে না; `a`-তেই সম্পর্ক লিখতে হবে।

## Exact proposed messages

নিচের system message একবার পাঠানো হবে; full schema, few-shot বা তৈরি ছয়টি shot
prompt-এ যোগ হবে না। `response_format`-এ আগের compact schema একবার থাকবে।

```text
Return only compact JSON. Fields: s=shared setting, m=mood, l=lighting, c=cast {id,name}, b=exactly six ordered shots {a:action,f:framing,v:camera movement,c:visible cast IDs}.
Each a must be a complete short English sentence naming the actor and an observable action. Name the object of actions such as finding, opening or handing over; name the recipient of a transfer. Use consistent cast names, not ambiguous pronouns or isolated verbs. Prefer 8-16 words per action, within 120 characters; preserve meaning before brevity.
Tell the requested story through six distinct, causally ordered visual beats. Establish that the notebook is lost and who owns it. Make the courier's return of the notebook to that owner explicit and show a clear resulting resolution. Keep object possession and cast visibility consistent. Do not pad the ending with repeated departures. The six actions themselves must convey the story without relying on a logline or this prompt.
Use short IDs, one shared setting and lighting, no dialogue, commentary or thinking. Choose the actual shot actions yourself.
```

User message হুবহু আগেরটি:

```text
A courier returns a lost notebook at a riverside market. 30 seconds, six 5-second shots. Style: 2D Japanese anime.
```

8–16 words একটি generation নির্দেশ, schema hard minimum নয়। লম্বা অথচ অর্থহীন
sentence pass নয়; ছোট কিন্তু পূর্ণ অর্থবহ sentence কেবল word count-এর জন্য fail নয়।
Story-এর lost/return/owner সম্পর্ক prompt-এ স্পষ্ট করা হয়েছে; অন্য নতুন subplot নয়।
এটি এক পরিচিত case-এর নির্দেশ মানার পরীক্ষা, generalization-এর প্রমাণ নয়।

## অপরিবর্তিত contract ও assembly

[আগের proposal-এর compact contract ও mapping](local-planner-compact-test-proposal.md)
প্রযোজ্য: top-level `s,m,l,c,b`; ছয়টি `b`-তে `a,f,v,c`; `a` সর্বোচ্চ 120 characters,
সব required, unknown field নিষিদ্ধ। Cast ১–৩, unique IDs ও valid visible references;
blank/coerced/malformed/duplicate-key/nonfinite JSON গ্রহণ নয়। Framing/movement enums,
বাকি string/array bounds অপরিবর্তিত। Schema-তে story-specific `const` বা action enum
দিয়ে উত্তর বসানো যাবে না।

Assembly raw `a` হুবহু `action`-এ রাখবে; image/motion prompts আগের labeled
concatenation। Copied logline, fixed style, IDs, ছয়টি 5.0s duration, seed 42 ও
pending/empty/null execution fields deterministic। Existing `StoryPlan.model_validate`
শেষে বাধ্যতামূলক। Missing notebook/recipient harness দিয়ে পূরণ, keyword ঢোকানো,
truncation, repair বা mock fallback নয়। Production schema/adapter পরিবর্তন নয়।

## এক-call execution envelope — আলাদা অনুমোদনের পরে

- একই verified Qwen3-4B Q4_K_M: revision `bc640142c66e1fdd12af0bd68f40445458f3869b`,
  2,497,280,256 bytes; SHA256
  `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`।
  একই llama.cpp b10964 / `b29c606e2`; [পুরোনো asset evidence](local-planner-smoke-result.md)
  পুনর্ব্যবহার। Missing/changed asset হলে stop; নতুন download/runtime/model নয়।
- শুধু case A, generation সর্বোচ্চ ১, repair/retry ০; B–E বা baseline rerun নয়।
- CPU generation/batch threads ৪; GPU layers ০, offload বন্ধ, এক slot; context 8192,
  output cap 768, reasoning off। Seed 42, temperature .7, top-p .8, top-k 20,
  min-p 0, presence penalty 1.5; prompt cache বন্ধ।
- Load timeout 180s, generation timeout 300s, load+generation সর্বোচ্চ 480s;
  runtime RSS cap 8 GiB, available RAM অন্তত 2 GiB, persistent swapping-এ stop;
  experiment directory মোট cap 6 GiB। Length finish/token cap, timeout/OOM,
  invalid output বা resource breach-এ stop; automatic দ্বিতীয় call নয়।
- `127.0.0.1` ephemeral port, ephemeral auth, নির্দিষ্ট local CORS origin; credentials
  log নয়। সব exit path-এ shutdown ও connection/LISTEN দিয়ে closure যাচাই।
- নতুন evidence destination `data/planner-smoke/compact-v2/`; পুরোনো `compact-v1/`
  harness, markers ও evidence অক্ষত। Exclusive execution marker accidental rerun
  আটকাবে। No production API/UI/DB wiring, billable resource বা personal assets।

## অনুমোদনের পরে checks ও evidence

1. Isolated harness-এ শুধু নতুন prompt বসিয়ে preflight-এ v1/v2 schema ও sampling/
   user message/assembly equality যাচাই; intended difference system message। নতুন
   request, prompt, schema ও harness hash রেকর্ড। পুরোনো four-method offline contract
   checks-এর ফল baseline; changed harness-এর compile ও প্রয়োজনীয় checks চালাতে হবে।
2. পুরোনো raw output semantic negative fixture: schema PASS হলেও notebook return
   criterion FAIL থাকে। কৃত্রিম review examples-এ শুধু `notebook` শব্দ, উল্টো transfer
   বা inconsistent possession থাকলে FAIL; এগুলো model output/PASS দাবি নয়।
   Semantic review criteria-based, automated keyword test যথেষ্ট নয়।
3. এক call শেষে raw draft → strict validation → deterministic assembly → StoryPlan
   validation। Schema-valid candidate আলাদা রাখবে; semantic verdict ছাড়া accepted
   label নয়। প্রতিটি review criterion-এ raw shot number ও সংক্ষিপ্ত evidence লিখবে।
4. Request/schema/message UTF-8 bytes, prompt tokens/time, first-content time,
   output tokens/decode time, finish reason, wall latency, sampled RSS/RAM/swap,
   full raw output ও cleanup রেকর্ড। Missing metric `unavailable` হবে।
5. আগের 52.44s/133 prompt tokens/175 output tokens-এর পাশে নতুন মাপ report করবে;
   বেশি narrative content-এর সময় আলাদা দেখাবে। এক sample-এ reliability বা causal
   speedup দাবি নয়; পুরোনো baseline পুনরায় চালানো নয়।

## Semantic acceptance rubric

এই rubric আগের semantic requirements স্পষ্ট করে; সেগুলো শিথিল করে না। কোনো
নির্দিষ্ট six-shot answer সরবরাহ করা হয়নি। সংগত বিকল্প sequencing গ্রহণযোগ্য।

| Criterion | Raw model content-এ প্রয়োজনীয় evidence |
| --- | --- |
| Action completeness | প্রতিটি shot-এ চেনা actor ও দৃশ্যমান কাজ; transitive কাজের object এবং transfer-এর recipient স্পষ্ট; bare `open`/`handover` যথেষ্ট নয় |
| Lost notebook ও ownership | notebook যে lost item এবং recipient যে owner, model-written actions-এ তা বোঝা যায়; copied logline/prompt দিয়ে শূন্যস্থান পূরণ নয় |
| Return direction | courier notebook owner-কে ফেরত দেয়; শুধু notebook নাম বা বিপরীত দিকের transfer pass নয় |
| Causal/visual consistency | possession/order-এ বিরোধ নেই; transfer shot-এ courier/recipient দৃশ্যমান cast-এ; references consistent |
| Six useful beats | ছয়টি relevant, আলাদা, ক্রমানুগ action; একই departure দিয়ে padding নয় |
| Resolution | owner-এর notebook পাওয়া বা তার পরিণতি স্পষ্ট; শুধু courier অদৃশ্য হওয়া যথেষ্ট নয় |
| Scene ও derived prompts | shared setting/light, framing/movement ও generated actions পরস্পরবিরোধী নয়; derived prompts নতুন story বানায়নি |

**এক-case PASS** পেতে সব structural/resource check এবং সব semantic criterion pass
লাগবে। Reviewer কে—Codex textual review না owner human review—স্পষ্ট report করতে
হবে; Codex verdict-কে owner approval বলা যাবে না। Human approval/real-adapter gate
আলাদা। FAIL হলে নির্দিষ্ট evidence report করে থামবে; ওই turn-এ prompt বদলে rerun নয়।

PASS হলেও Bengali/dialogue/45–60s/supplied traits/repair/repeatability অমাপা থাকবে;
আগের full five-case gate PASS হবে না। পরের কাজ ফলভিত্তিক পৃথক proposal/review;
3.10 স্বয়ংক্রিয়ভাবে অনুমোদিত নয়।

## বর্তমান completion ও authorization

Proposal তৈরির turn documentation-only ছিল: RESUME ও ledger update এবং document checks।
Model download/run, harness edit, timeout বৃদ্ধি বা completed test পুনরায় হয়নি।
Master requirements অপরিবর্তিত; excerpt regeneration প্রয়োজন নেই, drift check হবে।

এই proposal-এর পরবর্তী bounded কাজ ছিল isolated harness preparation ও এক-call
CPU test। Proposal উপস্থাপনের পর owner সেটি শুরু করার নির্দেশ দিয়েছেন;
[Phase 3 step 3.9](plan/phase-3.md)-এর “download/run করার আগে অনুমতি চাইবে” শর্ত
পূরণ হয়েছে। অনুমোদন শুধু এই এক call; repair/retry বা 3.10 এর অন্তর্ভুক্ত নয়।
