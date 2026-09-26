# Semantic run v1 — offline evidence review

2026-09-21। **অনুমোদিত offline review সম্পন্ন; run/repair/code edit হয়নি।**
Owner-এর পরবর্তী “ok porer kaj suru kor” নির্দেশে [সর্বশেষ failed run](local-planner-semantic-model-test-result.md)
পর্যালোচনা করা হয়েছে। Acceptance FAIL অপরিবর্তিত।

## সিদ্ধান্ত

তিনটি পৃথক সমস্যা আছে: invalid object reference, অর্থহীন scene placeholders এবং
free-text action বনাম structured event mismatch। Reference validator সঠিকভাবে
প্রথম সমস্যায় থেমেছে; অন্য দুটো এখনও narrative review-এর বিষয়। শুধু `:` → `N`
করলে পুরো গল্প সঠিক হয়ে যায়—এমন দাবি করা যাবে না। নতুন model run বা বড় budget
দিয়ে এগুলো সমাধান হবে, তার evidence পাওয়া যায়নি।

## Evidence integrity ও rejection reproduction

`semantic-run-v1/events.json`-এর content deltas জোড়া দিয়ে `content.txt`-এর সঙ্গে
byte-equivalent text equality PASS। Saved request schema এবং existing validator-এর
SCHEMA equality PASS। Original unmodified raw input parse/shape PASS, তারপর
validate-এ আবার **REFERENCE `$.b[4].e.object`** পাওয়া গেছে।

Raw SHA256:
`3ba4c1c736549957647f7f8ffca8e374029856689be909fbe7d3084d5dea05fd`

Object references: `[N, N, N, N, :, N]`; declared object ID `N`। Candidate file নেই।
Stream-এও ভুল value আছে, তাই client concatenation/assembly corruption এই evidence
ব্যাখ্যা করে না। Model/runtime-এর অভ্যন্তরে কেন tokenটি এসেছে তা অজানা। Raw
field পাল্টানো, corrected variant validate করা বা custody check bypass করা হয়নি।

## Reference কেন grammar পেরিয়েছে

Request-এর `b[].e.object` schema: string, minLength=1, maxLength=16। `:` এই shape
মেনে চলে। Schema-তে `o.id`-এর সঙ্গে dynamic equality constraint নেই। Runtime
schema উপেক্ষা করেছে—এই output তা প্রমাণ করে না; কাঠামোগতভাবে এটি বৈধ value।

Existing `validate` সব references পরীক্ষা করে, তারপর case facts ও ordered events
চালায়। তাই পঞ্চম shot-এর ভুল আগে ধরা পড়া প্রত্যাশিত। Custody trace/return/final-holder
বা StoryPlan validation এই output-এর জন্য PASS হয়েছে বলা যাবে না। Error code/path
সংরক্ষণ হয়েছে; validator-এর এই আচরণ bug নয়।

## Narrative findings

| Evidence | মূল্যায়ন ও সীমা |
| --- | --- |
| `s=shared setting`, `m=mood`, `l=lighting` | সব value prompt-এর field-description text-এ আছে; scene content নয়। Label copying-এর সঙ্গে সঙ্গতিপূর্ণ, causal proof নয় |
| Shot 1 action approaches market, event pickup | Approaching-এর মধ্যে notebook নেওয়া ঘোষিত নয়; action/event agreement FAIL |
| Shot 2 courier → vendor transfer | Raw action, event এবং দুই visible participant মেলে; এই local improvement পূর্ণ acceptance নয় |
| Role courier/owner ও notebook lost metadata | আগের ambiguity কিছুটা কমেছে; metadata story demonstration-এর বিকল্প নয় |
| Shot 5 leaves, shot 6 as courier leaves | পুনরাবৃত্ত departure; meaningful ছয়-beat resolution দুর্বল |
| Shot 6-এ courier mention, visible শুধু owner | নামের উল্লেখমাত্র দিয়ে visibility failure নয়; offscreen departure/reference সম্ভব। Shot 1 mismatch-এর মতো নিশ্চিত error-এর সঙ্গে এটি মেশানো হয়নি |

