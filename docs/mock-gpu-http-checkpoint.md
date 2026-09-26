# Phase 4.2 — fake remote GPU HTTP server

2026-09-25। অনুমোদিত micro-step 4.2 সম্পন্ন।

- [Server factory](../animation_studio/workers/mock_gpu.py) পৃথক FastAPI app;
  existing GPU models/MockGPUProvider ব্যবহার করে। Production API/DB wiring বদলায়নি।
- GET /health, GET /capabilities, POST /jobs (202), GET /jobs/{id}, POST /cancel।
  Cancel body: {"job_id":"mock-gpu-1"}; submit GPUJobRequest contract অনুসরণ করে।
- প্রতিটি endpoint-এ caller-supplied Bearer token প্রয়োজন; খালি token-এ app তৈরি
  হয় না। Validation/provider errors-এ code ফেরে, raw input echo হয় না।
- OpenAPI/docs ও remote advance endpoint নেই। Python-injected provider.advance()
  test control; polling read-only। Jobs memory-only; restart-এ state হারাবে।
- CLI চালাতে স্থানীয় terminal-এ নিচের snippet ব্যবহার করা যায়; token prompt hidden।
  Real remote deployment নয়; shared production secret loading/redaction 4.5-এ বাকি।

```python
import getpass
import uvicorn
from animation_studio.workers.mock_gpu import create_app

app = create_app(token=getpass.getpass('Local mock worker token: '))
uvicorn.run(app, host='127.0.0.1', port=8091)
```

## Checks ও সীমা

- Baseline: 4.1-এর 50 PASS evidence; GPU source অপরিবর্তিত।
- [HTTP tests](../tests/test_mock_gpu_http.py) + GPU contract tests: **77 PASS**।
  Auth rejection, invalid/unsupported requests, unknown IDs, app isolation,
  cancellation/terminal stability, schema round-trip ও Bengali metadata covered।
- প্রথম sandbox test 40s timeout-এ থামে; অনুমোদিত local execution-এ suite 0.71s PASS।
- পৃথক ephemeral 127.0.0.1 TCP smoke: health/submit/status/cancel PASS; server stopped।
- Ruff format/lint, excerpt drift, checkpoint links/RESUME length/whitespace PASS।
- Full app/media suite নয়; no real inference/media/artifact delivery। HTTP client
  adapter, actual timeout/retry/idempotency 4.3-এ বাকি; mock submit প্রতিবার নতুন job।
- Dependencies/public schema/model assets অপরিবর্তিত; paid action/download/commit নয়।
- পরের অনুমোদিত micro-step **4.3 timeout/retry/idempotency**; simulated network
  failure tests প্রয়োজন। Phase 3 real acceptance deferred এবং বহাল।
