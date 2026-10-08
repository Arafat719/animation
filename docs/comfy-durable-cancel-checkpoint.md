# Phase 5.4 — mock durable cancellation integration

2026-10-04। Owner next-work নির্দেশে micro-step সম্পন্ন।

## Outcome

- HTTP executor-এ optional per-call cancellation handler; default legacy behavior
  অপরিবর্তিত। V2 executor একই generation lock-এর মধ্যে durable handler দেয়;
  handler থাকলে default cancellation আর চলে না, fallback dispatch নেই।
- Valid receipt + timeout/cancel হলে sidecar initial record → receipt-matched intent
  fsync → এক targeted cancel → observed/unknown persistence। Primary error retained।
- Sidecar create/intent failure-এ zero cancel; acknowledgement persistence failure-এ
  cleanup io_error/unknown প্রকাশ, retained intent দ্বিতীয় attempt বন্ধ রাখে।
- True/false acknowledgement-এর canonical `cancelled=true`/`cancelled=false` bytes
  SHA256 reference রাখা হয়; এটি mock acknowledgement digest, external evidence
  file বা stop proof নয়। Job/compute/storage status unknown থাকে।
- Recovery unchanged GET-only; sidecar অনুপস্থিত হলেও accepted result পড়া যায়।
  Existing sidecar overwrite/retry নয়। Receipt-less failure arbitrary cancel করে না।

## Checks

`.venv/bin/python -m pytest -q tests/test_comfy_*.py tests/test_image_provider.py`:
**671 PASS**। Six new integration cases: true/false/auth failure, durable intent
visible before dispatch, GET-only restart recovery, create/intent/result write
failure ও original timeout preservation। Existing cancellation/receipt-loss/auth/
legacy/storage regressions included। Ruff lint/format ও docs/plan checks PASS।

## Limits / next

Mock-only; cooperative deadlines অপরিবর্তিত। No real TLS/GPU/resource shutdown।
Sidecar persistence failures typed cleanup error হিসেবে ফেরে; record না থাকলে
unknown—successful cleanup দাবি নয়। Timestamp initial attempt-এর; separate remote
observation time নয়। Digest authenticity যাচাই করে না। Accepted receipt persist
failure-এ targeted cancellation আগের মতো automatic নয়।

Next proposed owner-directed micro-step: process-crash acceptance around durable
cancel intent/ack persistence, zero duplicate cancel after restart যাচাই। এটি শুধু
local fixture subprocess tests; live process supervisor বা paid action নয়।
Runtime/GPU/real-image 5.4 gates deferred।
