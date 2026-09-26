# Contract/run design review — পরবর্তী সিদ্ধান্ত

2026-09-21। **অনুমোদিত design review সম্পন্ন; implementation/run নয়।**
[Regression checkpoint](local-planner-failure-regression-result.md) ও
[raw evidence review](local-planner-semantic-run-review.md) এই সিদ্ধান্তের ভিত্তি।

## সিদ্ধান্ত

পরের bounded কাজ হবে **isolated request-bound draft policy-এর offline implementation**।
একটি নতুন experimental wrapper-এ single notebook ID request থেকে নির্দিষ্ট করা এবং
পরিচিত field-description placeholders প্রত্যাখ্যান করা হবে। Existing semantic
contract/custody checks ও raw-action assembly বহাল থাকবে। এখন আরেক model run নয়।

এটি known invalid output তৈরি হওয়ার সুযোগ কমানো ও early rejection-এর কাজ;
model-কে coherent গল্প লিখতে শেখানোর সমাধান নয়। Narrative mismatch এখনও পৃথক
review-এ FAIL/UNRESOLVED হবে। এই সীমা থাকতেই পরবর্তী run design মূল্যায়ন করতে হবে।

## বিকল্পের তুলনা

| বিকল্প | কী মাপে/সারে | সিদ্ধান্ত |
| --- | --- | --- |
| Request-bound object ID | `:`-এর মতো unknown object generation constraint-এ বাদ দেওয়ার সুযোগ | Offline wrapper-এ নির্বাচন; runtime grammar support এখনো অমাপা |
| Known-placeholder rejection | `shared setting`, `mood`, `lighting`-এর হুবহু পুনরাবৃত্তি reject | Narrow deterministic check; generic scene relevance নয় |
| শুধু wording পরিবর্তন | Label copying কমে কি না | Future run-এ পৃথক hypothesis; এখন কার্যকারিতা দাবি নয় |
| Events থেকে action sentence তৈরি | Text/event divergence কিছুটা নির্মাণগতভাবে কমায় | এখন নির্বাচন নয়; generated story prose-এর ownership বদলে যায় |
| Budget/model পরিবর্তন | অন্য performance/capability পরীক্ষা | Current stop/395 tokens/222.91s budget-এর মধ্যে; এখন evidence নেই |

## নির্বাচিত offline policy: exact specification

নতুন ignored `data/planner-smoke/request-bound-policy-v1/`-এ wrapper, tests ও
synthetic fixtures। Existing `semantic-contract-v1/`, তার 28 fixtures, model-run
raw files ও L3 review অক্ষত থাকবে। Production StoryPlan/schema/master বদলাবে না।

1. Fixed synthetic case A-এর request metadata-তে `object_id='notebook'`। এটি opaque
   identifier normalization, story action নয়। Model output-এ `o.id` ও প্রতিটি
   `b[].e.object` হুবহু এই ID হতে হবে। Shape-এর string bounds রেখে ওই দুই schema
   location-এ `const='notebook'` যোগ; cast IDs/model roles/events অন্যথায় unchanged।
   একটি shared ID schema object in-place mutate নয়—deep copy ও targeted locations।
2. Existing strict parsing/shape আগে; তারপর request-bound equality check। Mismatch
   হলে `REQUEST_OBJECT` ও নির্দিষ্ট field path; missing key হলে পুরোনো `SHAPE`।
   Static schema constraint ছাড়াও Python check বাধ্যতামূলক, runtime grammar নয়।
3. ওই check-এর পরে known-placeholder policy: `s`-এ `shared setting`, `m`-এ `mood`,
   `l`-এ `lighting` হলে `PLACEHOLDER` ও field path। Detection-এ casefold ব্যবহার;
   existing shape আগে হওয়ায় padding/blank আগে reject হবে। শুধু নিজ field-এর exact
   phrase; `lighting` শব্দযুক্ত বাস্তব scene phrase substring দিয়ে reject নয়।
   Stored raw text কখনও normalize/rewrite হবে না।
4. তার পরে unchanged semantic `candidate(raw)`—roles/references/custody/visibility/
   return এবং StoryPlan assembly। Success এখনও **REVIEW_REQUIRED**, semantic PASS নয়।
   Error precedence: SHAPE → REQUEST_OBJECT → PLACEHOLDER → existing semantic stages।

এই experiment-এর ID convention বদলাবে; পুরোনো correct ID `N` বা synthetic `book`
new wrapper-এ reject হওয়া ইচ্ছাকৃত compatibility সীমা। Old contract এখনও সেগুলো
নিজস্ব নিয়মে process করে; saved raw automatically migrate/repair নয়। Model-এর
owner/holder/actor সিদ্ধান্ত request থেকে hard-code হবে না।

