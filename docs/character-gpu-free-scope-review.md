# 5.7d-পরবর্তী GPU-free scope review

2026-10-12। Owner-এর “পরের কাজ করো” নির্দেশে পূর্বপ্রস্তাবিত remaining-scope review
সম্পন্ন। এই micro-step documentation-only; feature implementation হয়নি।

## Evidence এবং সিদ্ধান্ত

[Phase 5](plan/phase-5.md) ও master-এর সংশ্লিষ্ট Phase 5 headings মিলিয়ে দেখা হয়েছে।
[5.7d checkpoint](character-preview-checkpoint.md)-এর 118 PASS evidence reuse।
[Profile contract](../animation_studio/domain/v1/character_profile.py),
[profile API](../apps/api/character_profiles.py),
[Characters UI](../apps/web/src/CharactersPage.tsx) এবং
[ShotList](../apps/web/src/ShotList.tsx) inspect করা হয়েছে।

| কাজ | বর্তমান evidence / dependency | সিদ্ধান্ত |
|---|---|---|
| User-provided immutable profile | Contract, persistence, adapter, preview API complete | Completed কাজ পুনরায় নয় |
| Profile authoring/read UI | Characters page শুধু legacy name/description save করে; profile GET/POST ready | পরের প্রস্তাবিত 5.7e |
| Selected-cast preview UI | API ready; UI-তে profile authoring নেই, ShotList persisted-plan flow ব্যবহার করে | 5.7e-পরবর্তী পৃথক scope |
| Description থেকে semantic extraction | বর্তমান profile source user_provided; real planner experiments স্থগিত | Full 5.7 pending, mock-কে extraction বলা যাবে না |
| Reference conditioning / poses / image approval | Real image ও visual consistency evidence নেই | 5.4/5.5 এবং 5.8–5.11 deferred |

## প্রস্তাবিত একক micro-step 5.7e

Existing saved character-এর জন্য immutable profile create/read UI। Characters page-এ
নির্দিষ্ট character খুললে তার profile GET হবে; null হলে form, saved হলে read-only
snapshot। Existing legacy create form/API অপরিবর্তিত থাকবে। নতুন migration বা API নয়।

Form-এ snapshot name/description এবং face, hair, eyes, outfit, colors প্রয়োজন;
accessories/negative traits optional। Name/description legacy record থেকে editable
initial values হতে পারে; traits অনুমান নয়। Existing schema অনুযায়ী whitespace ও
length/count validation: name 120, description 4000, each trait 500 characters;
colors 1–20, accessories 0–20, negative traits 0–100। Multi-value fields স্পষ্ট
one-item-per-line নির্দেশে নেওয়া যেতে পারে। User-provided profile ও save-এর পর
edit না হওয়ার বিষয়টি save action-এর কাছে পরিষ্কার থাকবে।

POST success-এ server snapshot দেখাবে; refresh-এ GET দিয়ে একই profile ফিরে আসবে।
409 হলে existing snapshot reload; timeout/ambiguous save হলে GET দিয়ে reconcile,
automatic POST retry নয়। GET ব্যর্থ হলে error/retry state; ব্যর্থ read-কে null ধরে
form দিয়ে overwrite attempt নয়। Character switch/unmount-এ abort/stale response
সুরক্ষা; double submit prevention। API errors থেকে raw private payload দেখানো নয়।

## Implementation acceptance checklist

1. Loading, no characters, no profile, saved read-only profile, GET error/retry states।
2. Unicode required/optional fields ও schema bounds; missing traits নিজে থেকে পূরণ নয়।
3. Save → reload persistence, 409 recovery, ambiguous-save reconciliation; duplicate
   POST নয়; unsaved values error-এ সংরক্ষণ।
4. Rapid character switch/unmount-এ আগের response ভুল character-এ না বসা।
5. Existing character create/list regression; selected API tests, frontend typecheck,
   lint/build এবং browser/UI state checks। Tool availability implementation-এর সময়
   যাচাই হবে; এই review browser testing complete দাবি করে না।

Expected code scope: CharactersPage, focused profile component/types/styles as needed;
existing backend endpoints reuse। Dependency install owner করবেন। Project assignment,
preview-to-approval wiring, reference upload UI, profile mutation/versioning, extraction
এ micro-step-এর বাইরে। এগুলো একই turn-এ যোগ হবে না।

## Checks ও authorization

Relative links, RESUME length, plan excerpt drift ও whitespace checked। Source code
বদলায়নি বলে app tests পুনরায় চালানো হয়নি। Master requirements বদলায়নি; এই document
একটি proposed implementation scope, নতুন feature requirement বা authorization নয়।

Review সম্পন্ন; 5.7e implementation এখন প্রস্তাবিত, এখনও শুরু হয়নি। Owner-এর পরবর্তী
“পরের কাজ করো” নির্দেশ এই নির্দিষ্ট 5.7e scope অনুমোদন হিসেবে গ্রহণ করা যাবে; আবার
একই অনুমতি চাইতে হবে না। New phase, paid resource, model download ও deferred CPU
experiments-এর অনুমোদন এতে অন্তর্ভুক্ত নয়।
