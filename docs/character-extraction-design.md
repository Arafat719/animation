# 5.7g — description-to-profile provider contract design review

2026-10-12। Owner next-work নির্দেশে documentation-only review সম্পন্ন।
[5.7f next scope](character-cast-preview-ui-checkpoint.md) অনুসৃত। এই document proposed
implementation design; provider/model/API/migration implementation হয়নি।

## Evidence ও compatibility সিদ্ধান্ত

[Master-এর Phase 5](../AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md) 5.7 description থেকে
profile ও saved traits চায়; বর্তমান GPU-free decomposition semantic extraction defer
করেছে। সংশ্লিষ্ট heading-ই পড়া হয়েছে, সম্পূর্ণ master audit নয়।
[Contract](../animation_studio/domain/v1/character_profile.py),
[tests](../tests/test_character_profile.py),
[store](../animation_studio/persistence/character_profiles.py),
[API](../apps/api/character_profiles.py) এবং
[planner adapter](../animation_studio/providers/character_profile_adapter.py) যাচাই।

বর্তমান CharacterProfileDraft সম্পূর্ণ face/hair/eyes/outfit ও অন্তত একটি color চায়;
source কেবল user_provided। Store immutable single snapshot রাখে। Extraction output
এই schema-তে partial হিসেবে ঢোকানো বা source বদলে model-generated value save করা
সঠিক নয়। Existing manual create/read/preview flow অপরিবর্তিত রেখে পৃথক suggestion
contract হবে। Suggestion কখনও SavedCharacterProfile নয়, planner adapter input-ও নয়।

## প্রস্তাবিত pure contract

| Boundary | Proposed shape / দায়িত্ব |
|---|---|
| ExtractionRequest | schema_version=1, explicit character_id, caller-supplied name, description |
| EvidenceValue | value এবং description-এর start/end Unicode code-point offsets |
| ExtractionCandidate | face/hair/eyes/outfit: EvidenceValue অথবা null; colors/accessories/negative_traits: immutable EvidenceValue tuples; ambiguous_fields: bounded unique field names |
| ExtractionReport | request identity/hash, candidate, computed missing_required, configured provider identity/version ও is_mock, status=REVIEW_REQUIRED |
| CharacterProfileExtractionProvider | extract(request) → ExtractionCandidate; DB/save/planner/job access নেই |
| Validation/report builder | expected request ও configured provider metadata নিয়ে candidate revalidate, identity bind, missing fields derive, report তৈরি |

সব নতুন schema strict/extra-forbid/frozen; nested unchecked copies পুনরায় validate।
Request character_id strict positive signed-64-bit integer (bool reject); name trimmed
1–120 ও description trimmed 1–4000 code points, বর্তমান contract bounds অনুসারে।
Trimming শুধু request boundary-তে; Unicode normalize/translate নয়। Provider পাবে সেই
canonical description; offsets সেখানেই প্রযোজ্য। Name caller-owned, provider নাম
invent/rename করবে না। একই নামের character-ও request ID দিয়ে পৃথক থাকবে।

প্রথম proposed contract **extractive suggestions**: প্রতিটি value 1–500 code points;
0 <= start < end <= len(description), এবং description[start:end] == value। Evidence
এর source শুধু request description; filename/path/URL/tool instruction নয়। Scalar
traits null মানে উল্লেখ পাওয়া যায়নি; colors 0–20, accessories 0–20, negative traits
0–100 items। Duplicate exact evidence entry reject; তালিকায় description-order রাখবে।
একই span একাধিক category-তে থাকতে পারে (যেমন outfit phrase-এ color)।

Exact-span validation quotation যাচাই করে, semantic correctness নয়: negation,
wrong character, category mismatch বা contradictory sentence এতে নিজে থেকে ধরা পড়ে
না। সেগুলো future provider evaluation ও user review-এর check। “কালো চুল” থেকে “নীল
চোখ” বানানো exact-span validation-এ reject হবে; description-এ দুটি চরিত্র থাকলে
কোন phrase কার—তা offset দিয়েই প্রমাণিত হয় না।

Required fields face/hair/eyes/outfit null হলে এবং colors empty হলে missing_required
fixed order-এ report builder হিসাব করবে। Optional empty lists মানে কোনো suggestion
নেই; “কোনো accessory নেই” এমন fact দাবি নয়। Ambiguous field-এর candidate null/empty
থাকবে; provider তার বদলে একটি guess বেছে নেবে না। ambiguous_fields শুধু সাতটি
trait field-এর নাম, duplicate/unknown reject। Required ambiguity missing_required-এও
থাকবে। Optional ambiguity-ও review-তে দৃশ্যমান রাখতে হবে।

সব ক্ষেত্র পূরণ হলেও status REVIEW_REQUIRED, approval/ready-to-save নয়। Model-এর
confidence score approval হিসেবে ব্যবহার হবে না; প্রথম contract-এ score প্রয়োজন নেই।

## Request binding ও provenance

Report builder metadata owner: configured provider_id/provider_version (bounded text),
is_mock explicit bool; provider candidate নিজে mock flag বা stored source লিখবে না।
সেগুলো trusted adapter configuration, cryptographic provider attestation নয়।

