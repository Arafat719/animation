# Isolated semantic contract ও negative-fixture proposal

2026-09-20: proposal সম্পন্ন। Owner-এর পরবর্তী নির্দেশে offline implementation
2026-09-21-এ সম্পন্ন: [ফল](local-planner-semantic-contract-result.md)। Model run হয়নি।
Owner-এর পরবর্তী নির্দেশে [offline analysis](local-planner-offline-failure-analysis.md)
থেকে এই bounded design তৈরি। এটি Phase 3.9 experiment-এর offline প্রস্তুতি;
production StoryPlan বা master requirements বদলানো নয়।

## নির্দিষ্ট সিদ্ধান্ত ও scope

নতুন standalone `semantic-draft-v1`-এ explicit role, একটি notebook-এর owner/current
holder এবং প্রতি shot-এর একটি event থাকবে। Deterministic checks কেবল ঘোষিত facts-এর
consistency পরীক্ষা করবে; free-text-এর সত্যতা বা গল্পের quality প্রমাণ করবে না।
পরের micro-step হবে **offline contract validator ও fixtures implementation**;
কোনো model/server/download/network call নয়। Model-run proposal তার পরের পৃথক কাজ।

প্রস্তাবিত স্থান: ignored `data/planner-smoke/semantic-contract-v1/`। সেখানে
`contract.py`, `test_contract.py`, `fixtures/`, `checks.json` ও reviewer evidence।
`compact-v1/`, `compact-v2/`, production source/API/DB/UI অপরিবর্তিত থাকবে।

## Draft shape ও structural rules

সব object-এ unknown field নিষিদ্ধ, সব নিচের field required, coercion নয়। Duplicate
JSON key, nonfinite number, blank/whitespace-only text, invalid enum reject। Text
trim করে semantic fact বদলানো বা missing field default দিয়ে পূরণ নয়।

| Field | Contract |
| --- | --- |
| `version` | strict integer `1`; boolean/float নয় |
| `s,m,l` | shared setting/mood/light, আগের nonblank string bounds 100/40/60 characters |
| `c` | 2–3 entries `{id,name,role}`; unique ID ও unique name; ID ≤16, name ≤40 characters |
| `c[].role` | `courier`, `owner`, `other`; ঠিক একজন courier ও একজন owner, distinct IDs |
| `o` | একটি object `{id,label,owner,holder,lost}`; ID ≤16, label nonblank ≤40; owner/holder cast reference, holder nullable; lost strict boolean |
| `b` | ঠিক ছয় ordered shots; array position-ই order |
| `b[]` | আগের `a,f,v,c` এবং নতুন `e`; action ≤120 characters; framing/movement enums অপরিবর্তিত; visible IDs unique, 0–3, known cast |
| `b[].e` | `{kind,actor,object,from,to,presentation}`; actor known cast ID; object হুবহু `o.id`; from/to nullable cast IDs |
| `kind` | `observe`, `pickup`, `inspect`, `transfer`, `gesture`, `mention` |
| `presentation` | `onscreen` বা `offscreen`; নিচের event rules অনুযায়ী |

ID/name-এর আগে-পরে whitespace reject; IDs case-sensitive। Object ও cast ID একই
namespace নয়; references field-এর namespace অনুযায়ী validate হবে। Name uniqueness
শুধু এই ক্ষুদ্র experiment-এর unambiguous review-এর সীমা, production policy নয়।

Fixed synthetic request A-এর case-specific preconditions: `o.label='notebook'`,
`o.lost=true`, `o.owner` role=owner, initial holder role=owner হতে পারবে না; null,
courier বা other হতে পারে। Ownership কখনও custody transfer-এ বদলাবে না। এই checks
user request A-এর facts enforce করে; arbitrary story validator দাবি নয়।

## Event ও custody semantics

`holder` শুরু হবে `o.holder` থেকে; null মানে এই bounded contract-এ **unheld**,
unknown নয়। প্রত্যেক event validate করে তবেই state update; failure-এ আর assembly নয়।
কোনো cut-এর আড়ালে implied transfer যোগ নয়। Abstract event একটি shot-এর মূল action;
এক shot-এ একাধিক custody change এই version-এ unsupported।

