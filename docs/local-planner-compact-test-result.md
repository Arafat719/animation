# Compact isolated planner test — ফল

2026-09-20। **এক-call পরীক্ষা সম্পন্ন: strict JSON/StoryPlan PASS;
semantic acceptance FAIL।** [অনুমোদিত proposal](local-planner-compact-test-proposal.md)।
Owner “ok porer kaj suru koro” বলে proposal-এর পরবর্তী isolated test অনুমোদন করেছেন।
3.10 adapter, retry/repair, B–E বা timeout বৃদ্ধি অনুমোদিত/চালানো হয়নি।

## Execution ও সীমা

আগের verified Qwen3-4B Q4_K_M ও llama.cpp b10964 / b29c606e2 পুনর্ব্যবহার;
[checksum/acquisition evidence](local-planner-smoke-result.md) অপরিবর্তিত। Model
size 2,497,280,256 bytes মিলে গেছে; hash/download পুনরায় করা হয়নি। চার CPU threads,
zero GPU/offload, এক slot, 8192 context; seed 42 ও proposal-এর sampling অপরিবর্তিত।
Reasoning `--reasoning off`; output cap 768; load 180s/generation 300s।

ছোট schema একবার response constraint-এ; full schema prompt-এ নেই। Model শুধু
setting/mood/light/cast ও ছয়টি action/framing/movement/visible-cast দিয়েছে। Harness
ঘোষিত mapping-এ IDs, timing, logline/style, seed, lifecycle defaults এবং prompts
যোগ করে existing StoryPlan validator ব্যবহার করেছে। Production source/API/DB/UI
অপরিবর্তিত; শুধুই ignored standalone harness ও synthetic input।

প্রথম sandbox invocation socket তৈরিতেই বাধাপ্রাপ্ত: তখন model load/generation ০।
অনুমোদিত escalation-এ localhost-only server চলে; এটি generation retry নয়। Ephemeral
API key ও নির্দিষ্ট local origin; unauthenticated `/v1/models` → 401। Credential
সংরক্ষণ হয়নি। Runtime exit 0; connection check ও আলাদা `/proc/net/tcp*` LISTEN
check-এ port বন্ধ।

## মাপা ফল

| Measurement | ফল |
| --- | --- |
| Generation calls / repairs | ১ / ০ |
| Model ready | 4.02s |
| Generation end-to-end | 52.44s; deadline 300s |
| First content | 7.70s |
| Prompt evaluation | 133 tokens; 7.688s |
| Decode | 175 tokens; 44.738s; runtime metric 3.89 tokens/s |
| Total usage | 308 tokens; cached ০ |
| Finish / content | `stop`; 455 characters; truncation ০; reasoning empty |
| Total lifecycle | 56.99s |
| Peak sampled RSS | 5,453,528 KiB ≈ 5.20 GiB |
| Minimum available RAM | 7,756,136 KiB ≈ 7.40 GiB |
| Peak process swap / resource stop | ০ / নেই |
| Experiment directory after run | 2,584,130,781 bytes; 6 GiB cap-এর নিচে |
| Assembled timeline | ছয়টি 5.0s shot; total 30.0s; strict validation PASS |

| UTF-8 size, একই compact serialization | আগের request | Compact request |
| --- | --- | --- |
| Message content (role wrappers ছাড়া) | 4,904 bytes | 465 bytes |
| Response constraint schema | 4,093 bytes | 930 bytes |
| সম্পূর্ণ serialized request | 10,097 bytes | 1,749 bytes |

আগের full-schema call 300.02s-এ অসম্পূর্ণ ছিল; পুরোনো prompt time/token total নেই।
বর্তমান call deadline-এর মধ্যে শেষ হওয়া ও payload ছোট হওয়া মাপা ফল; আলাদা schema,
অনেক ছোট output ও reasoning flag পরিবর্তন হয়েছে বলে schema reduction-এর causal
speedup দাবি নয়। আগের logged ~2.08 decode tokens/s পূর্ণ end-to-end metric নয়।

## Semantic review: কেন acceptance FAIL

Raw actions: `approach` → `stop` → `open` → `handover` → `walk away` → `disappear`।
Cast: courier ও shopkeeper; setting riverside market, mood calm, light golden hour।
এটি Codex-এর criteria-based text review; owner-এর human approval দাবি নয়।

| Proposal criterion | Verdict ও কারণ |
| --- | --- |
| ছয়টি relevant distinct action | FAIL: strings আলাদা, কিন্তু stop/open-এর object/purpose নেই; শেষ দুই shot একই departure প্রসারিত করেছে |
| Story order | FAIL: মোটামুটি approach/handover/departure আছে, কিন্তু open অস্পষ্ট ও return সম্পর্ক অনুল্লিখিত |
| Courier/recipient consistency | FAIL: IDs consistent; shopkeeper-কে notebook owner/recipient হিসেবে প্রতিষ্ঠা করা হয়নি |
| Notebook ফেরত দেওয়া | FAIL: model-এর কোনো field-এ notebook/lost item নেই; handover-এর object/direction নেই |
| সুস্পষ্ট ending | FAIL: departure আছে, কিন্তু সফল return বা recipient response প্রতিষ্ঠিত নয় |
| Shared scene/derived prompt compatibility | PASS: scene/light-এর সরাসরি বিরোধ নেই; assembly missing story বানিয়ে পূরণ করেনি |

Request থেকে copied `logline`-এ notebook আছে; এটি model-এর semantic success নয়।
Derived shot prompts-এও notebook নেই। `plan-schema-validated.json` কেবল schema-valid
candidate, accepted plan নয়; production persistence বা rendering হয়নি।

## Checks, evidence ও next step

- Standalone compile PASS; ৪ offline test methods PASS: valid deterministic assembly,
  timeline, malformed/duplicate/nonfinite JSON (৬ invalid cases), draft structure/
  cast/count/blank/length/type rejection (১৪ invalid cases), schema একবার পাঠানো।
- Model run: JSON/schema/timing/resource checks PASS; semantic acceptance FAIL;
  human acceptance অর্জিত নয়। Runtime cleanup ও independent port check PASS।
- Local document links, RESUME <60 lines, status/scope, plan excerpt drift ও
  whitespace checks PASS। Production code অপরিবর্তিত বলে app tests পুনরায় নয়।

Ignored evidence: `data/planner-smoke/compact-v1/`-এ `contract.py`, `test_contract.py`,
`run_compact.py`, `preflight.json`, `runtime-command.json`, `request.json`,
`schema.json`, `overhead.json`, `server-help.txt`, `server.log`, `events.json`,
`content.txt`, `draft-validated.json`, `plan-schema-validated.json`, `result.json`,
`metrics.json`, `samples.json`, `semantic-review.json`, `cleanup-check.json`।
Exclusive execution marker accidental rerun আটকায়; raw evidence/model সংরক্ষণ করো।

পরবর্তী owner নির্দেশে subject–action–object ও notebook-return সম্পর্ক অক্ষুণ্ণ রাখার
[সংশোধিত proposal](local-planner-semantic-test-proposal.md) সম্পন্ন হয়েছে। নতুন
proposal-এর execution অনুমোদন pending; automatic rerun নয়। Bengali, dialogue, 45/60s, supplied traits, repair ও repeatability অমাপা।
আগের five-case acceptance FAIL এবং Phase 3 real-adapter gate অসম্পূর্ণই আছে;
3.10 শুরু করার অনুমোদন নেই।
