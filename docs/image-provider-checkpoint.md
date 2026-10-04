# 5.2 — ImageProvider mock contract

2026-09-28। Owner-এর next-work নির্দেশে 5.1-only exception 5.2 পর্যন্ত বাড়ানো হয়েছে।

- `animation_studio/providers/image.py`: synchronous ImageProvider Protocol,
  immutable strict ImageRequest/ImageResult, typed operational errors ও MockImageProvider।
- Request: prompt, explicit model/version, seed; bypassed model_copy-ও revalidate।
  Invalid input raises ValidationError; unsupported/cancelled/missing/invalid/I/O
  errors পৃথক ImageProviderError code।
- Result: PNG path, dimensions, SHA256, provider/model/version/seed ও explicit is_mock।
  Mock শুধু fixture-image v1 নেয়, seed/prompt নির্বিশেষে একই existing fixture ফেরায়।
- PNG format, 16 MiB byte cap, 4096² pixel cap, verify এবং full decode checks।
  No writes/network/inference; shared path caller-এর read-only হিসেবে রাখতে হবে।
- Cooperative cancellation read/decode-এর আগে-পরে; hard I/O deadline নয়।
  Artifact delivery, DB/UI integration, reference conditioning ও real workflow বাকি।
  এই in-process models persisted schema নয়; migration প্রয়োজন নেই।

## Checks

Existing FakeProvider baseline 29 PASS। ImageProvider 22 + FakeProvider regression
29 = 51 PASS। Verified output bytes/dimensions/checksum, metadata/JSON roundtrip,
immutability/revalidation, unsupported model, pre/mid-call cancellation, corrupt/
truncated/wrong-format/missing/oversized fixture, I/O error, repeatability ও
network-disabled read-only behavior covered। Ruff lint/format, plan drift ও whitespace
checks PASS। New contract tests-এর provider fixture ভবিষ্যৎ adapter-এর boundary
checks reuse করতে পারে; mock-specific tests পৃথক।

## Next ও সীমা

5.2 সম্পন্ন। পরের step 5.3 ComfyUI API-format minimal image workflow validation;
বর্তমান scoped exception 5.2 পর্যন্ত, তাই 5.3 extension প্রয়োজন। Model run/install/
download/paid action অনুমোদিত নয়। Phase 3/4 real gates ও RunPod suspension বহাল।
