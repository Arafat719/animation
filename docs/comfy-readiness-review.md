# Phase 5.4 — Comfy image readiness/gap review

2026-10-04। Auth integration-এর পর Owner-এর next-work নির্দেশে offline review হালনাগাদ।
**Offline mock path প্রস্তুত; real image execution প্রস্তুত নয়; 5.4 অসম্পূর্ণ।**
এই review source ও existing checkpoint evidence-এর; নতুন runtime probe বা test run নয়।
পুরোনো checkpoint-এর “next” ও সীমাগুলো সেই সময়ের অবস্থা; নিচেরটি বর্তমান সংকলন।

## সম্পন্ন evidence

| অংশ | যাচাইকৃত অবস্থা ও প্রমাণ |
| --- | --- |
| Workflow/profile | Seven-node, 512×512, batch 1, steps 1, CFG 1; prompt/seed ও pinned model mapping; [workflow checkpoint](comfy-workflow-checkpoint.md) |
| Runtime specification | Exact ComfyUI commit, dependency locks, source/metadata compatibility; installed/native execution নয়; [runtime](comfy-runtime.md) |
| HTTP/image boundary | Injected MockTransport only; bounded response/polling, verified PNG/full decode/checksum/model/seed/mock provenance; [HTTP](comfy-http-checkpoint.md), [adapter](comfy-image-adapter-checkpoint.md) |
| Cancellation | Receipt-scoped cancel observation; dispatch acknowledgement execution-stop proof নয়; [checkpoint](comfy-cancellation-checkpoint.md) |
| Durable recovery | Intent/receipt fsync, exclusive lock, existing journal blocks resubmit; accepted receipt থেকে GET-only recovery ও verified save; [journal](comfy-journal-checkpoint.md), [image recovery](comfy-durable-image-checkpoint.md) |
| Mandatory preflight | Lock-এর মধ্যে inventory check → cancellation check → intent → submit; failure-এ intent/POST নেই; recovery inventory-independent; [latest checkpoint](comfy-durable-preflight-checkpoint.md) |

| v2 identity/storage | Strict versioned reader, original context matching, deterministic job-ID path, lock/fsync, v1 preservation; [context](comfy-context-checkpoint.md), [storage](comfy-storage-checkpoint.md), [executor](comfy-v2-executor-checkpoint.md) |
| Auth integration | Explicit selected HTTPS origin + bearer config, exact mock transport, safe view parameters, shared bounded parser; auth failure/no-retry ও durable GET-only recovery verified; [checkpoint](comfy-auth-workflow-checkpoint.md) |

Latest recorded baseline: **541 tests PASS**, `tests/test_comfy_*.py` ও
`tests/test_image_provider.py`, 2026-10-04। এই docs-only review-তে আগের turn-এর
সেই evidence পুনর্ব্যবহার করা হয়েছে; নতুন app test বা runtime probe নয়।

## Real execution-এর বাকি gates, dependency order

| Gate | বর্তমান gap | Pass evidence / boundary |
| --- | --- | --- |
| 1. Installed runtime + GPU | সর্বশেষ local check-এ ComfyUI/dependencies অনুপস্থিত, CUDA unavailable; [local evidence](comfy-local-preflight.md) | Owner-installed interpreter/checkout-এর exact pin, dependency/native imports, driver/libraries ও bounded tiny CUDA operation PASS; install owner করবেন |
| 2. Model registration + server validation | Local snapshot verified হলেও target runtime alias/weights identity ও native loading unverified | Target snapshot manifest/checksum, `sdxl-turbo` registration, actual six-class object_info ও native prompt validation; metadata check-কে model load বলা যাবে না |
| 3. Live transport + durable identity | Selected HTTPS origin/auth config ও v2 identity implemented; transport exact mock-only, storage `mode=mock`, wrappers `is_mock=True` | Explicit real transport composition, actual TLS/auth gateway verification, accurate real provenance ও trusted deployment/model evidence; v2 identity/backward-read mock tests completed, live integration বাকি |
| 4. Supervised execution/recovery | Standalone ComfyUI-তে app-script resource limits স্বয়ংক্রিয় নয়; cancellation observation durable নয়; receipt হারালে outcome unknown | CPU RAM/GPU VRAM/time bounds, server stop/cleanup verification, same-job journal retention ও ambiguous outcome-তে no resubmit; paid host হলে launch/budget/lifecycle approval আগে |
| 5. First real image | কোনো real PNG নেই; native Comfy loader-এর memory/latency evidence নেই | Approved bounded run-এ valid saved PNG/full decode, dimensions/checksum, model revision/seed/runtime ও real provenance recorded; anime quality owner review |

