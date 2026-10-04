# Phase 5.4 — offline endpoint/auth configuration

2026-10-04। একটি অনুমোদিত micro-step সম্পন্ন। New `ComfyEndpointConfig`
(`comfy_config.py`) explicit HTTPS origin ও caller-supplied `SecretStr` গ্রহণ করে।

## Outcome

- Existing canonical_origin reuse: normalized HTTPS root/explicit port; invalid
  URL, userinfo/query/fragment/path/control/ambiguous host rejected। Public origin
  validation error input echo করে না। Plain string credential accepted নয়।
- Empty/whitespace/control/non-ASCII token rejected; header-safe visible ASCII
  opaque token retained as SecretStr। Auto environment loading/refresh নেই।
- Frozen/slotted configuration; token repr/comparison থেকে excluded। Token rotation
  origin/public identity বদলায় না। `public_config()` নতুন nonsecret dictionary দেয়;
  token/hash/Authorization header নেই।
- Public policy: verify_tls=True, follow_redirects=False, trust_env=False, retries=0;
  constructor policy override নেয় না। এগুলো future client-এর requirements, চলমান
  TLS/auth enforcement-এর evidence নয়। কোনো HTTP client/network/file তৈরি হয় না।

## Checks

**150 tests PASS**: 39 new configuration cases + 111 existing identity/context cases,
`.venv/bin/python -m pytest -q tests/test_comfy_config.py tests/test_comfy_identity.py`।
অপরিবর্তিত provider/executor-এর previous 401-test baseline পুনর্ব্যবহার করা হয়েছে;
এই turn-এ full suite আবার চালানো হয়নি। Ruff lint/format PASS।

Coverage: canonical origins, invalid URLs/types/credentials, fixed sanitized errors,
repr/str/log/public JSON export, rotation/immutability/policy override rejection,
client/socket/DNS forbidden construction, environment independence ও no file writes।
সব credential synthetic test values; কোনো বাস্তব secret পড়া/লেখা হয়নি।

## Limits / next

SecretStr memory-তে token রাখে; explicit get_secret_value/debugger/private memory
access redaction guarantee নয়। Supported export public_config; arbitrary serialization
বা HTTP logging policy এই step-এর অংশ নয়। Config কোনো live activation gate নয়;
existing mock-only executors/storage অপরিবর্তিত। Real 5.4 এখনও অসম্পূর্ণ।

Next authorized offline micro-step: mock-only authenticated request boundary—selected
origin-এ bearer injection, redirect/auth failure/no-retry ও secret-safe error tests।
Real transport/client factory enable নয়; install/GPU/new phase/5.5 নয়।
