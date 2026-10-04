# Phase 5.4 — verified durable image recovery

2026-10-03। Owner next-work নির্দেশে durable ImageProvider integration micro-step
সম্পন্ন। New `DurableComfyImageProvider` explicit `generate` ও `recover` দেয়;
দুই path existing `ComfyImageProvider`-এর একই validation/save implementation
ব্যবহার করে। No install/model load/live GPU/network dispatch।

## Behavior

- `generate`: durable intent/receipt executor → verified PNG → ImageResult।
- `recover`: recovery-only executor bridge → existing journal/graph validation →
  GET-only history/download → একই PNG verification/full decode, exact 512x512,
  byte cap, checksum ও metadata checks → unique saved ImageResult।
- Mock provenance preserved; returned model/version/seed original request-এর।
  Journal accepted মানেই image success নয়; bytes validate না হলে result নেই।
- Corrupt/truncated/wrong-format/wrong-size media saved নয়। Cancellation before
  I/O, during download/decode এবং after save checked; newly cancelled file removed,
  previous output ও journal preserved।
- Output-save failure-এর পরে একই accepted journal থেকে explicit recovery হয়;
  নতুন submit লাগে না। Existing journal থাকলে generate এখনও blocked।
- Repeated recovery নতুন unique output file তৈরি করে, আগের output overwrite করে
  না। এটি output cache বা application artifact registration নয়; caller retention
  ও HTTP client lifetime manage করবে। DB/journal schema অপরিবর্তিত।

## Verification

166 PASS baseline reused; final **189 PASS** across six suites:
`test_comfy_durable_image.py`, `test_comfy_journal.py`, `test_comfy_http.py`,
`test_comfy_image.py`, `test_comfy_workflow.py`, `test_image_provider.py`।
23 added cases: 9 shared ImageProvider contract cases durable implementation-এ;
14 integrated success/error/cancellation/recovery/request-validation cases।

Actual subprocess abrupt exit during image download-এর পরে fresh process recovered
and saved verified ImageResult। PNG decoded/checksummed, model/seed/mock metadata
checked, result JSON roundtrip PASS; combined trace-এ **one POST /prompt**। Socket
access forbidden during that test ও in-process full-path test। Ruff lint/format,
plan drift ও docs/whitespace checks PASS।

## Remaining / next

Result checksum downloaded bytes-এর; server/model identity attestation নয়। Mock
transport ছাড়া execution enabled নয়। Lost receipt এখনও unknown; cancellation
observation durable নয়। Current journal path ধরে রাখা বাধ্যতামূলক। API/UI artifact
delivery (5.5) শুরু হয়নি; Phase 5.4 real image acceptance incomplete।

Next authorized offline micro-step: ComfyUI node/model inventory preflight-এর
mock contract, যাতে expected workflow nodes/model alias missing হলে dispatch
বন্ধ করা যায়। Real installed server/GPU preflight ও generation deferred।
