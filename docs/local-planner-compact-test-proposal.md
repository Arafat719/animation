# 3.9 follow-up — compact isolated test proposal

2026-09-20। Proposal সম্পন্ন হওয়ার পরে owner “ok porer kaj suru koro” বলে
এই এক-call isolated harness/test অনুমোদন করেছেন।
[ফল](local-planner-compact-test-result.md): strict PASS, semantic acceptance FAIL; run সম্পন্ন।
[আগের ফল](local-planner-smoke-result.md): case A 300.02s timeout, অসম্পূর্ণ
প্রথম shot; acceptance FAIL। [মূল proposal](local-planner-test-proposal.md)
ঐতিহাসিক baseline। এই নথি পরবর্তী সীমিত পরীক্ষার প্রস্তাব; 3.10 implementation নয়।

## উদ্দেশ্য ও অপরিবর্তিত asset

একই verified model/runtime দিয়ে duplicate full-schema instructions বাদ দিয়ে ছোট
content-only draft সময়সীমার মধ্যে সম্পূর্ণ হয় কি না মাপা হবে। Schema overhead-ই
আগের timeout-এর কারণ অথবা এই পরিবর্তন সফল হবে—কোনোটিই প্রতিষ্ঠিত নয়।

- বিদ্যমান ignored `data/planner-smoke/`-এর Qwen3-4B Q4_K_M ব্যবহার:
  revision `bc640142c66e1fdd12af0bd68f40445458f3869b`, 2,497,280,256 bytes;
  SHA256 `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`।
- একই llama.cpp CPU b10964 / commit `b29c606e2`; verified archive SHA256
  `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`।
- নতুন download, runtime upgrade, দ্বিতীয় model, GPU/cloud/API নয়। আগের
  acquisition/checksum evidence পুনর্ব্যবহার; asset missing/পরিবর্তিত হলে stop,
  স্বয়ংক্রিয় reacquire নয়। পুরোনো evidence অপরিবর্তিত রেখে আলাদা
  `data/planner-smoke/compact-v1/`-তে নতুন evidence রাখা হবে।

## একটিমাত্র প্রস্তাবিত run ও budget

শুধু আগের **case A**: “A courier returns a lost notebook at a riverside market.”
Target 30.0s; existing `split_duration` অনুযায়ী ছয়টি 5.0s shot। B–E, repeat,
repair, full-schema baseline rerun বা automatic retry এই প্রস্তাবের scope নয়।

| বিষয় | নির্দিষ্ট সীমা |
| --- | --- |
| Model calls | সর্বোচ্চ ১ generation; repair ০ |
| CPU/config | ৪ generation ও batch threads, GPU layers ০, offload বন্ধ, এক slot |
| Context/output | context 8192; output সর্বোচ্চ 768 tokens (আগে 3072) |
| Sampling | seed 42; temperature .7, top-p .8, top-k 20, min-p 0, presence penalty 1.5 |
| Reasoning | বন্ধ; pinned runtime-এর local help দেখে supported flag নির্বাচন/রেকর্ড |
| Deadline | model-load 180s; generation 300s অপরিবর্তিত; load+generation সর্বোচ্চ 480s |
| Memory/disk | runtime RSS সর্বোচ্চ 8 GiB; available RAM অন্তত 2 GiB; experiment directory মোট সর্বোচ্চ 6 GiB |
| Stop | প্রথম timeout/OOM, persistent swapping, cap breach, invalid/truncated output-এ পরীক্ষা শেষ |

768 tokens একটি stop cap, throughput বা success estimate নয়। JSON সম্পূর্ণ হলেও
length/token-cap finish হলে fail; timeout বাড়ানো বা cap বাড়িয়ে retry নয়।
অনুমোদনের পর resource preflight ও pinned help inspection-এ প্রয়োজনীয় setting
যাচাই না হলে generation-এর আগেই stop। Server শুধু `127.0.0.1`-এ ephemeral port;
local auth ও restrictive CORS সমর্থিত setting যাচাই করে প্রয়োগ, credentials log নয়।
সব exit path-এ runtime বন্ধ এবং port closure যাচাই বাধ্যতামূলক।

## কম schema overhead ও compact draft contract

