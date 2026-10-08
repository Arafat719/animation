# Phase 5.4 — mock supervision sidecar storage

2026-10-04। অনুমোদিত bounded storage/read compatibility micro-step সম্পন্ন।

## Outcome

- New `ComfySupervisionStore` exact `ComfyJournalStore` composition দিয়ে generation
  job-এর private root, permanent lock inode ও thread ownership reuse করে। Caller
  journal.locked() ধরে রাখবেন; পৃথক sidecar lock নেই। Mock-only restriction বহাল।
- Deterministic `<job_id>.supervision.json`; read cap 4097 bytes, no-follow/nonblocking
  open ও regular-file check। শুধু অনুপস্থিত sidecar-এ None (cleanup unknown);
  corrupt/mismatched/oversize/symlink/FIFO error, silent reset নয়।
- Create-only writer: existing path overwrite নয়; serialized size/schema/original
  context revalidation-এর পরে 0600 temp file → file fsync → replace → directory
  fsync। Normal failure-এ temp cleanup; directory-fsync failure-এ visible record
  থাকতে পারে, durability unknown, create retry refused।
- Generation v1/v2 bytes পড়া/বদলানো/upgrade হয় না। Legacy sidecar absence supported;
  generation reader ও sidecar parser পৃথক। কোনো DB migration নেই।

## Checks

`.venv/bin/python -m pytest -q tests/test_comfy_supervision_storage.py
 tests/test_comfy_supervision.py tests/test_comfy_storage.py
 tests/test_comfy_identity.py tests/test_comfy_journal.py` (এক লাইনে): **275 PASS**,
including 13 new storage cases। Ruff lint/format PASS; initial imported-fixture lint
collision local fixtures দিয়ে resolved। Docs links/length/plan drift/whitespace PASS।
Coverage: absent/read/create/reopen, v1/v2 preservation, 0600 permissions, shared lock
contention/thread ownership, corrupt/oversize/mismatch/symlink/dangling/FIFO rejection,
file/replace/directory failure states, fsync order, size guard, bypassed model rejection।

## Limits / next

Create-only storage; update/transition/attempt dispatch guard নেই। Schema evidence
claim যাচাই করে, stop proof নয়; generation accepted receipt-এর সঙ্গে sidecar receipt
মেলানো হয়নি। Caller-trusted root ancestors; abrupt crash temp orphan cleanup নেই।
এই step-এর restart test new instance দিয়ে persisted read; নতুন process-crash test নয়।
No cleanup action, process launch, real transport, model/GPU run; executor-এ wired নয়।

Next proposed owner-directed micro-step: mock sidecar cleanup state transitions ও
attempt guard, accepted receipt matchingসহ; no network/process action। Runtime/GPU
ও real 5.4 pending; paid-resource/new-phase restrictions বহাল।
