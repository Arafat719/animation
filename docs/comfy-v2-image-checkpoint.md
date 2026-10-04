# Phase 5.4 — v2 durable ImageProvider composition

2026-10-04। একটি অনুমোদিত micro-step সম্পন্ন। Existing
`DurableComfyImageProvider` এখন exact v1 অথবা v2 durable mock executor গ্রহণ করে।
আলাদা image validation implementation নয়; generate/recover উভয়ে আগের
`ComfyImageProvider` verification/save path ব্যবহার করে।

## Outcome

- V2 generation: identity/graph check, durable preflight/intent/receipt → bounded
  PNG bytes → full decode, exact 512×512, checksum, model/version/seed → saved result।
- V2 recovery: identity-matched accepted journal → GET-only history/download → একই
  image verification/save। Mock provenance অক্ষত; receipt মানেই image success নয়।
- Corrupt/truncated/JPEG/wrong-size recovery result save হয় না; previous PNG ও
  journal preserved। Save failure-এর পরে explicit recovery-তে নতুন submit লাগে না।
- Cancellation before read/during download/decode/after save পুরোনো file/journal
  অক্ষত রাখে; নতুন cancelled output cleanup হয়। Repeated recovery unique file দেয়,
  cache/overwrite নয়। Request prompt/seed mismatch HTTP-এর আগেই rejected।
- V1 behavior compatible; journal/DB/ImageResult schema, HTTP executor ও live
  configuration বদলায়নি। Caller client lifetime/output retention manage করবেন।

## Checks

**401 tests PASS** = previous 378 + 23 v2 cases। Existing durable image tests v1/v2
parameterized; shared ImageProvider contract-এ v2 যোগ। Ten relevant suites:
durable image, image provider, v2 executor, storage, identity, journal, HTTP, image,
workflow, preflight (`.venv/bin/python -m pytest -q`)।

23 additional cases: nine shared contract + fourteen durable image cases। Real
subprocess abrupt exit during download → fresh process verified saved ImageResult;
PNG decode/checksum/metadata/JSON roundtrip PASS, trace-এ one POST /prompt total।
Socket-forbidden generation/recovery checks PASS। Ruff lint/format PASS।

## Limits / next

এই ফল mock-only; real runtime/GPU/weight identity/image quality evidence নয়।
Live transport/auth factory নেই; output delivery/refresh persistence 5.5-এর পৃথক
scope। Existing cooperative deadlines/unknown intent/cleanup-stop সীমা বহাল।

Next authorized offline micro-step: [live contract](comfy-live-contract.md)-এর
endpoint/auth configuration validation ও secret-safe representation tests;
canonical HTTPS origin, explicit credential validation, no network/client creation।
Live enable/install/GPU/নতুন phase নয়; real 5.4 image gate এখনও incomplete।
