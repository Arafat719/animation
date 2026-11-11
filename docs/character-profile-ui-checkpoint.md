# 5.7e — saved-character profile create/read UI

2026-10-12। Owner-এর next-work নির্দেশে পূর্বের bounded 5.7e scope বাস্তবায়ন।
[Scope review](character-gpu-free-scope-review.md) baseline; full 5.7 extraction নয়।

## ফল ও source

[CharactersPage](../apps/web/src/CharactersPage.tsx)-এ নির্দিষ্ট saved character-এর
“View visual profile” খুললে [panel](../apps/web/src/CharacterProfilePanel.tsx) profile
GET করে। Null হলে form, saved হলে immutable read-only snapshot। Legacy name/description
create/list behavior ও backend schema/API অপরিবর্তিত। Touched page-এর formatting
repository formatter policy অনুযায়ী normalize হয়েছে।

[Validation/types](../apps/web/src/characterProfile.ts) এবং
[styles](../apps/web/src/CharacterProfilePanel.css) নতুন। Name/description legacy থেকে
editable initial values; face/hair/eyes/outfit/colors owner লিখবেন। Accessories ও
negative traits optional, one item per line; blank lines ignored। Unicode code-point
length/count checks existing schema bounds মেনে চলে; server-ই authoritative।
Returned identity/schema/source/trait shape যাচাই করে snapshot দেখায়। No inferred traits।
Save action-এর পাশে user-provided ও immutable সীমা স্পষ্ট।

Loading/error state-এ save form নেই; 422-এ draft থাকে। 409, network error, 10s timeout
বা malformed successful response-এ GET reconciliation, automatic POST retry নয়।
Reconciliation GET ব্যর্থ হলে retry-read ছাড়া save সম্ভব নয়; null হলে draft ফিরে আসে,
manual resubmit allowed। Backend single-snapshot conflict guard remains authoritative।
Character/API-base keyed panel এবং abort checks stale response আটকায়; synchronous ref
lock double submit ঠেকায়। Draft same panel-এর errors/retry-তে থাকে; navigation/character
switch-এ unsaved draft persist হয় না।

## Checks

- Frontend baseline typecheck PASS; unchanged backend-এর পূর্বের 118 PASS reused।
- Current API regression: **38 PASS**, 2 existing TestClient deprecation warnings:
  `tests/test_character_profiles_persistence.py tests/test_characters_api.py tests/test_character_preview_api.py`।
- [Reusable browser harness](../scripts/check_character_profile_ui.mjs): **13 scenarios PASS**।
  Existing cached Playwright 1.61.1/Chromium ব্যবহার; নতুন install/download নয়।
  Empty library/legacy create, loading/null, Unicode save/refresh/read-only, double
  submit, GET failure/retry, length/count bounds, 409/lost response/actual 10s timeout,
  null/failed reconciliation, sanitized 422, wrong server identity, late GET/POST after
  selection change এবং 390px horizontal overflow checked।
- পৃথক actual API + temporary SQLite browser roundtrip PASS: legacy create → Unicode
  profile save → page reload → GET read-only snapshot। Browser fixture suite mock API
  responses ব্যবহার করে; এই পৃথক check actual backend ব্যবহার করেছে।
- Desktop form/saved ও mobile saved screenshots inspected; artifacts শুধু `/tmp`-তে।
  Existing sticky navigation overlays screenshot crops; horizontal overflow নেই।
- `npm run build` (typecheck included), `npm run lint`, `npm run format:check` PASS।
  Lint-এ unchanged `ShotList.tsx`-এর একটি set-state-in-effect warning; নতুন files clean।
- Plan drift, relative links, RESUME <60 lines এবং whitespace PASS।

Browser rerun (existing local Vite server প্রয়োজন):

```sh
PLAYWRIGHT_MODULE_PATH=/absolute/path/to/existing/playwright node scripts/check_character_profile_ui.mjs
```

Default preview `http://127.0.0.1:5175`; `PROFILE_UI_URL` override supported। Harness
সমস্ত API requests fixture দিয়ে ধরে; user database লেখে না। Actual backend check-এ
অন্য port ও fresh `/tmp` database ব্যবহৃত। Sandbox socket EPERM-এর পরে approved
outside-sandbox localhost servers/browser/tests চলেছে; owned servers শেষে বন্ধ।
Initial browser failures ছিল StrictMode-এর initial GET count assumption; initial reads
থেকে reconciliation delta এবং no duplicate POST assert করে corrected, StrictMode
disabled নয়। New effect lint findings fixed; final full browser rerun PASS।
No GPU/model/install/remote publish/commit; unrelated dirty work preserved।

## Next ও সীমা

5.7e সম্পন্ন; full Phase 5/semantic extraction/real image gates pending। Next proposed
5.7f: project workspace-এ explicit saved-character selection দিয়ে existing POST mock
preview API-র read-only result দেখানো। Loading/empty/error/success, selection change
staleness এবং old no-cast behavior checks প্রয়োজন; existing persisted plan/approval
বা render flow-তে preview silently বসানো যাবে না। Project cast assignment, approval,
image generation এই proposal-এর বাইরে। Owner-এর পরবর্তী next-work নির্দেশ এই bounded
5.7f implementation অনুমোদন হবে; এই turn-এ সেটি শুরু হয়নি।