Placeholder exact-match check ভবিষ্যতে পরিচিত junk ধরতে পারে, কিন্তু scene relevance
প্রমাণ করতে পারে না। একইভাবে action/event match সাধারণ keyword test দিয়ে নির্ভরযোগ্য
হয় না: `notebook` লেখা থাকলেও pickup/transfer না-ও ঘটতে পারে। Review boundary রাখতে হবে।

## কী পরিবর্তন ন্যায্য, কী এখনো hypothesis

| সম্ভাব্য পথ | Evidence-ভিত্তিক মূল্যায়ন |
| --- | --- |
| Original failure regression fixture রাখা | এখনই পরের bounded offline কাজ হিসেবে উপযোগী; stable rejection ও narrative boundary রক্ষা করবে |
| একমাত্র object-এর ID fixed enum/implicit করা | Invalid-reference class কমাতে পারে; contract ও experiment বদলাবে। Placeholder/action mismatch সমাধান নয়; এখন implementation নয় |
| Field descriptions বদলানো বা placeholder নিষেধ | Copying hypothesis পরীক্ষা করতে পারে; একটি output থেকে সাফল্য অনুমান নয় |
| Structured events থেকে action sentence বানানো | Text-event divergence কমতে পারে, কিন্তু narrative model-authored থাকবে না; নতুন design/provenance সিদ্ধান্ত দরকার |
| Timeout/token cap বৃদ্ধি | এই output stop finish/395 tokens/222.91s; budget exhaustion নয়। এখন evidence-based next step নয় |

চারবারের পৃথক configuration-এ failure মানে সব local model বা এই model-এর সব
configuration অসমর্থ প্রমাণ নয়। আবার schema/validator যোগ হয়েছে বলেই model quality
উন্নত হয়েছে এমনও নয়। Success-rate, বাংলা দক্ষতা, broader-case capability অমাপা।

## নির্দিষ্ট পরের bounded কাজ

নতুন run proposal-এর আগে existing offline suite-এ **এই failure-এর regression fixture
ও diagnostic review record** যোগ করা:

1. Exact raw bytes নতুন legacy fixture হিসেবে copy; origin/model-run path/hash retain;
   expected `REFERENCE`/`$.b[4].e.object`, candidate absent। Sanitized repair নয়।
2. Stream reconstruction equality ও request-schema equality evidence retain; পুরোনো
   positive/negative expectations অপরিবর্তিত।
3. Same raw-এর placeholder values ও shot 1 mismatch reviewer evidence-এ FAIL হিসেবে
   রাখবে; test শুধু evidence association যাচাই করবে, automatic semantic understanding
   দাবি নয়। Empty/default scenario দিয়ে false PASS নয়।

এটি validator policy change বা contract redesign নয়; model failure থেকে বাস্তব
regression coverage যোগ করার একটি offline micro-step। Owner-এর পরবর্তী নির্দেশে
[implementation সম্পন্ন](local-planner-failure-regression-result.md)।
সেই implementation শেষে প্রয়োজন হলে পৃথক contract/run design review; automatic
model call, prompt retry, timeout বৃদ্ধি বা 3.10 adapter নয়।

## Checks ও recovery

Offline checks: stream/raw equality, schema equality, original rejection reproduction,
raw hash, candidate absence এবং field-label comparison সম্পন্ন। Document links,
RESUME size, scope/status, plan drift ও whitespace PASS। App tests/model run নয়।
Production/master/validator/harness/raw evidence অপরিবর্তিত; commit হয়নি।
[Offline contract](local-planner-semantic-contract-result.md)-এর পূর্বের PASS ও
model experiments-এর FAIL নিজ নিজ সীমায় বহাল; Phase 3 gate অসম্পূর্ণ।