| Kind | from/to ও precondition | Visibility ও state effect |
| --- | --- | --- |
| observe | from=null, to=null | actor onscreen; custody অপরিবর্তিত; দূর থেকে দেখা যায় |
| pickup | from=null, to=actor; holder=null | actor onscreen; holder=actor |
| inspect | from=null, to=null; holder=actor | actor onscreen; custody অপরিবর্তিত; handling inspection |
| transfer | from=actor=holder; to known, nonnull ও actor থেকে ভিন্ন | onscreen; actor ও recipient দুজন visible; holder=to |
| gesture | from=null, to=null | actor onscreen; custody অপরিবর্তিত; gesture দিয়ে hidden transfer নয় |
| mention | from=null, to=null | custody অপরিবর্তিত; onscreen হলে actor visible, offscreen হলে actor visible নয় |

সব physical event-এর presentation=onscreen। Mention-এ text-এ অন্য কারও নাম থাকলেই
তাকে visible লাগবে না। Offscreen mention একটি ঘোষিত narrative/reference fixture;
এই step-এ dialogue track বা audio তৈরি নয়। Inspect এখানে হাতে থাকা বস্তু পরীক্ষা;
দূর থেকে অন্যের বই দেখা চাইলে observe। এই ছোট vocabulary-র সীমা explicit।

Case A-তে অন্তত একটি `transfer` courier → owner হতে হবে এবং শেষে holder=owner।
Return-এর পরও অন্য transfer হলে একই preconditions লাগবে; শেষে ভুল holder reject।
Model বাস্তবে lost item বোঝাল কি না বা transfer text event-এর সঙ্গে মেলে কি না
আলাদা review। Rules মেলাতে narration বদলানো/অদৃশ্য participant ঢোকানো নয়।

## Validation ফল ও deterministic assembly

Validation order: strict parsing/shape → identities/roles/references → initial
case facts → ordered events/custody → return/final holder। Error-এ stable code ও
field/shot path থাকবে। Core codes: `SHAPE`, `ROLE`, `REFERENCE`, `CASE_FACT`,
`EVENT_FIELDS`, `CUSTODY`, `VISIBILITY`, `RETURN_REQUIRED`, `FINAL_HOLDER`।
এক fixture-এ এক targeted semantic fault; multiple fault থাকলে প্রথম validation
layer-এর error primary, পরে অনুমান করে অন্য stage চালানো নয়।

এই checks PASS হলে ফল **REVIEW_REQUIRED**, automatic semantic PASS নয়। তারপর
আগের deterministic StoryPlan mapping ব্যবহার করা যাবে: raw `a` action-এ হুবহু,
image/motion prompt আগের labeled concatenation, fixed style/seed/timeline/defaults।
`c` থেকে কেবল id/name StoryPlan-এ; roles/object/events আলাদা evidence sidecar-এ,
production schema-তে extras ঢোকানো নয়। ছয়টি 5.0s shot; StoryPlan validation আবার
বাধ্যতামূলক। Saved file শুধু `candidate`, accepted নয়।

Reviewer raw actions ও structured facts মিলিয়ে পরীক্ষা করবে: actor/object/recipient,
role/ownership establishment, custody continuity, ছয় relevant beat, resolution ও
visible cast। Verdict `PASS`, `FAIL` বা `UNRESOLVED`; শেষটি accepted নয়। Reviewer
identity ও shot evidence বাধ্যতামূলক; Codex review owner human approval নয়।
Metadata সঠিক কিন্তু text-এ reversed transfer থাকলে automated facts PASS হলেও
review FAIL। Unrelated text-এ notebook keyword বসানো success নয়। Free-text থেকে
regex/name matching দিয়ে general semantic verdict বানানো হবে না।

## Offline fixtures: concrete baseline ও expected outcomes

সব handcrafted fixture-এ `origin=synthetic_fixture` manifest; model-generated দাবি
নয়। একটি baseline: C=Courier (courier), O=Owner (owner); notebook owner O, initial
holder null, lost true। Scene riverside market; daylight; calm। Valid narrative:

| Shot | Event/visible | Hand-authored action |
| --- | --- | --- |
| 1 | pickup C → C from null; visible C | Courier picks up a lost notebook beside the market stalls. |
| 2 | inspect C; visible C | Courier checks the notebook for its owner's name. |
| 3 | mention O onscreen; visible C,O | Owner identifies the lost notebook as their own. |
| 4 | gesture C; visible C,O | Courier signals to Owner while holding the notebook. |
| 5 | transfer C → O; visible C,O | Courier returns the notebook to Owner at the stall. |
| 6 | gesture O; visible C,O | Owner thanks Courier while holding the returned notebook. |

Baseline expected automated REVIEW_REQUIRED, textual fixture review PASS। Text review
পূর্বলিখিত oracle; automated natural-language detector তৈরি হয়েছে বলা যাবে না।
এই sample model prompt-এ few-shot হিসেবে পাঠানোর অনুমোদন নেই।

