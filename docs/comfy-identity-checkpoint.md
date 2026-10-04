# Phase 5.4 — offline v2 identity record/versioned parser

2026-10-04। একটি অনুমোদিত implementation micro-step সম্পন্ন।
[Design](comfy-live-contract.md)-এর identity schema ও bytes parser অংশ implemented;
live configuration/auth, journal writer migration বা network dispatch নয়।

## Outcome

- New `comfy_identity.py`: strict/frozen `ComfyJobRecordV2`, canonical UUIDs,
  lowercase SHA256s, explicit mode/version এবং coherent intent/accepted receipt।
- `canonical_origin` offline HTTPS root normalization করে; explicit port, lowercase
  ASCII host, canonical IP। Userinfo/query/fragment/path/control characters,
  malformed authority, unspecified IP ও ambiguous numeric host rejected। Stored
  v2 origin অবশ্যই canonical; parser silently journal identity rewrite করে না।
- `parse_job_record(bytes, expected_mode=...)`: 4096-byte cap, duplicate keys ও
  nonfinite JSON rejection, exact integer version dispatch, mode check। Invalid
  record-এর public ValueError content echo করে না। এটি filesystem reader নয়;
  caller bounded bytes সরবরাহ করবেন। কোনো write/network side effect নেই।
- v1 accepted/intent আগের `ComfyJobRecord` হিসেবেই ফেরে; missing optional receipt
  intent-ই থাকে। Live mode-এ v1 rejected; implicit upgrade/identity backfill নেই।
- Existing durable executor-এর v1 reader/writer/graph hash অপরিবর্তিত; v2 parser
  এখনও execution path-এ wired নয়। নতুন model-এর `mode=live` live activation নয়।

## Checks

**298 PASS**: new identity tests (72) এবং existing seven relevant suites (226)।
Command: `.venv/bin/python -m pytest -q tests/test_comfy_identity.py
 tests/test_comfy_journal.py tests/test_comfy_durable_image.py
 tests/test_comfy_http.py tests/test_comfy_image.py tests/test_comfy_workflow.py
 tests/test_image_provider.py tests/test_comfy_preflight.py` (এক লাইনে চালানো)।

New coverage: mock/live intent/accepted roundtrip, frozen records, unchanged legacy
file bytes, v1 no live promotion, required identity fields, UUID/hash/state errors,
URL canonicalization/rejection, exact byte cap, malformed/duplicate/nonfinite JSON,
mode mismatch ও sanitized parse errors। Existing subprocess restart/recovery ও
no-resubmit regressions pass। Ruff lint/format PASS। `pytest` launcher interpreter
path unavailable ছিল; existing venv-এর `python -m pytest` সফল, install প্রয়োজন হয়নি।

## Limits / next

Schema validation remote identity attestation নয়। Expected graph/job/origin/
deployment/manifest context matching এখনও caller-এর দায়িত্ব; এই parser একা recovery
authorize করে না। Deterministic job path, v2 writer/migration, live transport/auth ও
runtime/GPU gates pending। DB schema/requirements বদলায়নি; full 5.4 incomplete।

Next authorized offline micro-step: v2 record-এর সঙ্গে trusted execution context
matching helper ও mismatch tests, যাতে প্রত্যেক identity mismatch recovery-এর আগে
reject হয়। একই step-এ writer migration/live enable নয়। Owner installation/paid
resource restrictions বহাল; নতুন phase/5.5 শুরু নয়।