## Offline acceptance matrix

| Case | Expected |
| --- | --- |
| নতুন synthetic fixture-তে সব object ID `notebook`, concrete scene, valid events | REVIEW_REQUIRED + unchanged StoryPlan projection |
| `o.id` wrong / এক shot object wrong (পৃথক variants) | REQUEST_OBJECT + correct path |
| Missing object field | SHAPE; wrapper exception নয় |
| নিজ field-এর তিন exact placeholders, case variants | PLACEHOLDER; raw text অপরিবর্তিত |
| Concrete `warm afternoon lighting`, `quiet riverside market` | Placeholder policy pass; full candidate যথারীতি validate |
| IDs/scene ঠিক কিন্তু reversed transfer narrative | REVIEW_REQUIRED → textual FAIL; automatic acceptance নয় |
| একই input-এ object ও placeholder faults | REQUEST_OBJECT আগে; stable precedence |
| Old raw L3 unchanged | Old suite-এ REFERENCE; new wrapper-এ প্রথম request ID mismatch; source hash অক্ষত |

নতুন fixture source স্পষ্ট `synthetic_fixture`; baseline-এর semantic facts রেখে ID
convention মানানো synthetic construction, real output repair নয়। V1 suite ফল ও
new-policy suite পৃথক report। Targeted tests-এ old SCHEMA mutation হয়নি, input
immutability, error path/order এবং candidate assembly-before-rejection না হওয়া লাগবে।
নতুন schema/request UTF-8 size মাপবে; tokenizer/model/network নয়।

## Model-authored বনাম derived content

| তথ্য | উৎস/দায়িত্ব |
| --- | --- |
| Request/story/30s/style/object ID convention | Caller/harness; model quality credit নয় |
| Cast names/roles, owner/initial holder, events ও ছয় action sentences | Model output; independent cross-field/text review লাগবে |
| Durations/order/shot IDs/seed/state/defaults | Deterministic assembly; story planning success নয় |
| Image/motion prompt concatenation | Model fields থেকে derived; নতুন action/participant যোগ নয় |
| Future event-to-text template, যদি কখনও নির্বাচিত হয় | Generated template prose বলে label করতে হবে; model-authored sentence বলা যাবে না |

Action/event mismatch ঢাকতে event থেকে missing pickup বাক্য লেখা হবে না। Shape,
request facts, custody ও narrative correctness report-এ পৃথক থাকতে হবে।

## Future run-এর design boundary

Offline implementation PASS হলেই model run শুরু নয়। তখন একটি exact request/run
proposal লাগবে: নতুন schema, request-bound ID instruction, concrete scene values
চাওয়ার prompt, one-call budget এবং raw narrative rubric। Positive six-shot fixture
few-shot হিসেবে পাঠানো default নয়; answer leakage/generalization সীমা আলাদা review।

একই pinned model/runtime, 768-token/300s ceiling ধরে planning হবে; নতুন measured
prompt/schema overhead অনুযায়ী cap-এর মধ্যে পরীক্ষা অর্থবহ কি না জানাতে হবে। এই
review runtime grammar-এর `const` support যাচাই করেনি; unsupported হলে future
run setup stop, schema silently weaken নয়। Asset/download/run অনুমোদন নেই।

Run-এর success criteria আগের চেয়ে শিথিল নয়: request-bound IDs ও concrete scene,
role/custody consistency, action/event agreement, ছয় relevant beat, return/resolution
এবং cleanup/resource checks। এক sample-এ factual improvement দেখা যেতে পারে;
কোন পরিবর্তনের causal অবদান বা general quality আলাদা করে প্রমাণ হবে না।

আরও narrative failure হলে automatic prompt/contract loop নয়: existing evidence
দিয়ে এই model+CPU path চালিয়ে যাওয়ার উপযোগিতা owner review-এ আনতে হবে। Rejection
coverage বাড়ানোকে product progress বা real planner gate PASS হিসেবে দেখানো যাবে না।

## Completion ও next step

এই turn documentation-only design decision; code/fixtures/runtime/model অপরিবর্তিত।
Document links, RESUME <60 lines, scope/status, plan drift ও whitespace checks PASS।
আগের ৯ tests/28 fixtures baseline পুনর্ব্যবহার; app/model tests চালানো হয়নি।

পরবর্তী bounded কাজ: উপরের request-bound draft policy-এর isolated offline wrapper,
fixtures ও checks implementation owner-এর পরবর্তী নির্দেশে
[সম্পন্ন](local-planner-request-bound-policy-result.md)। Model run/3.10/new phase নয়।
