# Phase 5.4 — live transport/durable identity offline contract

2026-10-04। **Design সম্পন্ন; নিচের নতুন contract implemented নয়।**
[Readiness review](comfy-readiness-review.md)-এর পরের অনুমোদিত offline micro-step।
বর্তমান mock-only guards অক্ষত। Product requirements/phase scope পরিবর্তন নয়;
এটি existing provider boundary-এর implementation design। Live enable, install,
server launch, model load বা GPU dispatch এই কাজের অন্তর্ভুক্ত নয়।

## 1. Configuration ও transport boundary

- Existing `ComfyHTTPExecutor` এবং v1 mock recovery চালু থাকবে। Future live
  composition আলাদা explicit factory দিয়ে হবে; import/default/environment discovery
  থেকে network client বা live mode চালু হবে না। Caller-এর `is_mock=False` flag
  একা live factory নির্বাচনের বিকল্প নয়।
- প্রথম live profile: operator-selected HTTPS origin, root path `/`, explicit
  bearer credential। URL-এ userinfo/query/fragment, non-root path, non-HTTPS scheme,
  whitespace/control characters rejected। Origin canonical form: lowercase ASCII
  DNS host (বা canonical IP), explicit effective port, trailing `/`; default 443
  ও explicit 443 একই identity। Unspecified/ambiguous host rejected।
- TLS certificate verification mandatory; redirects, environment proxy discovery,
  automatic retries ও alternate endpoint fallback বন্ধ। Auth gateway selected
  origin-এ থাকা deployment prerequisite; ComfyUI নিজে এই bearer auth দেয় এমন দাবি
  নয়। Native ComfyUI loopback bind বহাল; local HTTP/tunnel profile প্রথম contract-এ
  enabled নয়, পরে তার পৃথক verified transport contract লাগবে।
- Secret caller runtime-এ inject করবেন; URL/journal/result/repr/log-এ token বা
  token hash নয়। Header injection আটকাতে empty/CR/LF credential rejected। Token
  rotation execution identity বদলাবে না; refresh/login/retry automatic নয়।
- Mock tests future live configuration যাচাই করতে পারবে, কিন্তু fake transport-এর
  image সবসময় `is_mock=True`। Real provenance কেবল real transport composition থেকে;
  server JSON, filename বা journal-এর unchecked flag থেকে নয়।
- Existing JSON/image byte caps, MIME checks, poll bounds ও cooperative deadlines
  বহাল। Auth failure-এ typed `execution_failed`, sanitized message; response body/
  credentials echo নয়। Hard wall-clock/resource supervision পৃথক execution gate।

## 2. Identity record (প্রস্তাবিত v2)

Strict, immutable, extra-field-rejecting record; duplicate JSON keys rejected।
Existing graph fingerprint algorithm অপরিবর্তিত থাকবে, যাতে v1 পাঠে drift না হয়।

| Field | Contract |
| --- | --- |
| `schema_version` | Exact integer `2`; bool/unknown version rejected |
| `mode` | `mock` অথবা `live`; executor composition-এর সঙ্গে exact match |
| `job_id` | Canonical UUID; একই logical job-এর retry/recovery-তে অপরিবর্তিত |
| `graph_sha256` | Existing validated graph fingerprint; lowercase 64 hex |
| `origin` | উপরের canonical, credential-free origin |
| `deployment_id` | Operator-controlled canonical UUID; selected server/history namespace-এর identity |
| `runtime_manifest_sha256` | Verified deployment runtime manifest-এর exact bytes SHA256 |
| `model_manifest_sha256` | Verified selected model manifest-এর exact bytes SHA256 |
| `state` | `intent` অথবা `accepted` |
| `prompt_id` | Intent-এ null; accepted-এ canonical UUID |

Deployment ID শুধু URL alias নয়: replaced server/history store হলে নতুন ID;
same ID reuse কেবল history continuity verified হলে। Manifest digest trusted
operator configuration/evidence থেকে আসবে। এগুলো remote attestation নয়; arbitrary
server response-এর digest গ্রহণ করে gate pass করা যাবে না। Secret, raw prompt,
full response ও media journal-এ থাকবে না।

Job registry-এর minimal boundary হবে private journal root-এর deterministic
`<job_id>.json` ও স্থায়ী lock inode। Caller arbitrary filename দিয়ে একই job retry
করতে পারবেন না। নতুন job ID দিয়ে একই prompt পাঠানো আলাদা intentional generation;
এই design global prompt deduplication/exactly-once server execution দাবি করে না।

## 3. Write/read এবং backward compatibility

- v1 reader ও existing mock journal format বজায় থাকবে; accepted v1 record শুধু
  legacy mock path-এ recover হবে। Optional `prompt_id`-বিহীন v1 intent আগের মতো
  unknown থাকবে। v1-কে live হিসেবে পড়া, implicit v2 promotion বা in-place rewrite
  নিষিদ্ধ; হারানো identity অনুমান করে backfill নয়।
