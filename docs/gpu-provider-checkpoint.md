# Phase 4.1 — GPUProvider ও local mock

2026-09-25। Owner-এর Phase 4 mock scope ও পরের কাজ শুরুর নির্দেশে 4.1 সম্পন্ন।

- [GPUProvider](../animation_studio/providers/gpu.py): synchronous Protocol;
  health_check, capabilities, submit, status, cancel; validated immutable request ও
  job snapshots, model/version/seed, progress এবং normalized boundary errors।
- MockGPUProvider memory-only; শুধু mock.noop + mock-worker/1। Explicit advance
  দিয়ে queued → running → succeeded/failed; cancel terminal jobs অক্ষত রাখে।
  Status read-only, unknown ID not_found; provider instances আলাদা।
- Mock success মানে simulated noop completion; media বা real inference নয়।
- [Tests](../tests/test_gpu_provider.py): shared boundary fixture ভবিষ্যৎ adapters-এর
  জন্য reuse করা যাবে; advance-নির্ভর lifecycle tests mock-specific।
- Baseline: existing FakeProvider/PlannerProvider inspected; নতুন GPU boundary ছিল
  না। Phase 3-এর আগের ২৫২-test evidence retained; existing source বদলায়নি।
- Check: GPU suite **50 PASS**, ruff format/lint PASS; plan excerpt drift,
  checkpoint links, RESUME length ও whitespace PASS। Full app/media suite নয়।

```sh
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_gpu_provider.py
.venv/bin/ruff check animation_studio/providers/gpu.py tests/test_gpu_provider.py
```

সীমা: HTTP server/transport নেই (4.2); deadline validation আছে, actual network
expiry/retry/idempotency 4.3-এ বাকি। Artifact retrieval, worker authentication,
compute/storage lifecycle, budget/secrets এবং real adapter পরের scope। Public
schema, DB, API/UI অপরিবর্তিত; নতুন dependencies/download/paid action/commit নেই।
পরের অনুমোদিত micro-step 4.2 fake remote GPU HTTP server। পূর্ণ Phase 4 শেষ নয়;
Phase 3 real planner acceptance deferred ও বাধ্যতামূলক।
