# Phase 5.4 — mock-only authenticated request boundary

2026-10-04। একটি অনুমোদিত micro-step সম্পন্ন। New
`MockComfyAuthenticatedClient` explicit config + exact MockTransport গ্রহণ করে।

## Outcome

- Config পুনরায় validate করে selected HTTPS origin-এ প্রতি request bearer header
  inject করে। Narrow relative route grammar; absolute URL, authority/query/fragment,
  traversal/escaped paths rejected। Method/payload route checks আছে।
- Client verify=True, follow_redirects=False, trust_env=False; retry/fallback/refresh
  নেই। Non-200 (redirect/auth failureসহ) fixed typed error দেয়; response body/Location
  echo করে না। Transport/timeout exception sanitized, original traceback suppressed।
- Identity encoding ও 16 MiB response cap; stream context response close করে।
  Returned bytes-এর MIME/JSON/media validation এখনও caller-এর দায়িত্ব।
- Always is_mock=True; real transport rejected। Existing HTTP/durable/image paths
  অপরিবর্তিত; এই boundary এখনো তাদের সঙ্গে wired নয়। Caller close করবেন।

## Checks

**173 tests PASS**: 23 new auth-boundary cases + 39 config + 111 identity/context।
Command: `.venv/bin/python -m pytest -q tests/test_comfy_auth.py
 tests/test_comfy_config.py tests/test_comfy_identity.py` (এক লাইনে)।
Ruff lint/format PASS। Previous unchanged provider/executor 401 baseline reused।

Coverage: socket/DNS forbidden selected-origin bearer injection, proxy independence,
redirect 301/302/307/308, auth 401/403, 429/500 no-retry, timeout/read-error sanitized
traceback, route injection zero-dispatch, live-transport rejection, response byte cap।
Synthetic credentials only; no real network/install/model/GPU run।

## Limits / next

Mock transport TLS handshake/auth server verification করে না। Trusted injected
handler Authorization header দেখতে পারে; arbitrary handler/private request logging
redaction guarantee নয়। 10s I/O timeout hard streaming wall-clock cap নয়।
এই standalone boundary view query parameters বা workflow execution API নয়; existing
bounded workflow executor-এর integration আলাদা কাজ। Real 5.4 image gate pending।

Next authorized offline micro-step: authenticated mock boundary-এর সঙ্গে existing
bounded Comfy workflow executor integration, view parameter validationসহ; duplicate
HTTP parsing এড়িয়ে full preflight/submit/recovery contract tests। Live enable বা
নতুন phase নয়; runtime/GPU এবং paid-resource restrictions বহাল।
