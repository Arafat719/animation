# Phase 5.4 — mock v2 durable executor integration

2026-10-04। অনুমোদিত একটি micro-step সম্পন্ন। New `DurableComfyExecutorV2`
(`comfy_v2_executor.py`) v2 storage/context এবং existing mock HTTP executor যুক্ত করে।

## Behavior

- Exact mock executor ও validated independent context প্রয়োজন; context origin
  fixed mock transport origin-এর সঙ্গে মেলে। Live mode storage-এ rejected।
- Graph fingerprint ও pre-cancel check → job lock → existing-path guard → mandatory
  inventory preflight → graph/cancel recheck → intent fsync → one submit → accepted
  receipt persist → history/view। Lock পুরো operation-এ ধরে রাখা হয়।
- Preflight/cancel/pre-write failure-এ intent/POST নেই; corrected explicit retry
  সম্ভব। Intent থাকলে execute বন্ধ; lost/malformed receipt outcome unknown রেখে
  recovery-ও বন্ধ। Receipt storage failure typed io_error ও validated receipt
  retaining `ComfyExecutionError` দেয়; retry বা success ঢেকে দেওয়া হয় না।
- Recovery graph/context-matched accepted v2 record ছাড়া HTTP চালায় না। Recovery
  GET-only history/view; inventory read, submit বা cancellation POST নয়।
- Legacy v1 executor অপরিবর্তিত; v1 journal v2 path-এ rejected, implicit promotion
  নয়। Existing provider/schema/DB/UI পরিবর্তন হয়নি। Returned bytes image-provider
  verification/save-এর বিকল্প নয়; v2 durable ImageProvider composition এখনও বাকি।

## Checks

**378 PASS** = previous 357 + 21 new executor cases, ten relevant suites।
`.venv/bin/python -m pytest -q` দিয়ে executor/storage/identity/journal/durable image/
HTTP/image/workflow/image provider/preflight suites চালানো হয়েছে।

New evidence: socket-forbidden order/restart recovery, preflight/cancel/write failure
retry boundary, lost/malformed receipt ও receipt persistence failure no-resubmit,
সব সাত identity mismatch + v1 rejection before HTTP, competing owner during
preflight, pre-cancel/wrong graph, GET-only recovery timeout। Actual subprocess
abrupt exit at submit/download → parent restart: one submit total, receipt-less
intent blocked অথবা accepted record থেকে GET-only output recovery।
Subprocess test script-এর newline escaping সংশোধনের পর final run PASS। Ruff
lint/format PASS; কোনো dependency install/live network/model/GPU call হয়নি।

## Limits / next

Mock identity declarations remote runtime/model attestation নয়। Raw executor bypass,
same-job root/ID retention, cooperative deadlines, ambiguous receipt ও cleanup-stop
proof-এর আগের সীমা বহাল। Real 5.4 image gate এখনও অসম্পূর্ণ।
Next authorized offline micro-step: v2 durable ImageProvider generate/recover
composition ও verified saved image contract tests; existing v1 compatibility
বজায় রেখে। Live transport/runtime/GPU/new phase/5.5 শুরু নয়।