Full StoryPlan schema prompt বা response format-এ পাঠানো হবে না। একটিমাত্র ছোট
JSON Schema response constraint থাকবে, `$defs`/বড় descriptions ছাড়া; prompt-এ
শুধু field semantics, story, ছয়টি shot এবং concise text নির্দেশ থাকবে। Schema
দ্বিতীয়বার prompt-এ serialize করা হবে না; full-plan example বা few-shot নয়।
নিচের contract পরবর্তী অনুমোদিত standalone harness-এর specification, এখন code নয়।
সব key required; প্রতিটি object-এ unknown key নিষিদ্ধ, coercion নয়।

| Draft field | অর্থ ও strict সীমা |
| --- | --- |
| `s` | shared setting/background; nonblank string, সর্বোচ্চ 100 characters |
| `m` | mood; nonblank string, সর্বোচ্চ 40 characters |
| `l` | shared lighting; nonblank string, সর্বোচ্চ 60 characters |
| `c` | ১–৩ cast entries, প্রত্যেকটি `{id, name}`; nonblank, যথাক্রমে সর্বোচ্চ 16/40 characters; unique IDs |
| `b` | ঠিক ৬ ordered shot objects; প্রতিটিতে শুধু `a`, `f`, `v`, `c` |
| `b[].a` | distinct story action, সংক্ষিপ্ত clause; nonblank, সর্বোচ্চ 120 characters |
| `b[].f` | camera framing; শুধু `wide`, `medium`, `close-up` |
| `b[].v` | camera movement; শুধু `static`, `pan`, `tracking` |
| `b[].c` | ০–৩ unique visible cast IDs; সবাই top-level cast-এর সদস্য |

Prompt-এর উদ্দেশ্য: JSON ছাড়া অন্য text নয়; নদীতীরের বাজারে courier-এর হারানো
খাতা ফেরত দেওয়ার ছয়টি ধারাবাহিক action, স্পষ্ট শুরু/ফেরত দেওয়া/সমাপ্তি। ছোট
English clauses, shared setting/light, dialogue ছাড়া visual story। এই সীমিত
case-এ style হলো `2D Japanese anime`; style ও dialogue generation মাপা হবে না।
Character limit tokenizer budget নিশ্চয়তা দেয় না। Grammar structural সাহায্য
করলেও strict parser ও cross-field checks আলাদাভাবে লাগবে। Duplicate JSON keys,
nonfinite values, prose/fences/thinking, missing fields ও blank text প্রত্যাখ্যাত।
অসম্পূর্ণ output extract/repair, missing action পূরণ বা অতিরিক্ত shot কাটা নয়।

## Deterministic assembly: কোনটি model, কোনটি harness

শুধু সম্পূর্ণ strict-valid draft assemble হবে। Field mapping স্পষ্টভাবে সংরক্ষিত থাকবে:

- `schema_version=1`; `logline` হুবহু request prompt; `setting=s`, `mood=m`;
  `visual_style` উপরের declared constant; `characters=c`। Logline/style model output নয়।
- Shot order `b`-এর index+1; ID `compact-a-01` … `compact-a-06`;
  duration existing `split_duration(30.0)` থেকে; estimated total request-এর 30.0।
  প্রতিটি shot seed request seed 42; generated seed/ID/timing দাবি নয়।
- `background=s`, `lighting=l`, `action=a`, `camera_framing=f`,
  `camera_movement=v`, `visible_character_ids=b[].c`; cast names ID lookup থেকে।
- Base `image_prompt` নির্দিষ্ট labeled concatenation: style, setting, lighting,
  framing, visible cast names, action; `motion_prompt`: movement, action।
  Field order ও separators harness version-এ স্থির থাকবে; নতুন story text যোগ নয়।
- `negative_prompt=''`, `dialogue=[]`, `reference_inputs=[]`, media paths `null`,
  `status='pending'`, `attempts=0`, `error=null`—ঘোষিত experiment defaults।
- এই A request-এ supplied character profiles নেই। ভবিষ্যতে profiles অনুমোদিত হলে
  existing `inject_character_traits` base prompts-এ একবার এবং পরে validation;
  বর্তমান run-এ trait injection বা Bengali capability পরীক্ষা হয়েছে বলা যাবে না।

শেষে existing `StoryPlan.model_validate` দিয়ে পুরো assembled plan validate করতে
হবে; [contract](contracts/story-plan-v1.md) ও production schema বদলাবে না।
6–10 shots, প্রতিটি 3–6s, contiguous order, unique IDs, valid cast references এবং
sum 30.0 ± 1e-6 পরীক্ষা হবে। Schema pass ও human semantic verdict পৃথক থাকবে।
Standalone harness ছাড়া app/provider/API/DB/UI-তে কোনো wiring বা persistence নয়।

