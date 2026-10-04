# Phase 5.4 — offline execution-context matching

2026-10-04। অনুমোদিত একটি micro-step সম্পন্ন। `comfy_identity.py`-তে
`ComfyExecutionContext` এবং `match_job_context` যোগ; writer/network integration নয়।

## Behavior

- Strict/frozen context-এ সাতটি required identity field: mode, job ID, graph hash,
  origin, deployment ID, runtime/model manifest hashes। Existing v2 validation
  reuse হয়; canonical origin/UUID ও hash rules অপরিবর্তিত। Credentials নেই।
- Caller journal থেকে context বানাবেন না; original trusted execution configuration
  থেকে দেবেন। Helper context পুনরায় validate করে, bounded versioned parser চালিয়ে
  প্রতিটি field exact-match করে এবং validated v2 record ফেরত দেয়।
- Valid-but-different identity যেকোনো পাশে থাকলে rejected। Invalid model-copy বা
  incomplete model-construct দিয়ে validation bypass accepted নয়। Public helper
  error fixed/sanitized; raw journal বা context values echo করে না।
- v1 matching path-এ rejected; existing v1 mock recovery অপরিবর্তিত। Intent match
  হলেও intent-ই ফেরে; recovery caller-কে accepted state আলাদাভাবে require করতে হবে।
  Helper কোনো receipt বানায় না, record upgrade/write/submit করে না।
- Current inventory/GPU/model availability check নেই; original context comparison
  remote attestation বা server/history continuity proof নয়।

## Checks

**337 tests PASS** = previous 298 + 39 new context cases। Eight suites:
`test_comfy_identity`, `test_comfy_journal`, `test_comfy_durable_image`,
`test_comfy_http`, `test_comfy_image`, `test_comfy_workflow`,
`test_image_provider`, `test_comfy_preflight` (`.venv/bin/python -m pytest -q`)।

Coverage: mock/live × intent/accepted success with sockets/DNS forbidden; all seven
identity mismatches on both sides; missing/invalid context fields; immutability;
v1 rejection; bounded/malformed journal errors; bypassed-instance revalidation।
Existing v1 recovery/subprocess restart regressions PASS। Ruff lint/format PASS।

## Limit / next

Helper এখনও durable executor-এ wired নয়; current runtime enforcement আগের mock v1
path। New context helper নিজে live activation বা recovery authorization নয়। Source
schema addition শুধু offline context; persisted journal/DB schema অপরিবর্তিত।

Next authorized offline micro-step: deterministic job-ID path ও bounded atomic v2
journal storage mock tests—v1 bytes preserve, lock/fsync ও write-size limitsসহ।
তারপর পৃথক durable execution integration প্রয়োজন; live transport/GPU/5.5 নয়।
Owner installation ও paid-resource restrictions বহাল; real 5.4 image gate অসম্পূর্ণ।
