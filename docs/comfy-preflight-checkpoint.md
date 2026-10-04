# Phase 5.4 — node/model inventory preflight mock contract

2026-10-03। Owner next-work নির্দেশে একটি offline micro-step সম্পন্ন।
New inventory validator, bounded HTTP `preflight` এবং opt-in
`CheckedComfyExecutor` যোগ। Existing mock transport restriction বহাল।

- Seven-node graph-এর six unique classes-এর জন্য পৃথক
  `GET /object_info/{class}`; duplicated CLIPTextEncode একবার query।
- Expected output order/types, scalar/list flags, required input names/types,
  SaveImage output-node flag এবং selected model/sampler/scheduler choices পরীক্ষা।
  `sdxl-turbo` exact choice হতে হবে; substring বা malformed combo accepted নয়।
- Existing bounded JSON reader-এর size/MIME/status/deadline/cancel checks ব্যবহার।
  ছয় read-এর shared cooperative deadline; no retries/live network।
- Checked executor প্রত্যেক execute-এর আগে preflight করে; failure-এ submit নেই।
  Success cache নয়, next execute-এ আবার পরীক্ষা। ComfyImageProvider composition
  দিয়ে verified mock PNG result test করা হয়েছে।
- এটি inventory contract, complete Comfy validation নয়: numeric option limits,
  custom validators, weights checksum/identity, GPU availability ও memory readiness
  যাচাই নয়। Alias advertisement model revision-এর proof নয়। Preflight ও submit
  atomic নয়; server state মাঝখানে বদলাতে পারে।
- Raw HTTP executor/durable path এখনো automatically gated নয়। Checked executor
  opt-in, নিজে durable duplicate protection দেয় না; আগের durable guard অক্ষত।

Reference: pinned
[ComfyUI node_info/object_info routes](https://github.com/Comfy-Org/ComfyUI/blob/6b747c0428c343e1417219641db93a4fb7cb69ae/server.py#L685)
read-only যাচাই। Test inventory synthetic; installed server capture নয়।

Checks: prior 189 baseline reused; final **219 PASS**, seven relevant provider/
workflow/HTTP/journal/durable/preflight suites। 30 new cases include missing all six
classes, wrong alias/ports/types/combos/list flags, new/missing required inputs,
HTTP/JSON/timeout/cancel failure, no stale success cache, six GETs only, sockets
forbidden full image path ও unchanged unrelated inventory। Ruff lint/format,
plan drift ও docs/whitespace checks PASS। No install/download/model/GPU run।

Next authorized offline micro-step: preflight-কে durable submission path-এ যুক্ত
করা—journal intent লেখার ও submit-এর আগে check, recovery GET-only রাখা; mock
failure/retry-boundary tests। Phase 5.4 real-image/runtime gates deferred।
