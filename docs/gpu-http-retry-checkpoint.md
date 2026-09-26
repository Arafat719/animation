# Phase 4.3 — HTTP timeout, retry ও idempotency

2026-09-25। অনুমোদিত micro-step 4.3 সম্পন্ন।

- [HTTPGPUProvider](../animation_studio/providers/gpu_http.py) GPUProvider-এর
  synchronous HTTP implementation: health/capabilities/submit/status/cancel;
  validated responses, request/job identity checks ও normalized errors।
- সর্বোচ্চ default 2 retries (3 attempts), configurable 0–5; exponential backoff।
  Transport failures এবং 429/502/503/504 retry হয়; auth/validation/conflict ও malformed
  response retry হয় না। Redirects/environment proxies disabled; remote HTTP rejected,
  HTTPS বা loopback HTTP origin-only URL প্রয়োজন।
- Positive finite timeout প্রতিটি network I/O phase-এ প্রযোজ্য; elapsed request
  budget retries-এর আগে ও response-এর পরে checked। Slow streaming response-এর
  কঠোর wall-clock interruption নয়। Timeout remote job cancellation বোঝায় না।
- Submit-এর এক call-এর সব retries একই generated Idempotency-Key ব্যবহার করে।
  Ambiguous failure-এর পরে caller আবার submit করলে আগের key নিজে রাখতে হবে:
  `provider.submit(request, idempotency_key='retained-operation-id')`।
- [Mock server](../animation_studio/workers/mock_gpu.py)-এ lock-সহ atomic key/request
  mapping: same key + same validated payload → existing job-এর বর্তমান status;
  different payload → 409 idempotency_conflict। Invalid key → 422।
  Header ছাড়া পুরোনো submit আচরণ বহাল: প্রতি call-এ নতুন job।
- Cancel repeatable; response হারিয়ে retry হলেও terminal status অক্ষত।

## Evidence ও সীমা

- [Retry tests](../tests/test_gpu_http_retry.py) + existing GPU/HTTP suites:
  **112 PASS**, 2 existing dependency deprecation warnings। Ruff format/lint PASS।
- Lost response after actual mock submission → একটি job; caller replay/conflict,
  concurrent 8 submissions, lost cancel response, retry cap/backoff, deadline budget,
  malformed responses ও real loopback socket read timeout verified।
- আগের 77-test checkpoint baseline হিসেবে ব্যবহৃত; local execution প্রয়োজন হয়েছিল
  পূর্বপরিচিত sandbox thread সীমার জন্য। Socket/thread শেষে বন্ধ।
- Plan excerpt drift, checkpoint links/RESUME length ও whitespace PASS।
- Existing pinned httpx/httpcore/certifi dev থেকে runtime requirements-এ স্থানান্তর;
  version upgrade বা install নয়। Production API/DB/UI wiring অপরিবর্তিত।
- Idempotency শুধুমাত্র এক mock app/process lifetime-এ। Durable deduplication,
  multi-worker coordination ও restart recovery নেই; real paid dispatch-এর জন্য
  যথেষ্ট নয়। App restart-এর পরে পুরোনো ambiguous submission retry নিরাপদ দাবি নয়।
- Full app/media suite নয়; real GPU/model run/download/paid action/commit হয়নি।
- পরের অনুমোদিত micro-step **4.4 budget config ও dry-run estimator**। Phase 3 real
  acceptance এবং Phase 4-এর real worker/artifact/resource lifecycle gates বহাল।
