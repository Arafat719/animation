# Phase 5.4 — prompt-scoped cancellation ও receipt handling

2026-10-03। Owner next-work নির্দেশে একটি GPU-independent micro-step সম্পন্ন।
Existing mock-only Comfy HTTP executor-এ validated receipt-এর জন্য targeted
cancellation যোগ; live transport, install ও model execution হয়নি।

## Behavior

- Valid submit acknowledgement-এর canonical UUID immutable `ComfyReceipt`-এ থাকে।
  Execution failure-এ `ComfyExecutionError` (existing `ImageProviderError` subclass)
  original code/message/cause, receipt এবং independent cancellation observation
  প্রকাশ করে। Success-এর bytes/ImageProvider contract অপরিবর্তিত।
- Cancellation/timeout-এর সময় valid receipt থাকলে একবার
  `POST /api/jobs/{prompt_id}/cancel`; global interrupt/queue clear নয়।
  Cleanup-এর আলাদা 5s cooperative deadline, original cancellation event উপেক্ষা
  করে। HTTP timeout প্রতি I/O phase; hard wall-clock guarantee নয়। Retry নেই।
- Strict boolean `cancelled=true` মানে server cancellation dispatch করেছে;
  `false` মানে no-op। কোনোটিই terminal execution/compute stop-এর proof নয়।
  Malformed response/HTTP failure/timeout হলে `dispatched=None` ও cleanup
  `error_code` থাকে; original failure বদলায় না বা success হয় না।
- Submit শুরু হওয়ার আগে cancellation হলে I/O নেই। Submit চলাকালে local cancel
  এলে original bounded deadline-এর মধ্যে receipt পড়া শেষ করার চেষ্টা হয়, যাতে
  acknowledgement পাওয়া গেলে prompt-টি cancel করা যায়। Receipt lost/invalid বা
  receipt read deadline পেরোলে identity unknown থাকে; arbitrary cleanup হয় না।
- Receipt প্রতি call-এর local state; reused executor আগের receipt দিয়ে cancel
  করতে পারে না। Non-cancellation operational failure-এ receipt retained, automatic
  cleanup নয়। Durable storage/restart recovery ও cross-call deduplication বাকি।

Protocol checked against pinned ComfyUI
[prompt-scoped cancellation route](https://github.com/Comfy-Org/ComfyUI/blob/6b747c0428c343e1417219641db93a4fb7cb69ae/server.py#L861):
queued/running job target করে; finished/unknown ID no-op। এটি source verification;
বাস্তব server lifecycle acceptance নয়।

## Checks ও next

Baseline 123 PASS; final **141 PASS** across `test_comfy_http.py`,
`test_comfy_image.py`, `test_comfy_workflow.py`, `test_image_provider.py`।
18 new cases: cancellation during submit/history/download, true/false ack,
cleanup timeout/disconnect/HTTP/malformed/schema failures, fresh cleanup budget
after primary expiry, missing receipt/no arbitrary cancellation, stale receipt
isolation ও immutable retained receipt। Existing mid-stream cancellation test এখন
history stream-এ চলে; submit receipt read-এর deferred-cancel behavior separately
covered। Ruff lint/format, plan drift এবং docs/whitespace checks PASS।

Next GPU-independent micro-step: durable submission intent/receipt recovery design
ও bounded implementation/tests, যাতে restart-এর পরে ambiguous submit অন্ধভাবে
পুনরায় না হয়। Existing offline authorization প্রযোজ্য; new phase/live dispatch নয়।
GPU runtime/native import/real image evidence deferred; Phase 5.4 incomplete।
