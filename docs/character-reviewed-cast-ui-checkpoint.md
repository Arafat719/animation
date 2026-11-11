# 5.7o — cast preview UI version-aware selection/origin labels

2026-10-12। Owner-এর পরের কাজের নির্দেশে [5.7n](character-reviewed-preview-checkpoint.md)
পরবর্তী bounded UI/tests সম্পন্ন।

## Outcome ও files

- [CastPreviewPanel](../apps/web/src/CastPreviewPanel.tsx) character list-এর পর versioned
  GET /v2/characters/{id}/profile পড়ে, এক batch-এ সর্বোচ্চ 8 requests। Saved v1/v2 select
  করা যায়; null profile disabled এবং “No saved visual profile” দেখায়। Invalid/error response
  list error ও explicit retry দেয়; loading শেষ হওয়ার আগে selection প্রকাশ করে না।
- [castPreview parser](../apps/web/src/castPreview.ts) displayed profile summary-এর identity,
  version/source, reviewed confirmation/report status/provider mock type যাচাই করে। Full
  provenance/hash/traits validation backend-এর দায়িত্ব; UI semantic review করে না।
- Selection ও result-এ Manual profile / Reviewed profile · Mock extraction / Reviewed
  profile · Non-mock extraction labels। Preview-level Mock/Review required/Read-only banner
  সবসময় থাকে। Response profile_origins required এবং selected IDs/order/version/source/
  mock types-এর সঙ্গে bind হয়; missing/invalid metadata হলে result দেখায় না।
- [CSS](../apps/web/src/CastPreviewPanel.css)-এ origin label আলাদা row; mobile overflow
  check ও screenshot review সম্পন্ন। [Browser harness](../scripts/check_cast_preview_ui.mjs)
  versioned profile fixtures ও নতুন mixed-origin/error/navigation scenarios যুক্ত করেছে।

Profile fetch/preview abort ও project remount stale result দমন করে; reload selection/result
clear করে। Existing selection order/100 limit, pending preview ও no-write controls বজায় আছে।
API/backend/writer/Character profile editor পরিবর্তন হয়নি; নতুন dependency/install নেই।

## Checks

**26 browser scenarios PASS** (আগের 17 + নতুন 9): loading/empty/retry/manual/mixed mock ও
non-mock origin labels, disabled missing profile, corrupt profile, sanitized profile error,
invalid/missing/mismatched preview origins, navigation during profile fetch, stale preview,
refresh/reset, actual timeout, no automatic retry, safe IDs/selection cap, read-only POST
allowlist এবং mobile no-overflow। Fixtures synthetic; non-mock marker real extraction
প্রমাণ নয়। Prior 5.7n 84 API tests baseline reused; unchanged backend tests rerun হয়নি।

```sh
npm --prefix apps/web run build
npm --prefix apps/web run lint
PLAYWRIGHT_MODULE_PATH=/home/arafat/.npm/_npx/e41f203b7505f1fb/node_modules/playwright node scripts/check_cast_preview_ui.mjs
```

TypeScript/build PASS; lint-এ existing ShotList.tsx set-state-in-effect warning মাত্র।
Changed files Prettier PASS; plan excerpt drift/docs links/RESUME length/whitespace PASS।
Sandbox listen EPERM-এর জন্য local Vite/Chromium outside sandbox; API routes mocked,
কোনো live backend/user DB write হয়নি। Test Vite process শেষে বন্ধ করা হয়েছে।

## Limits ও next

Reviewed-save API, trusted extraction draft lookup/lifetime ও real extraction বাকি।
Characters profile editor এখনও v1-only; v2-তে existing explicit 409 error দেখায়, blank
manual save form নয়। Cast preview এখন reviewed profiles consume করে, full 5.7 complete নয়।

Next proposed **5.7p server-owned extraction draft lifecycle design review**: opaque draft
identity, request/provider/character binding, expiry/retention, atomic reviewed-save lookup
ও recovery/conflict acceptance নির্ধারণ; documentation-only। Owner-এর পরবর্তী next-work
নির্দেশে এই bounded review শুরু করা যাবে; migration/API writer implementation নয়।