- New v2 jobs নতুন deterministic path-এ লিখবে। Version dispatcher আলাদা strict
  model নির্বাচন করবে; unknown version/corrupt data/mode mismatch-এ কোনো I/O নয়।
  Existing 4096-byte read cap বহাল; serialization cap check write-এর আগেই হবে।
- Migration policy হলো dual-read/explicit-new-write; old file preservation। Backend
  DB schema বদলাবে না। Implementation-এ v1 accepted/intent fixtures ও migration
  compatibility tests বাধ্যতামূলক। এই design-এ schema code পরিবর্তন হয়নি।
- Recovery caller original job context দেবেন; graph, job, mode, origin, deployment
  এবং recorded manifests match না হলে HTTP-এর আগেই reject। Original deployment
  mapping অনুপস্থিত হলে recovery blocked; অন্য endpoint-এ receipt পাঠানো নয়।
- Recovery-তে recorded identity compare হবে, নতুন node inventory/model availability
  check নয়। Server-এর current model বদলালেও original execution context সংরক্ষিত
  এবং history namespace continuity verified থাকলে saved output পড়া যাবে।

## 4. Dispatch/recovery state contract

| অবস্থা | অনুমোদিত action / durable ফল |
| --- | --- |
| New job | Local validation → job lock → existing-record guard → execution readiness/inventory → cancellation check → intent fsync → one submit |
| Preflight failure | Intent/POST নেই; ঠিক করার পরে একই job-এ explicit retry |
| Intent persisted | Submit outcome unknown ধরে রাখা; crash-before-send হলেও automatic resubmit নয় |
| Valid receipt | Atomic accepted write + file/directory fsync, এরপর bounded history/view reads |
| Receipt lost/malformed বা receipt-write failure | Intent preserved, outcome unknown; নতুন filename/job ID দিয়ে automatic retry নয় |
| Accepted recovery | Same identity + lock + validated record; history/view GET-only; no submit/cancel/inventory |
| Auth/timeout/network failure | Original journal preserved; no fallback/retry; accepted হলে পরে explicit recovery |
| Invalid/missing media | Image success নয়; accepted journal রেখে পরে explicit recovery সম্ভব |

Receipt-less outcome এই contract-এ স্বয়ংক্রিয় reconcile হবে না। Operator investigation
ছাড়া record delete করে পুনরায় submit নয়। Client job ID কোনো server idempotency
key guarantee নয়। Existing targeted cancellation কেবল validated receipt-এ;
acknowledgement stop proof নয়। Recovery cancellation local reads থামায়, server-এ
POST নয়। Durable cleanup observation ও supervisor implementation এখনও আলাদা gap।

## 5. Implementation acceptance matrix (এখন চালানো হয়নি)

| Test group | প্রয়োজনীয় evidence |
| --- | --- |
| Endpoint/auth | Canonical equality; rejected URL forms/schemes; missing/header-injection secret; TLS/redirect/proxy/retry settings; credential absent from errors/repr/journal |
| Identity | Every field mismatch fails before transport; token rotation identity-neutral; mock/live provenance mismatch rejected |
| Backward read | v1 accepted recovery, omitted-receipt intent, unchanged bytes, no live promotion; unknown/bool version/duplicate keys/oversize rejected |
| Durable ordering | Same-job concurrency exclusion; deterministic path; preflight failure no intent; fsync before single submit; crash/lost receipt no resubmit |
| Recovery/result | Original context/history continuity; inventory unavailable recovery; GET-only timeout/cancel; identical PNG verification/model/seed/checksum; fake output remains mock |

এই matrix future tests-এর specification; current test results নয়। Source review:
[HTTP executor](../animation_studio/providers/comfy_http.py),
[journal](../animation_studio/providers/comfy_journal.py),
[durable provider](../animation_studio/providers/comfy_durable_image.py),
[existing journal tests](../tests/test_comfy_journal.py)। Existing 226 PASS checkpoint
শুধু বর্তমান mock path-এর baseline; live contract acceptance নয়।

## Outcome / next

Endpoint/auth/provenance, v2 identity, v1 preservation ও ambiguous-submit policy
নির্দিষ্ট হয়েছে। Docs links/whitespace, RESUME length ও plan drift checks এই step-এর
verification; application tests প্রয়োজন নেই, source অপরিবর্তিত।

পরের একক micro-step: **offline v2 identity record ও versioned reader contract/tests**;
network factory/journal writer migration/live dispatch একসঙ্গে নয়। Existing
GPU-independent development authorization-এর মধ্যে এই implementation করা যাবে।
Runtime/GPU verification prerequisites না আসা পর্যন্ত deferred; 5.4 real-image
acceptance অসম্পূর্ণ, 5.5/new phase বা paid launch অনুমোদিত নয়।