Request fingerprint: validated request-এর schema_version/character_id/name/description
নিয়ে sorted-key compact JSON (`ensure_ascii=False`, separators comma/colon), UTF-8
bytes-এর SHA256 hex। একই canonical request একই hash; অন্য ID/name/description আলাদা।
Report validator expected request-এর সঙ্গে identity/hash মিলাবে। Hash provenance বা
semantic correctness প্রমাণ করে না, stale/cross-request mix-up detect করার উপায়।
Raw description future logs-এ dump নয়; প্রথম pure step logging/I/O রাখবে না।

Future UI-তে suggestion ও evidence review করা যাবে; বর্তমান profile endpoint-এ
model suggestion auto-convert/save নয়। Model-origin traits-এর persisted provenance
ধারণ করতে future versioned save contract/migration/backward-read design আলাদা দরকার।
শুধু user click করেছে বলে পুরোনো source=user_provided-এ model output relabel করা যাবে
না। এই সিদ্ধান্ত existing manual profile API বন্ধ বা পরিবর্তন করে না।

## Mock ও failure semantics

Mock হবে explicit fixture provider: validated expected request fingerprint-এর জন্য
configured candidate দেয়, unknown input-এ typed FixtureNotFound। Arbitrary prose parse
করে বাস্তব extraction হয়েছে দাবি করবে না। Fixture নিজেও report builder-এর validation
পাস করবে। Known fixture incomplete হতে পারে; missing fields ঢাকতে canned full profile
নয়। Deterministic output, immutable data, no clock/random/network/model/database।

Invalid request/candidate/evidence → validation failure; unmatched fixture → typed
failure; success হলে শুধু review report। Failure-এ empty-success report বা fallback
character নয়। Retry/repair প্রথম pure step-এ নেই। Future real adapter-এর timeout,
cancel, output byte limits ও sanitized provider failures আলাদা orchestration কাজ।

## Proposed 5.7h acceptance

পরের একক micro-step: pure extraction request/candidate/report contract, provider Protocol,
explicit fixture mock ও report validation tests। API/UI/save conversion/model load নয়।
সম্ভাব্য files: নতুন domain contract, provider module ও dedicated tests; existing
CharacterProfileDraft/store/adapter/API/schema untouched।

1. Bengali/English fixture-এর exact spans ও caller-owned name/ID preserved; canonical
   request hash deterministic, অন্য character/description-এ mismatch reject।
2. Required omissions, all-unknown description, optional empty lists ও ambiguity
   accurately reported; কোনো trait default/invent নয়; all statuses REVIEW_REQUIRED।
3. Bounds, bool IDs/offsets/schema-version, invalid type/extra field, reversed/out-of-range
   offset, wrong substring, duplicate evidence ও unknown ambiguity reject।
4. 500-code-point trait, count limits, Unicode emoji/combining sequence offsets;
   Python code points ব্যবহার, UTF-16 indices ধরে নেওয়া নয়।
5. Frozen nested data, unchecked-copy revalidation; no DB/network/model side effects।
6. Fixture success/incomplete/unmatched/invalid cases; fixture report সবসময় is_mock=true;
   provider output mock flag override করতে পারবে না।
7. Existing manual contract, adapter ও persistence tests regression PASS; semantic
   extraction achieved বা full 5.7 complete বলা যাবে না।

## Real-provider prerequisites ও সীমা

Real provider choice এই review-তে করা হয়নি; কোনো current model capability/hardware
recommendation বা বাইরের research দাবি নেই। Owner-deferred CPU experiments পুনরায় নয়।
Real adapter শুরুর আগে আলাদা scope, available runtime/resource preflight, provider
identity/license এবং bounded cancellation/output handling দরকার। Paid resource বা
>2 GB download-এর explicit approval নিয়ম বহাল।

Real acceptance-এ Bengali/English held-out descriptions, omitted attributes, negation,
contradictions, multiple characters, prompt-like instructions এবং repeated runs যাচাই
করতে হবে। Category/subject correctness human-labelled evidence দিয়ে মাপতে হবে; শুধু
schema/span tests model quality প্রমাণ নয়। Full 5.7 completion-এ real extraction এবং
provenance-preserving reviewed persistence evidence এখনও প্রয়োজন; visual consistency
এবং Phase 5-এর image gates আলাদাভাবে pending।

## Outcome, checks ও next authorization

Design review সম্পন্ন; source/schema/requirements বদলায়নি। তাই master edit/regeneration
নয়; plan excerpt drift check, relative links, whitespace ও RESUME length যাচাই।
আগের 38 API + 17 browser evidence reused; documentation-only হওয়ায় app tests rerun নয়।
No install/model/server/GPU/commit। Unrelated dirty workspace preserved।
Next proposed 5.7h pure contract/mock/tests উপরের bounded scope। Owner-এর পরবর্তী
next-work নির্দেশ এই implementation অনুমোদন হিসেবে গণ্য হবে; এই review instruction
নিজে implementation অনুমোদন নয়। Future API/UI, reviewed-save migration এবং real
provider integration আলাদা micro-step, এই next scope-এর অংশ নয়।
