# 5.7f — explicit saved-character mock preview UI

2026-10-12। Owner next-work নির্দেশে [5.7e-এর next scope](character-profile-ui-checkpoint.md)
অনুযায়ী project workspace read-only cast preview সম্পন্ন।

## আচরণ ও files

[ProjectWorkspace](../apps/web/src/ProjectWorkspace.tsx)-এ
[CastPreviewPanel](../apps/web/src/CastPreviewPanel.tsx),
[display validation](../apps/web/src/castPreview.ts) ও
[styles](../apps/web/src/CastPreviewPanel.css) যুক্ত হয়েছে। Existing ShotList, persisted
plan/approval/render flow, backend/schema/migrations বদলায়নি।

Characters GET থেকে explicit checkbox selection; automatic cast নেই। Same-name
characters ID দিয়ে পৃথক; selection order POST body-তে যায়, সর্বোচ্চ 100 নির্বাচন।
List-এ legacy saved character records দেখা যায়; profile availability preview API
যাচাই করে। Missing profile 409-এ Characters-এ profile save করার নির্দেশ/link থাকে।
সব character-এর profile আগেই fetch করার N+1 request যোগ হয়নি।

`POST /projects/{id}/mock-plan` response-এ mock/review labels, requested cast identity/order,
shot order/unique IDs, duration sum/range, pending status, seed, displayed prompt limits
ও visible cast references checked। এটি displayed subset validation; full StoryPlan
validation backend-এর দায়িত্ব। Snapshot names, Unicode image/motion/negative prompts,
visible IDs ও seeds read-only দেখায়। UI-তে save/approve/render action নেই।

Loading/empty/error/success states, sanitized HTTP errors, manual retry, 10s timeout
ও duplicate-submit guard আছে। Selection/reload-এ old result মুছে request abort হয়;
request identity guard newer result রক্ষা করে। Project/API keyed component navigation-এ
selection/result reset করে। Refresh-এ preview ও selection persist হয় না। Existing
saved plan remains independent।

## Checks

- Prior unchanged 5.7e build/typecheck + 38 API/13 browser evidence baseline reused।
- Relevant API tests **38 PASS** (2 existing TestClient deprecation warnings):
  `tests/test_character_preview_api.py tests/test_mock_plan_api.py tests/test_character_profiles_persistence.py`।
- [Browser harness](../scripts/check_cast_preview_ui.mjs): **17 scenarios PASS**, first run।
  Loading/empty/list error retry, no auto cast, same-name IDs/order, Unicode result,
  double submit, refresh reset, old no-cast shot prompts untouched, HTTP 404/409/422/500,
  invalid mock marker/cast/timeline/status/visible identity, selection/project races,
  list reload, network failure, actual 10s timeout, 100-selection limit ও unsafe IDs।
  Every non-GET request asserted to be the preview POST only।
- Separate actual API/fresh temporary SQLite browser check PASS: profile save → explicit
  cast preview → six shots with stored Bengali traits; persisted plan and jobs JSON
  before/after equal, old ShotList prompt unchanged; reload clears temporary result।
- Build (includes typecheck), lint, format check PASS। Only unchanged ShotList
  set-state-in-effect lint warning remains; new files clean।
- Desktop screenshot inspected; 390px mobile horizontal overflow check PASS। Fixture
  screenshots `/tmp` only। No claim of real generated media/visual consistency।
- Docs links, RESUME <60 lines, plan excerpt drift ও whitespace PASS।

Reusable browser command, with local Vite running:

```sh
PLAYWRIGHT_MODULE_PATH=/absolute/path/to/existing/playwright node scripts/check_cast_preview_ui.mjs
```

Default URL `http://127.0.0.1:5175`, override `CAST_UI_URL`। Harness uses mock API routes;
actual API check used another port/fresh temp DB। Existing cached Playwright/Chromium
used, no dependency install/download। Local server/browser/API regressions ran with
approved sandbox escalation (prior socket/TestClient restrictions)। Owned servers stopped।
No GPU/remote publish/commit; unrelated dirty changes preserved। Requirements unchanged,
master/excerpts not rewritten।

## সীমা ও next

UI accepts only JS-safe positive integer IDs; invalid/duplicate/unsafe list identity
fails closed rather than rounding into another character। Backend signed-64-bit range
remains unchanged। Character list GET is existing unpaginated API; profile availability
is confirmed at submit, not advertised as preverified in list। Prompt overflow remains
an explicit API error; no truncation or automatic retry।

5.7f সম্পন্ন; full 5.7 description-to-traits extraction ও real image gates pending।
Next proposed bounded work: **5.7g description-to-profile provider contract design
review**, GPU-free/documentation-only। Existing user_provided immutable contract এবং
manual-save flow রেখে extraction draft/provenance/missing-trait validation boundary,
mock acceptance ও real-provider prerequisites নির্ধারণ করবে; এই review model run,
provider implementation, migration বা automatic save অনুমোদন নয়। Owner-এর পরবর্তী
next-work নির্দেশে review করা যাবে; এই turn-এ শুরু হয়নি।
