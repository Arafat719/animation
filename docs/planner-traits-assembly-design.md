# Traits assembly — ownership ও duplicate/overflow design

2026-09-23। Owner “ok porer kaj koro” নির্দেশে design review সম্পন্ন।
[Cast checkpoint](planner-cast-checkpoint.md), [injector](../animation_studio/providers/planner.py)
ও [traits tests](../tests/test_character_traits.py) পর্যালোচনা হয়েছে। Source বদলায়নি।

## বর্তমান আচরণ ও নির্বাচিত boundary

Existing inject_character_traits visible supplied profiles-এর visual traits
image_prompt/motion_prompt-এ এবং negative traits negative_prompt-এ append করে।
এটি input অপরিবর্তিত রেখে validated নতুন plan দেয়; overflow reject করে। কিন্তু
একই assembled output আবার দিলে blocks আবার যোগ হবে। MockPlanner ইতিমধ্যে injector
চালায়; তার returned plan raw base নয়। Repair runner বর্তমানে traits assemble করে না।

নির্বাচিত পরের micro-step: **পৃথক pure offline traits assembly helper + tests**।
Repair runner/API/MockPlanner-এ wiring এই step-এ নয়। Helper input raw base StoryPlan
JSON ও caller profiles; output frozen result-এ immutable base_json এবং assembled_json,
status REVIEW_REQUIRED। Output-কে base হিসেবে পুনর্ব্যবহারের contract নেই।
Stored JSON strings ব্যবহার করলে base snapshot ও derived output mutable model
reference share করবে না। দুই JSON-ই schema-validated normalized serialization;
base_json byte-for-byte provider stream নয়—raw evidence caller-এর দায়িত্ব।

## Ownership ও procedure

1. Profiles independent validation snapshot; duplicate profile ID reject। Base JSON
   existing StoryPlan validator-এ validate। Supplied IDs cast subset এবং matched
   names exact equality চাই; whitespace normalization existing schema অনুযায়ী।
   Helper direct call-এ runner guard আগে হয়েছে ধরে নেবে না।
2. Helper canonical caller blocks-এর মালিক: `Name [id]: trait1; trait2`;
   visible_character_ids order অনুযায়ী existing injector-ই assembly করবে।
   Offscreen-only/unused profile-এর blocks যোগ হবে না; extra cast-এ caller traits
   নেই। Empty profiles হলে independently validated unchanged plan।
3. Duplicate preflight: প্রতিটি supplied profile-এর nonempty visual/negative canonical
   block তৈরি করে সব shot-এর তিন prompt field-এ exact substring উপস্থিতি পরীক্ষা।
   পাওয়া গেলে TRAITS_ALREADY_PRESENT; strip/replace/deduplicate নয়। Check order
   shot → image/motion/negative field → request profile → visual/negative block।
   প্রথম conflict-এ fail; path ('shots', index, field)।
4. এই conservative reserved-format rule provider-এর হুবহু canonical block ফিরিয়ে
   দেওয়া reject করে, invisible profile-এর prefilled block-ও ধরে। Legitimate base
   text-এ একই literal block থাকলেও ambiguous হিসেবে reject হবে। Paraphrase,
   case/spacing variation বা semantic repetition শনাক্তের দাবি নেই। Caller traits
   নিজেরাই repeated হলে helper সেটি silently clean করবে না।
5. Existing injector একবার চালিয়ে assembled plan পুনরায় validate। Existing 4000-character
   prompt limits বহাল; overflow-এ TRAITS_ASSEMBLY_INVALID, validator field paths।
   Truncation/trait omission নয়; base unchanged। Hidden retry বা provider call নেই।
6. Result-এর assembled_json আবার input হলে কোনো injected canonical block থাকলে
   duplicate preflight reject করবে। No-visible-profile/empty-profile no-op ক্ষেত্রে
   আবার একই unchanged result গ্রহণযোগ্য; যোগ করার block-ই নেই।

## Failures ও ভবিষ্যৎ integration

Proposed helper `assemble_planner_traits(base_json, profiles)` এবং typed
TraitsAssemblyError(code, paths) ব্যবহার করবে। Input JSON/profile validation-এর
ValidationError propagate; duplicate profile ID/unknown cast/name mismatch typed
TRAITS_PROFILE_MISMATCH, যথাযথ profile/cast path। Non-string input TypeError।
Assembly overflow-এ শুধু injector validation failure wrap হবে; broad exception
swallow নয়। Codes runner-এর RepairIssue-তে এখন যোগ হবে না।

ভবিষ্যৎ runner wiring-এ প্রতিটি candidate নিজস্ব raw base থেকে assembly করতে হবে;
assembled output কখনো repair feedback হিসেবে পাঠাবে না। Overflow-এ shorter base
চাওয়া হবে কি না, এবং impossible profile-size preflight—সেটি integration scope।
এই helper live provider suitability, freshness/duration retry বা narrative acceptance
যাচাই করে না; existing runner guards আলাদাভাবে বহাল থাকবে।

## প্রয়োজনীয় tests ও files

প্রস্তাবিত files: `animation_studio/providers/planner_traits.py`,
`tests/test_planner_traits.py`। Existing injector/mock behavior বদলাবে না।

- Visible-only visual/negative blocks; visible order; offscreen-only ও no-visible
  cases; extra cast ও empty profiles; Bengali/multiline traits।
- Immutable independent base/assembled JSON; একই raw base থেকে repeat assembly
  deterministic, caller input/profile unchanged।
- Already assembled output ও prefilled canonical block (অন্য prompt field এবং
  invisible supplied profile-সহ) reject; variation semantic dedup দাবি নয়।
- Duplicate/unknown/mismatched profiles এবং invalid raw JSON reject।
- প্রতিটি prompt field-এ limit boundary PASS ও overflow FAIL; কোনো truncation নয়;
  empty negative traits existing negative prompt অক্ষত রাখে।
- Existing mock output with visible supplied traits helper-এ raw base হিসেবে reject;
  fixtures explicit base prompts বানাবে, mock snapshots বদলাবে না।

Implementation হলে নতুন helper suite + existing traits/repair/mock/StoryPlan suites
চালাবে। আগের ১১১ PASS baseline reuse; এই docs-only step-এ app tests চালানো হয়নি।

## Outcome ও authorization

Design সম্পন্ন; blocker নেই। পরের bounded কাজ উপরের helper/tests implementation;
Owner-এর পরবর্তী নির্দেশে helper/tests সম্পন্ন; [checkpoint](planner-traits-checkpoint.md)।
Traits assembly runner/API-তে জুড়ে দেওয়া আলাদা কাজ। Phase 3/3.10
অসম্পূর্ণ; CPU experiment queue বন্ধ; model run/download নয়।
Docs links/RESUME/status/scope/plan drift/whitespace PASS; master/public schema/source
অপরিবর্তিত। এটি internal helper-এর proposed contract, product requirement revision
নয়। Unrelated edits সংরক্ষিত; commit হয়নি।
