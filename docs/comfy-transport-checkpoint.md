# Phase 5.4 — L2 transport factory/lifecycle

2026-10-08। Owner next-work নির্দেশে [transport contract](comfy-live-transport-contract.md)
এর L2 standalone implementation সম্পন্ন।

[Source](../animation_studio/providers/comfy_transport.py): explicit production
factory config revalidate করে verified HTTPS HTTPTransport (trust_env=False,
retries=0) ও no-redirect client তৈরি করে। Constructor-এ dispatch নেই; production
factory injected transport নেয় না। পৃথক offline factory exact MockTransport নেয়,
is_mock=True। Existing executor/auth/storage live gates পরিবর্তিত হয়নি।

L1 policy dispatch-এর আগে চলে; finite absolute deadline ও cancellation check,
per-I/O timeout initial remaining budget-এ capped। Request একবার; no redirect/
retry/refresh। Response identity encoding, declared/streamed 16 MiB cap; bytes ও
content_type ফেরায়। JSON/MIME/media interpretation existing caller/parser-এর কাজ;
এই standalone layer সেটি duplicate করে না। TLS/auth/timeout/read failure bounded
public error; raw transport text traceback-এ নয়।

Owned response cleanup success/failure/interrupt-এ চেষ্টা হয়। Cleanup failure-এ
primary error থাকে এবং cleanup_handle দিয়ে caller resource ধরে রাখে; subsequent
request বন্ধ। Client close idempotent on success; failure-এ underlying transport
retained, কারণ HTTPX নিজে closed flag আগে set করে। Caller close দিয়ে cleanup
পুনরায় চেষ্টা করতে পারে; এটি job resubmit নয়। Remote job stopped দাবি নেই।

## Checks

[Tests](../tests/test_comfy_transport.py): **34 cases**, combined **271 PASS**:

```sh
.venv/bin/python -m pytest -q tests/test_comfy_transport.py tests/test_comfy_request_policy.py tests/test_comfy_auth.py tests/test_comfy_config.py tests/test_comfy_identity.py
```

Baseline L1/auth/config/identity 237 PASS reused। Socket/DNS forbidden fixture;
production factory construction/close only, requests mock-only। Selected origin/
bearer/body/timeouts, TLS/proxy/retry configuration, redirect/auth/server failure,
ambiguous transport error single call, invalid zero-dispatch, cap/compression,
deadline/cancel before/during stream, interrupt, response/client cleanup failure,
handle retention ও existing executor rejection verified। Ruff/docs checks PASS।

## Limits ও next

Actual TLS handshake/auth server/network/model/GPU test হয়নি। Timeout প্রতিটি I/O
phase-এর initial budget; চলমান synchronous read-এর timeout প্রতি chunk-এ কমানো হয়
না। Cooperative deadline checks chunk-এর আগে/পরে, hard streaming wall-clock cap নয়।
Independent production supervision এখনও দরকার। Single-owner synchronous use;
concurrent request/close support দাবি নয়। Trusted mock handler headers দেখতে পারে।

Next owner-directed L3 shared executor boundary composition/provenance tests,
offline-only; byte/content_type result existing parser-এ যুক্ত করা, route validation
consolidation ও fixture provenance বজায় রাখা। Live workflow admission/storage,
real target capability ও GPU gates unresolved; L2 factory একা সেগুলো পূরণ করে না।
