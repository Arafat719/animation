# Compact planner — offline failure analysis

2026-09-20। **অনুমোদিত analysis সম্পন্ন; model run/implementation হয়নি।**
Owner-এর “ok porer kaj suru koro” নির্দেশে ঘোষিত next step কার্যকর।
[V1 ফল](local-planner-compact-test-result.md) ও [V2 ফল](local-planner-semantic-test-result.md)
দুটির semantic FAIL অপরিবর্তিত।

## সিদ্ধান্ত

প্রমাণিত ঘাটতি হলো **semantic তথ্য ও cross-field validation-এর অভাব**।
Compact schema শুধু action string ও visible cast IDs নেয়; courier/owner role,
notebook ownership, possession ও transfer participants আলাদা structured facts নয়।
তাই valid JSON/StoryPlan পাওয়া মানে prompt-এর গল্প সঠিক হওয়া নয়।

V2 prompt পূর্ণ action sentences এনেছে, কিন্তু role ও cast consistency নিশ্চিত
করেনি। আরও timeout/token budget বা আরেক wording সফল হবে—বর্তমান evidence তা বলে না।
Model কেন internally ভুল করেছে নির্ণয় হয়নি; এই report observable failure ও
validation gap চিহ্নিত করে, model capability-এর চূড়ান্ত সীমা নয়।

## Evidence ও reproduction

শুধু existing `compact-v1/` ও `compact-v2/` content/request/result/metrics,
contract/assembly এবং production StoryPlan source দেখা হয়েছে। Offline Python
inspection-এ দুই raw output parse/assemble করে saved candidate-এর সঙ্গে equality
যাচাই করা হয়েছে। Model/runtime load, network call বা evidence overwrite হয়নি।

| Check | V1 | V2 |
| --- | --- | --- |
| Raw draft → saved candidate equality | PASS | PASS |
| Raw action → assembled action হুবহু | PASS | PASS |
| Finish / generated tokens | stop / 175 | stop / 336 |
| সর্বোচ্চ action length | 9 characters | 48 characters |
| Action/output cap | 120 chars / 768 tokens | 120 chars / 768 tokens |
| Resource stop | নেই | নেই |

দুই request-এ system message ছাড়া equality PASS। ফলে assembly truncation,
missing streamed tail বা cap exhaustion এই দুই failure-এর observed কারণ নয়।
তবু দুই sample থেকে prompt-এর causal effect বা success rate মাপা যায় না।

Raw content SHA256 (ছোট text files; model পুনরায় hash নয়):
- V1: `98dd08ddfb3b7a472bddd16b25524a40212a6d079dd52df103b00e4d0136b9a6`
- V2: `518f4e380a495b36f901fe23f6fde1ecbba07e6ee5d22e30a799e7e320b76af7`

## কোথায় কী হারিয়েছে

| স্তর | Evidence | সিদ্ধান্ত |
| --- | --- | --- |
| V1 generation | `open`, `handover`; কোনো action-এ notebook নেই | Model content অপর্যাপ্ত; grammar nonblank string মেনে নিয়েছে |
| V2 role | Cast শুধু Rina/Takumi/Aiko নাম; courier/owner পরিচয় নেই | Finder Rina-কে owner ধরে নেওয়া যাবে না; role prompt থেকে অনুমান করতে হচ্ছে |
| V2 possession | 1-এ Rina finds; 2/4-এ Takumi checks/opens | সংযোগ অনুল্লিখিত; physical impossibility প্রমাণ নয়, continuity অস্পষ্ট |
| V2 transfer | 6: Takumi hands notebook back to Rina; visible IDs শুধু `1` (Rina) | এই proposal-এর transfer-visibility criterion ভাঙে; known-ID check এটি ধরতে পারে না |
| V2 story relevance | Seal/missing pages/showing pages | Owner শনাক্তকরণে সম্পর্ক প্রতিষ্ঠিত নয়; missing-pages detail অসম্পূর্ণ |
| Assembly | Saved candidates হুবহু পুনর্গঠিত | Harness নতুন অর্থ হারায়নি; input-এর ঘাটতি faithfully বহন করেছে |
| Copied logline | Original prompt-এ courier/return আছে | Model-authored evidence নয়; shot-এর ভুল সারায় না |

Shot 5-এ Rina-র উল্লেখ আছে কিন্তু visible cast-এ নেই—এটি একা error নয়: অন্য কাউকে
নিয়ে কথা বলা যায়। Shot 6-এ Takumi সক্রিয় physical transfer actor; proposal সেখানে
দুই participant দৃশ্যমান চেয়েছে। সব mentioned name-কে visible করা ভুল heuristic।
একইভাবে cut-এর মধ্যে প্রতিটি mundane movement দেখানো বাধ্যতামূলক নয়; possession
ambiguity-কে সরাসরি contradiction বলা উচিত নয়। Role/transfer gap-ই যথেষ্ট fail evidence।

