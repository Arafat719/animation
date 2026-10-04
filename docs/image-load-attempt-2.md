# 5.4 — Streaming load-only attempt 2

2026-09-29। One authorized run; attempt-1 preserved. No retry or inference.

## Preflight

MemAvailable 12,177,399,808 bytes (~11.34 GiB), swap unused; disk available
98,950,152,192 bytes (~92.15 GiB). Existing snapshot/runtime inventory and
unchanged loader/guard 77-test evidence reused. Output directory absent and
confirmed git-ignored. Same 300s / 24 GiB address space / sampled 8 GiB RSS /
2 GiB host reserve limits; CPU/offline mode, no install/download/paid resource.

```sh
.venv/bin/python -m scripts.image_load_probe --load --output data/image-load-probe/attempt-2
```

## Result

**FAIL: child_failed / RuntimeError**. Elapsed 15.8094s; sampled peak RSS
1,146,662,912 bytes (~1.068 GiB); child return code 1, CLI exit 1.
Supervisor completed its child wait/reap path. Evidence retained in ignored
`data/image-load-probe/attempt-2/result.json` and `stage.json`.

Final stage `error` overwrites the preceding operation. Harness records only
exception type and discards stderr, so failing component, message and traceback
are unknown. No reported RSS/host-memory/timeout guard breach. Lower sampled
peak does not prove full-model loading fits. No image; 5.4 remains incomplete.

## Checks and next

No automatic retry or limit increase. Previous 77 passing tests reused because
source unchanged. Plan drift, whitespace, local doc links and RESUME length PASS.
Only docs and ignored runtime evidence changed; no model-file edits or commit.

Next proposed micro-step: retain last operation and bounded exception details
in the harness with synthetic regression tests, without loading SDXL. Await
owner next-work direction; another real attempt is not automatically authorized.