| Fixture | Baseline থেকে পরিবর্তন | Expected |
| --- | --- | --- |
| P1 | Baseline unchanged | REVIEW_REQUIRED; fixture review PASS |
| P2 | Shot 3 text: `Owner tells Courier that the lost notebook belongs to Owner.`; visible শুধু O | REVIEW_REQUIRED; mere mention target absent বৈধ |
| P3 | Shot 3 offscreen mention O, visible শুধু C; narrative speaker O | REVIEW_REQUIRED; offscreen voice/reference বৈধ, audio নয় |
| N1 | Owner role missing বা courier/owner একই ID (পৃথক variants) | ROLE বা duplicate-ID SHAPE |
| N2 | Event actor/object/from/to/visible-এ unknown reference (পৃথক variants) | REFERENCE |
| N3 | Object owner=C অথবা initial holder=O (পৃথক variants) | CASE_FACT |
| N4 | Shot 5 actor=from=O, to=C, visible C,O; holder=C | CUSTODY |
| N5 | Shot 5 recipient=actor | EVENT_FIELDS |
| N6 | Shot 1 pickup-এর initial holder=C | CUSTODY |
| N7 | Shot 2 inspector=O, visible O, কিন্তু holder=C | CUSTODY |
| N8 | Shot 5 visible শুধু O; পরে শুধু C (পৃথক variants) | VISIBILITY |
| N9 | Physical transfer offscreen | EVENT_FIELDS |
| N10 | Mention-এর from/to দিয়ে holder বদলানোর চেষ্টা | EVENT_FIELDS |
| N11 | Initial holder=other X; X→O return, courier-এর transfer নেই | RETURN_REQUIRED; hand-authored independent coherent event sequence |
| N12 | C→O return-এর পরে O→C, শেষে holder=C | FINAL_HOLDER; shot 6-এ valid transfer বসবে |
| R1 | Metadata ঠিক, shot 5 text `Owner hands the notebook to Courier.` | REVIEW_REQUIRED → textual FAIL |
| R2 | Metadata ঠিক, shot 5 শুধু notebook দেখার text | REVIEW_REQUIRED → textual FAIL |
| R3 | Role metadata ঠিক, narration role/ownership অস্পষ্ট | REVIEW_REQUIRED → textual FAIL/UNRESOLVED; accepted নয় |
| L1/L2 | Original compact-v1/v2 raw text হুবহু | নতুন contract SHAPE reject; পুরোনো semantic FAIL evidence অক্ষত |

N11-তে ঠিক ছয় events: X observe, X inspect, C gesture, X→O transfer, O inspect,
O gesture; initial holder X, notebook owner O; সব actors প্রয়োজনমতো visible। একমাত্র
target failure courier→owner return অনুপস্থিত। Missing fields fabricate করে legacy
outputs upgrade করা যাবে না। Generic parse tests-এ duplicate keys, blank/overlong
text, nonfinite/boolean coercion, unknown fields, shot count ও enums থাকবে।

## পরের bounded implementation-এর pass check

Isolated validator, synthetic fixtures ও test runner; নতুন dependency install নয়।
সব positive/negative expected outcome, deterministic custody trace, input immutability,
strict StoryPlan candidate mapping এবং REVIEW_REQUIRED boundary পরীক্ষা করবে।
Review-only fixture outcomes আলাদা manual-oracle evidence; unit-test pass মানে
semantic interpretation automated হয়েছে নয়। Full pytest/app suite প্রয়োজন নেই।

শুধু নতুন schema/example payload-এর UTF-8 size মাপবে ও v2-এর 930-byte schema/
2,485-byte request-এর পাশে report করবে। Model tokenizer/load নয়; নতুন token cost
unmeasured থাকবে। আগে থেকে 768-token/300s model budget বাড়ানোর সিদ্ধান্ত নয়।
Offline pass-ও model success নয়; পরে পৃথক model-run proposal-এর আগে output overhead
ও এই narrow vocabulary-র usefulness review করতে হবে।

## বর্তমান completion ও অনুমোদন

এই turn শুধু documentation; contract code/fixtures লেখা বা model run হয়নি।
Document links, RESUME size, status/scope, plan excerpt drift ও whitespace checks
PASS; production/master/harness/raw evidence অপরিবর্তিত।
উপরের **offline validator + fixture implementation** পরে অনুমোদিত ও সম্পন্ন হয়েছে।
একই অনুমোদন model run, 3.10 adapter বা নতুন phase চালুর অনুমোদন হবে না।