## কেন বর্তমান checks pass করেছে

[StoryPlan source](../animation_studio/domain/v1/story_plan.py)-এ text bounds,
unique IDs, contiguous order, duration sum ও references cast-এ আছে কি না যাচাই হয়।
Action text-এর semantic subject বা object-owner relation পরীক্ষা হয় না। Compact
`contract.py`-তেও একই সীমা: `b[].c` known IDs-এর subset, `a` nonblank bounded string।
এই validators তাদের বর্তমান structural contract অনুযায়ী কাজ করেছে; parser bug নয়।

Offline in-memory diagnostic mutations; কোনো model output বদলে save করা হয়নি:

| V2 shot 6-এ diagnostic পরিবর্তন | বর্তমান validator-এর ফল | অর্থ |
| --- | --- | --- |
| Visible cast `[]` | STRUCTURAL_ACCEPT | Action participant-এর উপস্থিতি enforce হয় না |
| Visible cast `['unknown']` | STRUCTURAL_REJECT | Referential integrity কাজ করছে |
| Action `Takumi watches clouds.` | STRUCTURAL_ACCEPT | Request/story relevance enforce হয় না |

এগুলো semantic correctness-এর নতুন automated test suite নয়; validator boundary
যাচাইয়ের ক্ষুদ্র probes। চার existing contract test methods মূলত syntax/shape,
references, assembly ও timing পরীক্ষা করে। Synthetic semantic negatives আগে
textual review হয়েছে; code সেগুলো semantic error হিসেবে detect করে—এমন দাবি নেই।

## পরবর্তী পরিবর্তনের ভিত্তি

আরেক prompt-only run-এর আগে **isolated semantic contract ও offline negative
fixtures-এর proposal** প্রস্তুত করাই পরের bounded কাজ। প্রস্তাবের নকশায় বিবেচ্য:

| Needed fact/check | নির্দিষ্ট উদ্দেশ্য ও সীমা |
| --- | --- |
| Cast role → character ID | Model courier/owner কাকে বলছে স্পষ্ট করা; names থেকে role অনুমান নয় |
| Object ID ও owner ID | Notebook-এর ownership স্থির রাখা; owner ও current holder আলাদা |
| Event actor/object/from/to references | Transfer-এর দিক ও participants যাচাই; unknown ID reject |
| Explicit custody transitions | যেটুকু ownership/possession ঘোষণা করে, তার contradiction ধরা; gap-এ story বানানো নয় |
| Event participants বনাম visible IDs | Onscreen physical action-এ participant requirement; mere mention/offscreen speech আলাদা |
| Narrative বনাম structured facts | Metadata ঠিক কিন্তু action text উল্টো হলে reject/review; schema alone যথেষ্ট নয় |

এগুলো এখন design candidates, নতুন production requirements বা implemented contract
নয়। Event vocabulary কতটা সীমিত হবে, free-text ambiguity কীভাবে review হবে,
metadata থেকে prompts তৈরি করলে model-authored planning কতটুকু থাকবে—পরবর্তী
proposal-এ সিদ্ধান্ত লাগবে। Model-এর তৈরি metadata নিজেই মিথ্যা/অসংগত হতে পারে।

Offline fixtures-এ অন্তত missing role, unknown participant, reversed transfer,
owner/holder confusion, contradictory custody, absent onscreen actor, এবং valid
mention-only/offscreen case থাকতে হবে। Positive fixture ও semantic negative
আলাদা; হাতে লেখা fixture-কে model success বলা যাবে না। Existing raw outputs
negative evidence হিসেবে থাকবে, fabricated fields দিয়ে pass করানো যাবে না।

আরও fields token overhead বাড়াবে; পূর্ণ StoryPlan schema আবার পাঠানো বা cap বৃদ্ধি
স্বয়ংক্রিয় সিদ্ধান্ত নয়। প্রথমে contract/fixture review, পরে প্রয়োজন হলে আলাদা
bounded run proposal। এই analysis কোনো নতুন model run অনুমোদন করে না।

## Completion, checks ও authorization

Offline reproduction: দুই saved assembly equality, action preservation, request
comparison ও তিন validator probes সম্পন্ন। Document links, RESUME <60 lines,
status/scope, plan drift ও whitespace checks PASS। App tests/model benchmark নয়।
Production code, harness, raw evidence, master requirements অপরিবর্তিত; commit হয়নি।

পরের bounded কাজ: উপরের evidence-ভিত্তিক isolated semantic contract/negative-fixture
[proposal](local-planner-semantic-contract-proposal.md) owner-এর পরবর্তী নির্দেশে সম্পন্ন।
পরবর্তী offline implementation অনুমোদন pending। Model download/run, 3.10 adapter ও নতুন phase
অনুমোদিত নয়। বর্তমান mock flow চালু; Phase 3 real-adapter gate অসম্পূর্ণ।
