# 5.7i — reviewed extraction save/provenance design

2026-10-12। Owner next-work নির্দেশে documentation-only review সম্পন্ন।
[5.7h checkpoint](character-extraction-contract-checkpoint.md)-এর next scope অনুসৃত।
এটি proposed design; নিচের v2 schema/table/API এখনও implemented নয়।

## Existing evidence ও সিদ্ধান্ত

[Extraction contract](../animation_studio/domain/v1/character_extraction.py) report-এ
request/hash, candidate evidence, configured provider identity/is_mock এবং missing traits
রাখে। [Manual store](../animation_studio/persistence/character_profiles.py) ও
[migration 0005](../animation_studio/persistence/migrations/versions/0005_character_profiles.py)
character_id primary key, schema_version=1 CHECK ও no-update trigger রাখে। Existing
CharacterProfileDraft.source কেবল user_provided; adapter-ও saved schema v1 চায়।

তাই reviewed model/fixture candidate-কে v1 source=user_provided বানিয়ে save নয়।
পৃথক v2 reviewed values + provenance envelope হবে; v1 rows rewrite নয়। একটি character-এর
একটিই authoritative immutable profile থাকবে, manual ও reviewed দুইটি পাশাপাশি নয়।

## Review decision: প্রথম bounded pure contract

Proposed `ExtractionReviewDecision`-এ full report hash, character_id, explicit
confirmed Literal[True] (raw bool type check), এবং সাতটি trait field-এর decision থাকবে।
`report_hash` পুরো validated ExtractionReport-এর canonical sorted-key compact UTF-8
JSON-এর SHA256; request_hash একা যথেষ্ট নয়, কারণ একই request-এ candidate/provider
বদলাতে পারে। Pure builder expected request/provider নিয়েও report revalidate করবে।

প্রতি field-এ একটিমাত্র tagged decision:

| Action | মানে ও validation |
|---|---|
| accept | সংশ্লিষ্ট nonempty, unambiguous candidate হুবহু নেবে; user value payload নিষিদ্ধ |
| replace | user-supplied পূর্ণ field value নেবে; scalar/list type, length/count existing bounds মেনে চলবে |
| omit | শুধু optional accessories/negative_traits; value payload নিষিদ্ধ; final empty tuple |

Face/hair/eyes/outfit/colors required; omit নয়। Missing বা ambiguous required field-এ
replace প্রয়োজন। Ambiguous optional field-এ replace/omit প্রয়োজন। Empty optional
candidate-এর decision omit; accept দিয়ে unknown-কে confirmed absence বলা হবে না।
সাতটি decision explicit হওয়ায় unresolved field silently default হবে না। Name ও original
description প্রথম version-এ request থেকে অপরিবর্তিত থাকবে; edit করলে নতুন extraction
request/report লাগবে। এটি full form-edit feature নয়।

List replacement প্রথম scope-এ whole-field; item merge/edit tracking নয়। Accept list
candidate order ধরে রাখে। Replace-এর final normalized value candidate-এর সমান হলেও
origin user_replacement থাকবে—কী action হয়েছে তা inference করে বদলাবে না।

Proposed `ReviewedProfileValues`: name, description, visual_traits, negative_traits;
existing bounds reuse, কিন্তু CharacterProfileDraft subclass বা user_provided source নয়।
Proposed `ReviewedExtractionProfile`: schema_version=2, character_id, source=
reviewed_extraction, values, provenance (validated full report, report_hash, decisions)।
Origin mapping builder derives: extraction_accepted / user_replacement / user_omitted।
Caller-supplied inconsistent derived fields reject। Nested frozen/strict/extra-forbid;
unchecked-copy inputs revalidate। Initial pure builder timestamp/DB/network I/O করবে না।

সব final required fields পূরণ ও confirmed=true হলেও এটি profile review, keyframe বা
plan approval নয়। Full original report-এর REVIEW_REQUIRED status history হিসেবে থাকে;
review decision আলাদা। Evidence যে description থেকে এসেছে তা যাচাই হয়, semantic
correctness human review-এর দায়িত্বই থাকে।

## Provenance ও trusted boundary

Provider ID/version/is_mock, original canonical request, evidence spans, missing/ambiguous
fields এবং সব review actions envelope-এ থাকবে। Fixture-origin report accept/replace
করলেও is_mock=true থাকবে; provenance বাদ দিয়ে “real extraction” বলা যাবে না।
Original report ধরে রাখায় user edits আর extraction suggestion পৃথক দেখা যায়।

Pure builder-এ expected report/context caller-এর trust boundary; SHA256 signing বা
provider attestation নয়। Future HTTP save endpoint arbitrary client-posted report/
provider metadata বিশ্বাস করবে না। Server-owned draft store থেকে opaque draft_id
দিয়ে validated report read করবে; client শুধু report_hash ও review decisions পাঠাবে।
Draft record immutable, character/request/provider-bound; stale/missing draft reject।
Server-owned draft storage/lifetime এবং API wiring পরে পৃথক micro-step। সেই trusted
lookup ছাড়া reviewed-save endpoint production-ready নয়।

