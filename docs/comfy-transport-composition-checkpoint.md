# Phase 5.4 — L3 offline executor composition/provenance

2026-10-08। Owner next-work নির্দেশে L3 সম্পন্ন। আগে থাকা অসম্পূর্ণ
composition source/tests সংরক্ষণ করে shared route validation ও final checks শেষ।

[Executor](../animation_studio/providers/comfy_http.py) exact offline ComfyTransport
নেয়; production transport forged mock label দিয়েও reject হয়। Dispatch-এর আগে
provenance recheck, সব executor পথে shared L1 request policy; authenticated client
একই validator ব্যবহার করে। Identity/journal import cycle এড়াতে policy local import।
Transport caller-supplied JSON/image byte cap ও MIME stream পড়ার আগে enforce করে;
existing executor JSON/history ও image provider PNG validation reuse হয়।
Cleanup handle executor error-এ retained; executor close owned client বন্ধ করে।

[Composition tests](../tests/test_comfy_transport_composition.py) forbidden socket/
DNS fixture-এ production rejection, conflicting clients, provenance mutation,
cleanup handle ও pre-read MIME rejection যাচাই করে। Existing HTTP contract suite
plain/auth/bounded তিন পথে চলে: fixture image is_mock=True, invalid JSON/media,
receipt/cancel/failure semantics। V2 suite plain/bounded পথে mock journal ordering,
no resubmit ও GET-only recovery যাচাই করে; live storage admission যোগ হয়নি।
Shared policy-র 9 added cases foreign URL/global interrupt/path traversal-এ zero dispatch।

## Checks

Initial relevant baseline 520 PASS। Shared policy import-এর initial collection
failure root cause ঠিক করার পরে final combined **590 PASS**:

```sh
.venv/bin/python -m pytest -q tests/test_comfy_transport_composition.py tests/test_comfy_http.py tests/test_comfy_v2_executor.py tests/test_comfy_transport.py tests/test_comfy_request_policy.py tests/test_comfy_auth.py tests/test_comfy_config.py tests/test_comfy_identity.py tests/test_comfy_image.py tests/test_comfy_auth_workflow.py tests/test_comfy_preflight.py
```

Touched composition files Ruff/check-format PASS; plan excerpt drift PASS।

## Limits ও next

Actual TLS/server/GPU/inference হয়নি; live workflow/storage gate বন্ধ। Cooperative
I/O deadline hard total execution bound নয়। Existing dirty work preserved; commit নয়।
Next owner-directed L4 durable live-mode composition/backward-read + supervised
acceptance scope; implementation এখনও শুরু হয়নি। Actual target/GPU gates blocked,
paid resource/new phase approval পৃথক।
