# Phase 5.4 — offline supervision schema checkpoint

2026-10-04। Owner next-work নির্দেশে একটি pure data-contract micro-step সম্পন্ন।

## Outcome

- `comfy_supervision.py`: strict/frozen/revalidated policy; explicit target RAM,
  host reserve, device index, VRAM ও finite positive timing values। Overall budget
  includes cleanup+reap reserves, তাদের বাদে run time positive হতে হবে; staleness
  bound sample interval-এর চেয়ে ছোট নয়। Resource enforcement নয়।
- Mock-only observation schema v1: nested validated execution context-এ সাত identity
  field, canonical optional receipt, typed primary outcome, cleanup phase/0–1
  attempt, ordered integer Unix seconds (0..253402300799), independent job/worker/
  compute/storage status। Generation journal v1/v2 পরিবর্তিত হয়নি।
- Observed phase-এ mock source ও lowercase SHA256 evidence reference mandatory;
  other phases-এ statuses unknown। Cancel acknowledgement/terminal job claim-এর
  receipt mandatory; acknowledgement নিজে compute/job status বদলায় না।
- Parser exact bytes, <=4096-byte cap, duplicate keys/nonfinite JSON/extra fields
  reject করে; independently supplied original context-এর সব field মেলায়। Errors
  sanitized। Bypassed nested model instance পুনরায় validate হয়; live context reject।

## Checks

`.venv/bin/python -m pytest -q tests/test_comfy_supervision.py
 tests/test_comfy_identity.py tests/test_comfy_journal.py tests/test_comfy_storage.py`
(এক লাইনে): **262 PASS**। Ruff lint/format PASS। Two initial fixture-style lint
findings fixed; application tests প্রথম run থেকেই PASS। Unchanged broader
workflow/auth baseline 541 PASS reused; নতুন total হিসেবে যোগ করা হয়নি।
Coverage includes invalid policy types/bounds, phase coherence, ack vs stop,
independent statuses, success with unknown cleanup, all context mismatches,
mock/live boundary, immutability, duplicate/deep/oversize JSON ও exact byte cap।
Existing v1/v2 reader/storage regressions PASS। Docs/plan consistency checked।

## Limits / next

Schema validates claims, not evidence authenticity or actual stop। SHA256 reference
lookup, accepted-journal receipt matching, telemetry/fake-clock admission logic,
state transitions/attempt guard, writer/locks/fsync, process launcher ও live
transport নেই। No DB or persisted format migration; missing sidecar handling belongs
to future storage integration, not parser (None is malformed input)। Current
executor cancellation remains memory-only; no hard deadline introduced।

Next proposed micro-step: mock-only supervision sidecar storage/read compatibility
with same-job locking, bounded atomic write, absent-sidecar unknown and generation
journal preservation tests। Owner next-work নির্দেশে এই bounded implementation;
cleanup action/process launch/live enable নয়। Runtime/GPU/real 5.4 deferred।
