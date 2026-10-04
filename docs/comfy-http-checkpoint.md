# Phase 5.4 — bounded mock HTTP transport

2026-10-03। Owner-এর next-work নির্দেশে GPU-independent transport micro-step
সম্পন্ন। `ComfyHTTPExecutor` শুধুমাত্র explicitly injected `httpx.MockTransport`
গ্রহণ করে; fixed `https://comfy.invalid/` origin, `is_mock=True`, live client নেই।
Existing httpx dependency ব্যবহৃত; install/download হয়নি।

## Behavior ও evidence

- Existing exact graph validator → একবার `POST /prompt` → returned canonical UUID
  দিয়ে `GET /history/{prompt_id}` → verified node 7 reference দিয়ে `GET /view`।
  Submit retry নেই; acknowledgement হারালে outcome unknown। নতুন execute call
  নতুন submit করে; cross-call idempotency বা durable recovery এখনো নেই।
- History-এর prompt ID ও graph request-এর সঙ্গে মেলে; completed success এবং
  একটিমাত্র output image প্রয়োজন। Empty history bounded polling চালায়; malformed,
  failed বা incomplete terminal record fail করে। Output-only flat filename allowlist;
  traversal, input/temp images ও subfolder rejected।
- JSON সর্বোচ্চ 1 MiB; image সর্বোচ্চ 16 MiB; 64 KiB chunks-এ accumulated byte cap
  এবং deadline/cancel checks। Declared length-ও checked; compressed responses,
  duplicate/nonfinite JSON, unexpected MIME/status/redirect rejected।
- Default 60s cooperative deadline, প্রতি I/O phase সর্বোচ্চ 10s, সর্বোচ্চ 240 polls;
  configurable positive finite timeout/interval এবং 1–1000 polls। Slow in-flight
  I/O/MockTransport callback forcibly interrupted নয়: hard wall-clock guarantee নেই।
- Response streams failure/cancellation-এও closed। Cancellation local waiting বন্ধ
  করে; server queue/job stop request পাঠায় না। No global interrupt।
- `ComfyImageProvider` দিয়ে full fake HTTP path verified PNG save/checksum/model/seed
  metadata return করে; mock provenance বজায় থাকে। Invalid download save হয় না।

Protocol reference: pinned ComfyUI commit
`6b747c0428c343e1417219641db93a4fb7cb69ae`-এর
[server routes](https://github.com/Comfy-Org/ComfyUI/blob/6b747c0428c343e1417219641db93a4fb7cb69ae/server.py)
ও [history/status structure](https://github.com/Comfy-Org/ComfyUI/blob/6b747c0428c343e1417219641db93a4fb7cb69ae/execution.py)
এই step-এ read-only যাচাই। Live server validation নয়।

## Checks ও next

Prior baseline 74 PASS evidence reused; final **123 PASS**:
`test_comfy_http.py`, `test_comfy_image.py`, `test_comfy_workflow.py`,
`test_image_provider.py`। 49 transport tests cover full fake flow with sockets
forbidden, HTTP failures/no retries, malformed receipt/history/JSON, path rejection,
poll bounds, cancellation, deadline expiry, byte caps with/without declared length,
mid-stream stop/closure, invalid download ও live transport rejection।
Ruff lint/format, plan excerpt drift ও docs/whitespace checks PASS।

Next authorized GPU-independent micro-step: prompt-scoped cancellation/receipt
handling with fake HTTP tests। Authentication/live transport, durable restart,
remote runtime/model identity ও real image acceptance deferred; GPU/install
availability এখনও blocker। Phase 5.4 সম্পূর্ণ নয়।