Gate 1-এর verification existing 5.4 scope-এ অনুমোদিত, prerequisites পাওয়া পর্যন্ত
স্থগিত। Gate 2–5-এর তালিকা readiness requirements; এই review live dispatch বা paid
launch-এর অনুমোদন নয়। RunPod স্থগিত; paid resource ও >2 GB download-এর পৃথক explicit
approval প্রয়োজন। Existing local snapshot-এর duplicate download প্রয়োজন নেই।

## Source review-এ নিশ্চিত সীমা

- `comfy_preflight.py` node ports/required inputs/selected combos যাচাই করে; numeric
  limits, native custom validators, GPU capacity বা weight identity যাচাই করে না।
- `comfy_journal.py` ও `comfy_v2_executor.py` mandatory preflight দেয়; raw `ComfyHTTPExecutor.execute` bypass
  করলে সেই gate/durable protection নেই। Inventory read এবং submit atomic নয়।
- Preflight/execution-এর cooperative budgets পৃথক; hard combined wall-clock cap নেই।
- Intent-only journal recovery fail-closed; v2 একই private root/job ID-তে deterministic
  path ও lock দিয়ে resubmit ঠেকায়। নতুন root/job ID-তে global deduplication নেই।
  Accepted receipt recovery পূর্বের
  history/output থাকার উপর নির্ভরশীল; বারবার recovery unique file তৈরি করে।
- `DurableComfyImageProvider` generation/recovery এখনও mock-only। Saved checksum
  output bytes-এর proof; server/model identity proof নয়। API/UI artifact registration
  ও refresh persistence 5.5-এর পৃথক কাজ, এখন অনুমোদিত নয়।

## Checks ও next

Relevant provider sources ও checkpoint ordering cross-check করা হয়েছে। Local docs
links, plan excerpt drift এবং changed-doc whitespace checks PASS; source/schema/
requirements পরিবর্তন নেই, তাই app tests/install/model load প্রয়োজন নেই।

## পরবর্তী কাজের সিদ্ধান্ত

- Completed identity/config/storage/auth কাজ restart নয়। পুরোনো
  [offline contract](comfy-live-contract.md)-এর “implemented নয়” ও “next” সেই
  design checkpoint-এর ঐতিহাসিক অবস্থা; উপরের evidence বর্তমান বাস্তবায়ন দেখায়।
- Existing authorized next execution step: owner-installed runtime/GPU পাওয়া গেলে
  Gate 1-এর exact pin/native imports ও bounded tiny CUDA verification। Owner install
  করবেন; prerequisites বদলানোর তথ্য না থাকায় পুরোনো probe পুনরায় চালানো হয়নি।
- GPU-independent প্রস্তাবিত পরের micro-step: **Comfy execution supervision-এর
  offline contract design**—RAM/VRAM/time bounds, durable cleanup observation,
  receipt-less outcome ও stop-proof acceptance matrix। এটি এখনো implemented নয়;
  পরবর্তী owner next-work নির্দেশে শুধু এই design করা যাবে, live dispatch নয়।
- এই review নতুন source feature, live transport, paid launch বা 5.5 অনুমোদন দেয় না।
  Phase 3/4-এর deferred gates এবং 5.4-এর real-image acceptance বহাল।
