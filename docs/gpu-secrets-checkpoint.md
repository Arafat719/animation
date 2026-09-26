# Phase 4.5 — secret loading ও log redaction

2026-09-25। অনুমোদিত micro-step 4.5 সম্পন্ন।

- [gpu_secrets.py](../animation_studio/providers/gpu_secrets.py): শুধুমাত্র
  ANIMATION_GPU_TOKEN environment variable load; missing/empty/nonprintable value
  fail-closed। Error value echo করে না; SecretStr-এর সাধারণ str/repr masked।
- HTTPGPUProvider.from_env এবং mock worker create_app_from_env ব্যবহার করলে token
  load ও বর্তমান logging handlers-এ redaction configure হয়। Explicit-token constructors
  backward-compatible; তাদের caller-কে configure_gpu_logging নিজে করতে হবে।
- Formatter existing output format রেখে final text redact করে: messages, formatting
  args, headers, extras, exception/stack text, raw/URL-encoded/Python-repr/JSON-escaped
  known token variants। Rotation-এর পরে পুরোনো registered token-ও masked থাকে।
- Root ও বর্তমান animation_studio/httpx/httpcore/uvicorn handler outputs protected;
  নতুন handler বা logging reconfiguration-এর পরে আবার configure করতে হবে। Logging
  level/destination বদলায় না; root handler না থাকলে stream handler তৈরি করে।

## Local usage

Token shell history-তে লিখবে না; terminal-এ hidden input থেকে process environment দাও:

```bash
read -rs -p 'Local GPU token: ' ANIMATION_GPU_TOKEN
export ANIMATION_GPU_TOKEN
.venv/bin/uvicorn animation_studio.workers.mock_gpu:create_app_from_env --factory --host 127.0.0.1 --port 8091
unset ANIMATION_GPU_TOKEN
```

Client-এ একই environment token দিয়ে
`HTTPGPUProvider.from_env('http://127.0.0.1:8091')` context manager ব্যবহার করা যায়।
Token কোনো tracked config/.env/source-এ রাখা হয়নি। বাস্তব credentials পড়া হয়নি।

## Checks ও সীমা

- [Secret tests](../tests/test_gpu_secrets.py) + GPU/budget/HTTP/retry regression:
  **157 PASS**, 2 existing dependency warnings। Ruff format/lint PASS।
- Missing/invalid env, masked repr, header/JSON/bytes escaping, traceback, token
  rotation, real env-factory authentication এবং client wire/log separation verified।
- Existing 4.4/4.3 checkpoints baseline; local test execution পূর্বপরিচিত sandbox
  thread সীমার জন্য। Plan drift/links/RESUME length/whitespace PASS।
- Raw in-memory LogRecords, print/stdout, custom serializers, unregistered secrets
  বা আলাদাভাবে configured handlers covered নয়। SecretStr encryption নয়; process
  memory/environment থেকে privileged access ঠেকায় না। Token expiry/rotation service
  নেই; deployment secret manager ও production logging integration ভবিষ্যৎ scope।
- Full app/media suite নয়; dependencies/production API/UI/DB/public schema অপরিবর্তিত।
  Unrelated edits অক্ষত; paid action/model run/download/commit হয়নি।
- পরের অনুমোদিত micro-step **4.6 RunPod adapter skeleton**, mock responses-এ tests।
  Real resource launch approval ও Phase 3 deferred real acceptance বহাল।