Future persistence wrapper server-generated created_at/reviewed_at রাখবে; client time
trusted audit timestamp নয়। Raw input/provider output logs-এ dump নয়। Stored original
request/evidence ব্যক্তিগত description-এর আরেকটি copy; future retention/delete scope-এ
profile provenance ও drafts দুটোই include করতে হবে। এখানে নতুন retention service নয়।

## Proposed additive storage ও conflict policy

Future migration existing v1 table রেখে `reviewed_character_profiles` যোগ করতে পারে:
character_id PK/FK, schema_version=2 CHECK, reviewed_json, server timestamps। v2 UPDATE
নিষিদ্ধ; v1 rows/JSON/timestamps unchanged। Both tables-এ BEFORE INSERT cross-table
existence guard দিতে হবে, যাতে পুরোনো manual writer-ও v2-এর পাশে v1 ঢোকাতে না পারে।
Repository transaction `BEGIN IMMEDIATE`-তে character existence, either profile existence,
server-owned draft binding এবং insert করবে। DB guard concurrency backstop; integrity
failure শুধু profile conflict প্রমাণিত হলে 409, সব DB error-কে conflict বলা নয়।

| State/attempt | Proposed outcome |
|---|---|
| Character missing | 404; no write |
| No profile + valid reviewed draft | Create v2 immutable record |
| Existing v1 + reviewed save | 409; v1 untouched |
| Existing v2 + manual or reviewed save | 409; v2 untouched |
| Concurrent manual/reviewed saves | Exactly one success; other conflict |
| Response lost after commit | GET authoritative profile; no automatic overwrite/retry |
| Corrupt provenance/unsupported schema | Sanitized read error; never null/fallback profile |

No automatic migration of existing user_provided rows into reviewed provenance। No
profile replacement/version-history feature; schema v2 মানে format version, editable
revision নয়। Destructive downgrade forbidden, current migration policy অনুসারে।

## API/adapter backward compatibility rollout

Future versioned profile read path authoritative v1-or-v2 discriminated union ফেরত দেবে;
reviewed save-এর পৃথক endpoint/draft lookup থাকবে। Existing v1 GET/POST-এর v1 records
ও response shape অপরিবর্তিত। v2-only character-এর old GET null ফেরাবে না—explicit
409 unsupported-profile-version দেবে; old UI error দেখাবে, empty form নয়। Old POST-ও
conflict। Legacy Character create/list API/schema অপরিবর্তিত।

Current planner adapter/preview শুধু v1 জানে। V2 writer enable করার আগে version-aware
reader/adapter/consumer checks লাগবে; silent v1 projection বা source relabel নয়।
Adapter final reviewed values inject করবে, provenance/raw description prompt-এ নয়;
mock-origin marker UI-তে বজায় রাখতে হবে। এই rollout একাধিক future micro-step; শুধু
pure contract বা migration pass মানেই reviewed save enable করা যাবে না।

## Acceptance ও next bounded implementation

Next proposed **5.7j pure review-decision/ReviewedExtractionProfile contract ও builder
with tests**; migration/API/UI/draft store/provider run বাদ। New domain module/tests,
existing extraction and manual persistence untouched। Acceptance:

1. Complete candidate + seven decisions + confirmed=true produces immutable v2 values
   and retained report/provenance; not a SavedCharacterProfile v1।
2. Partial/ambiguous required fields require explicit replacements; optional omissions
   recorded, incorrect accept/omit/extra/missing decisions rejected।
3. Wrong character/report hash/context, bool-vs-int confirmation/version, bad nested
   unchecked copies/types/bounds rejected; no silently reassigned evidence।
4. Unicode/Bengali, exact accepted values/order, whole-list replacement, normalized
   final values and derived origins verified; fixture remains mock after edits।
5. Changing candidate/provider with identical request changes report hash; replay of
   old decision rejected; all fixtures stay review-only until explicit confirmation।
6. No DB/network/clock; manual contract/extraction/store regression PASS।

Future storage acceptance (not 5.7j): all prior revisions migrate/backward-read, legacy
rows byte-preserved, both write-order conflicts and concurrent races, rollback/restart,
corrupt provenance error, trusted draft lookup, authoritative read and old-v1 guard,
version-aware preview integration।

## Outcome/checks/authorization

5.7i design review সম্পন্ন। Existing requirements unchanged; this is proposed design,
master schema amendment নয়। Source/migration/API untouched; prior 92 PASS evidence
reused, app tests rerun হয়নি। Relative links, RESUME <60 lines, plan excerpt drift ও
whitespace checked। No install/model/GPU/server/commit; unrelated workspace preserved।
Owner-এর পরবর্তী next-work নির্দেশে শুধু উপরের 5.7j pure contract/builder/tests অনুমোদিত
হবে। এই review নিজে implementation, v2 database write বা real inference approval নয়।
Full 5.7 এবং image generation এখনও অসম্পূর্ণ।