## অনুমোদনের পর procedure ও evidence

1. পুরোনো assets/evidence অক্ষত রেখে আলাদা standalone harness প্রস্তুত; malformed
   JSON, duplicate keys, missing/unknown fields, ভুল shot count/cast reference,
   overlong/blank action rejection এবং valid assembly/duration-এর offline checks।
   এগুলো future execution prerequisite; এই proposal turn-এ harness লেখা/চালানো নয়।
2. Request body, compact schema, prompt, config ও harness hash সংরক্ষণ; historical
   `A-1-request.json` বনাম নতুন request-এর schema/prompt UTF-8 bytes মাপা। Compact
   schema শুধু একবার থাকার check; comparison-এ generation rerun নয়।
3. অনুমোদিত একমাত্র A call; monotonic request start, first token, finish, prompt
   token count/evaluation time, generated tokens/decode time, finish reason, total
   latency, sampled RSS/available RAM/swap এবং raw output সংগ্রহ। Runtime কোনো
   metric না দিলে `unavailable`; অনুমান করে prompt time বা tokens/sec নয়।
4. Draft validate → deterministic assemble → StoryPlan validate → semantic review।
   Raw draft ও assembled plan আলাদা files; failure-এ accepted plan নয়। Report-এ
   model-authored fields বনাম defaults/derived prompts ও rejection reason থাকবে।
5. Runtime shutdown/port closure-এর পরে summary: measured bytes/tokens/time,
   output completeness, resource peaks, strict/semantic verdict এবং সীমাবদ্ধতা।

আগের baseline: 300.02s timeout, 797 characters incomplete output, peak RSS 5.23 GiB,
শেষ logged decode ~2.08 tokens/sec; exact total tokens ও prompt latency নেই।
নতুন run-এর end-to-end speed-এর সঙ্গে ওই decode-only rate তুলনা করে speedup দাবি
নয়। পুরোনো prompt timing অজানা থাকায় overhead reduction-এর সময়গত causal লাভ
নির্ণয় করা যাবে না; schema bytes ও নতুন prompt/decode timings আলাদা report হবে।

## Acceptance ও পরবর্তী সিদ্ধান্ত

এই **এক-case feasibility check PASS** কেবল যদি 300s generation deadline ও সব
resource cap-এর মধ্যে একটি সম্পূর্ণ nontruncated draft এবং validated StoryPlan
পাওয়া যায়; human review-এ ছয়টি relevant distinct action, story order, courier ও
recipient-এর consistent cast, notebook ফেরত দেওয়া এবং সুস্পষ্ট ending থাকতে হবে।
Shared setting/light বা deterministic prompts যেন action-এর সঙ্গে বিরোধ না করে।
প্রতিটি criterion-এর pass/fail ও কারণ লিখতে হবে; schema success একা যথেষ্ট নয়।

PASS হলেও আগের five-case acceptance FAIL মুছে যাবে না; Bengali, dialogue,
45/60s, supplied traits, repair এবং repeatability অমাপা থাকবে। পরের bounded কাজ
হতে পারে পৃথক অনুমোদিত wider test proposal। FAIL হলে কারণভিত্তিক পরবর্তী proposal;
স্বয়ংক্রিয় timeout বৃদ্ধি/model বদল নয়। কোনো ফলেই 3.10 নিজে থেকে শুরু হবে না।

[Phase 3](plan/phase-3.md)-এর 3.9 শর্ত: “download/run করার আগে অনুমতি চাইবে”।
Proposal লেখার সময়ে শুধু documentation অনুমোদিত ছিল। পরবর্তী owner নির্দেশ
“ok porer kaj suru koro” এই এক-call CPU test ও isolated harness প্রস্তুতি/চালানোর
অনুমোদন হিসেবে নথিভুক্ত। B–E, retry, timeout বৃদ্ধি বা 3.10 এর অন্তর্ভুক্ত নয়।

এই turn-এর checks: local document links, RESUME <60 lines, status/scope consistency,
generated plan excerpt drift ও whitespace। ফল RESUME/ledger-এ লেখা থাকবে।
Master requirements বদলায়নি; app tests/model checks পুনরায় চালানোর প্রয়োজন নেই।
