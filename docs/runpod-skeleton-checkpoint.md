# Phase 4.6 — RunPod adapter skeleton

2026-09-25। অনুমোদিত mock-only micro-step 4.6 সম্পন্ন।

- [RunPodGPUProvider](../animation_studio/providers/runpod.py) existing
  HTTPGPUProvider job contract reuse করে। Worker URL Pod ID/port থেকে HTTPS proxy
  origin; Pod control API ও worker token পৃথক SecretStr inputs।
- Control request: GET https://rest.runpod.io/v1/pods/{podId}; allowlisted snapshot
  শুধু pod_id ও desired_status দেয়। Extra fields/env বাদ; mismatched ID/malformed
  response reject। Unknown future status UNKNOWN; desired state readiness নয়।
- Control lookup single-attempt timeout ও normalized errors; job HTTP retry/
  idempotency existing contract অনুসরণ করে। Control key worker-এ যায় না।
- দুটি injected httpx.MockTransport বাধ্যতামূলক; live transport ও inherited env
  factory বন্ধ। Pod create/start/stop/delete methods নেই। Explicit fixture tokens;
  production credentials loading এই skeleton-এ নেই। Context manager দুই client বন্ধ করে।

## Official contract references

2026-09-25-এ official documentation যাচাই করে REST v1 contract নির্বাচন করা হয়েছে:

- [Find a Pod by ID](https://docs.runpod.io/api-reference/pods/GET/pods/podId):
  GET route, Bearer authorization, id/desiredStatus response fields।
- [Pod connection options](https://docs.runpod.io/pods/connect-to-a-pod):
  HTTPS Pod-port proxy hostname pattern। এই worker service-এর /jobs contract
  আমাদের application-এর; RunPod Serverless /run API নয়।

## Checks ও সীমা

- [Adapter tests](../tests/test_runpod_provider.py) existing GPU boundary tests
  import/reuse করে; health/capabilities/submit/status/cancel এবং invalid deadlines।
- Mock control responses-এ status mapping, token separation, allowlist, errors,
  timeout, malformed response, no retry ও live-transport rejection covered।
- Adapter + secrets/budget/GPU/HTTP/retry suites **214 PASS**; 2 existing dependency
  deprecation warnings। Ruff format/lint এবং docs drift/links/whitespace PASS।
- আগের 157-test evidence baseline; existing runtime source অপরিবর্তিত। Local tests
  পূর্বপরিচিত sandbox thread সীমার বাইরে চালানো হয়েছে; real RunPod API call নয়।
- Full app/media suite নয়; worker image pinning/deployment, protected artifacts,
  real readiness/inference, lifecycle/storage verification ও durable paid dispatch
  acceptance বাকি। Real API compatibility mock fixtures দিয়ে প্রমাণিত নয়।
- No dependencies/install/model download/paid action/commit; unrelated edits অক্ষত।

পরের micro-step **4.7 exact cost/action preview proposal**; শুধু read-only research/
proposal, resource creation নয়। Model/image/storage/budget-এর concrete proposal
প্রস্তুত করে paid action-এর আগে explicit approval প্রয়োজন। Phase 4 সম্পূর্ণ নয়;
Phase 3 real planner acceptance deferred এবং বহাল।
