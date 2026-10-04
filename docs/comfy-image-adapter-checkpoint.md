# Phase 5.4 — offline ImageProvider adapter

2026-10-03। Owner GPU আসা পর্যন্ত GPU-independent development চালাতে বলেছেন।
একটি micro-step: injected workflow executor-এর সঙ্গে `ComfyImageProvider` boundary
সম্পন্ন। Live HTTP executor/server integration এই checkpoint-এর অংশ নয়।

- Existing SDXL-Turbo graph builder দিয়ে request থেকে workflow তৈরি; unsupported
  model/revision execution-এর আগেই rejected। Model/seed result-এ retained।
- Executor explicit injection; কোনো default network client বা automatic retry নেই।
  Executor trusted configuration-এ `is_mock` ঘোষণা করে; fake output mock-ই থাকে।
- Output bytes maximum 16 MiB; PNG verification/full decode, exactly 512x512 এবং
  single frame required। Valid output unique temporary-name PNG-তে save; checksum
  recorded, previous output overwrite নয়। Successful output caller-read-only।
- Cancellation before/after execution, after decode এবং after save checked;
  cancelled newly saved file removed। Timeout/I/O execution errors typed;
  executor-এর ImageProviderError propagated। No exception converted to success।
- Executor bounded download/timeout/cancellation-এর দায়িত্ব নেবে। Adapter-এর
  byte check returned bytes-এর উপর; এটি network streaming memory cap নয়।
- Model identity workflow mapping-এর declaration; remote weights attestation নয়।
  Live executor, authentication, submission/history/download, remote pin verification,
  runtime preflight ও real GPU/image evidence deferred। API artifact delivery পৃথক।

Checks: baseline 51 PASS; final workflow/provider/adapter **74 PASS**। একই shared
contract tests mock ও fake-executor adapter-এ verified PNG/metadata/cancellation/
invalid request যাচাই করে। Additional tests: no network, unique outputs, wrong
format/dimensions, corrupt/oversize bytes, unsupported model, timeout/failure with
one execution, cancellation cleanup ও output I/O failure। Ruff lint/format ও
plan excerpt drift PASS। কোনো install/download/model load হয়নি।

Next GPU-independent micro-step: bounded ComfyUI transport implementation with
fake HTTP tests; current owner scope permits offline development। Live dispatch
default enable নয়; real runtime verification GPU availability পর্যন্ত deferred।
Phase 5.4 real-image acceptance এখনও incomplete।
