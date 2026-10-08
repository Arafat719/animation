# Phase 5.4 — Comfy image readiness/gap review

2026-10-08। L4.4 পর্যন্ত consolidated readiness review; [বর্তমান gap review](comfy-live-admission-review.md)।
**Offline mock path প্রস্তুত; real image execution প্রস্তুত নয়; 5.4 অসম্পূর্ণ।**
এই review source ও existing checkpoint evidence-এর; নতুন runtime probe বা test run নয়।
পুরোনো checkpoint-এর “next” ও সীমাগুলো সেই সময়ের অবস্থা; নিচেরটি বর্তমান সংকলন।

## সম্পন্ন evidence

| অংশ | যাচাইকৃত অবস্থা ও প্রমাণ |
| --- | --- |
| Workflow/profile | Seven-node, 512×512, batch 1, steps 1, CFG 1; prompt/seed ও pinned model mapping; [workflow checkpoint](comfy-workflow-checkpoint.md) |
| Runtime/dependencies | Pinned checkout, 107 installed versions, pip check ও চার native package import PASS; full server/GPU নয়; [installed evidence](comfy-local-preflight.md) |
| HTTP/image boundary | Injected MockTransport only; bounded response/polling, verified PNG/full decode/checksum/model/seed/mock provenance; [HTTP](comfy-http-checkpoint.md), [adapter](comfy-image-adapter-checkpoint.md) |
| Durable cancellation | Same-lock sidecar intent→single cancel→observation এবং crash acceptance সম্পন্ন; ack stop proof নয়; [integration](comfy-durable-cancel-checkpoint.md), [crash](comfy-cancel-crash-checkpoint.md) |
| Durable recovery | Intent/receipt fsync, exclusive lock, existing journal blocks resubmit; accepted receipt থেকে GET-only recovery ও verified save; [journal](comfy-journal-checkpoint.md), [image recovery](comfy-durable-image-checkpoint.md) |
| Mandatory preflight | Lock-এর মধ্যে inventory check → cancellation check → intent → submit; failure-এ intent/POST নেই; recovery inventory-independent; [latest checkpoint](comfy-durable-preflight-checkpoint.md) |
| v2 identity/storage | Strict versioned reader, original context matching, deterministic job-ID path, lock/fsync, v1 preservation; [context](comfy-context-checkpoint.md), [storage](comfy-storage-checkpoint.md), [executor](comfy-v2-executor-checkpoint.md) |
| Auth integration | Explicit selected HTTPS origin + bearer config, exact mock transport, safe view parameters, shared bounded parser; auth failure/no-retry ও durable GET-only recovery verified; [checkpoint](comfy-auth-workflow-checkpoint.md) |
| R1–R7 resource decisions | Strict mock identity/freshness, RAM/VRAM boundaries ও shared deadline evaluator; measurement/enforcement নয়; [checkpoint](comfy-resource-guard-checkpoint.md) |
| P1–P3 dummy supervision | Fixed owned child stop/kill/bounded reap, synthetic telemetry, unrelated child isolation; [checkpoint](comfy-dummy-supervisor-checkpoint.md) |
| I1 child-exit acceptance | Test-only mock executor substitution; four kill boundaries, fresh GET-only recovery/no duplicate submit/cancel; production composition নয়; [checkpoint](comfy-supervised-recovery-checkpoint.md) |

| Local RAM reader | Owned PID/start ticks, bounded procfs parsing, direct-child RSS/MemAvailable; VRAM unknown; [checkpoint](comfy-ram-telemetry-checkpoint.md) |
| C1–C3 CPU dummy integration | Pure CPU guard, serialized sampler, bootstrap/first admission, stop/kill/reap ও normal-return cleanup handles; [C1](comfy-cpu-guard-checkpoint.md), [C2](comfy-ram-sampler-checkpoint.md), [C3](comfy-cpu-dummy-checkpoint.md) |

Historical C3 evidence 315 PASS; exceptional cleanup fix-এর পরে 320 PASS।
L4.1 storage 290, L4.2 supervision 337, L4.3 session 113 PASS checkpoints reused;
overlapping counts যোগ করা নয়। Latest review-তে test/runtime probe rerun হয়নি।

## Real execution-এর বাকি gates, dependency order

| Gate | বর্তমান gap | Pass evidence / boundary |
| --- | --- | --- |
| 1. Installed runtime + GPU | Installed dependency ও pin checks PASS; CUDA unavailable/count 0; [local evidence](comfy-local-preflight.md) | Owner-installed interpreter/checkout-এর exact pin, dependency/native imports, driver/libraries ও bounded tiny CUDA operation PASS; install owner করবেন |
| 2. Model registration + server validation | Local snapshot verified হলেও target runtime alias/weights identity ও native loading unverified | Target snapshot manifest/checksum, `sdxl-turbo` registration, actual six-class object_info ও native prompt validation; metadata check-কে model load বলা যাবে না |
| 3. Live transport + durable identity | Standalone production transport ও live generation/supervision storage আছে; workflow executor/session এখনও mock-only; [L4.4 review](comfy-live-admission-review.md) | Explicit real transport composition, actual TLS/auth gateway verification, accurate real provenance ও trusted deployment/model evidence; v2 identity/backward-read mock tests completed, live integration বাকি |
| 4. Supervised execution/recovery | Durable cancellation ও offline R/P/I acceptance PASS; local direct-child CPU RAM telemetry আছে; GPU/remote telemetry, process-tree enforcement ও production supervised executor composition নেই; receipt হারালে outcome unknown | CPU RAM/GPU VRAM/time bounds, server stop/cleanup verification, same-job journal retention ও ambiguous outcome-তে no resubmit; paid host হলে launch/budget/lifecycle approval আগে |
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

## C3 review finding — exceptional cleanup ownership (resolved)

[Source](../animation_studio/providers/comfy_cpu_dummy_integration.py)-এ cleanup_child/
cleanup_sampler শুধু normal return-এর CpuDummyResult-এ যোগ হয়। Parent loop বা setup
exception হলে finally cleanup চেষ্টা করে, তারপর exception propagate হয়; result
construction চলে না। একই সময়ে read আটকে থাকলে close unknown হলেও caller session
handle পায় না। Worker reap অসম্পূর্ণ থাকলেও একই ownership gap। Signal/cleanup
exception হলে পরের cleanup action-ও বাদ পড়তে পারে।

এটি source control-flow finding; এই review fault injection চালায়নি। Existing setup
failure test দ্রুত reaped child যাচাই করে; hung sampler + parent failure বা cleanup
action exception cover করে না। Normal-return hung-read tests PASS evidence বহাল।
তাই C3 checkpoint-এর bounded cleanup বক্তব্য exceptional paths-এর পূর্ণ acceptance নয়।

## Review-এর নির্ধারিত fix (এখন সম্পন্ন)

Completed reader/C1/C2/C3 happy-path কাজ restart নয়। **পরের একক micro-step:
C3 exceptional cleanup ownership bug fix ও targeted regression tests।**

- Parent exception + blocked sampler বা unconfirmed worker হলে caller-এর জন্য
  retained cleanup session পৌঁছাতে হবে; original error লুকানো যাবে না।
- এক cleanup action ব্যর্থ হলেও অন্য independent cleanup চেষ্টা করতে হবে;
  original absolute final deadline reset বা unbounded wait নয়।
- Existing normal result/API behaviour, mock-only fixed child ও no-retry scope বজায়।
- Tests: injected parent error after sampler starts + blocked read; cleanup action
  failure; unknown worker retention। Fixtures শেষে blocked reads release/join এবং
  owned child reap; private exception text public outcome/reasons-এ নয়।

2026-10-08 owner next-work নির্দেশে উপরের fix সম্পন্ন:
[cleanup checkpoint](comfy-cpu-cleanup-checkpoint.md)। Original exception-এ retained
cleanup session; independent cleanup attempts, private error details ও unchanged
deadline। Five new regressions-সহ combined 320 PASS; এই finding closed।

পরের pending real micro-step available GPU environment-এ bounded CUDA/native
preflight; existing authorization বহাল। Dependency installation সম্পন্ন;
hardware/environment বদলের তথ্য ছাড়া GPU probe পুনরাবৃত্তি নয়। Real 5.4 এখনও
blocked: target CUDA operation → model/server validation → live transport/
supervised composition → valid real PNG। 5.5/new phase/paid launch অনুমোদিত নয়।

## Owner-confirmed offline next scope — 2026-10-08

Owner GPU নেই নিশ্চিত করে [live transport offline design](comfy-live-transport-contract.md)
অনুমোদন করেছেন; design সম্পন্ন। Next owner-directed L1 pure request-policy
validator/tests; production transport/live storage/dispatch disabled থাকবে।
এটি উপরের GPU-dependent real preflight-এর বিকল্প acceptance নয়।

L1 owner নির্দেশে [সম্পন্ন](comfy-request-policy-checkpoint.md): 237 tests PASS।
Next owner-directed scope L2 factory/lifecycle offline tests; GPU/live gates বহাল।

L2 owner নির্দেশে [সম্পন্ন](comfy-transport-checkpoint.md): standalone transport
factory/lifecycle, 271 tests PASS। Existing executor/storage live gates intact;
actual TLS/server/GPU evidence নেই। Next L3 offline composition/provenance।

## L4.4 current outcome — 2026-10-08

[Review](comfy-live-admission-review.md) সম্পন্ন। L4.1/L4.2 standalone live data
support ও L4.3 offline composition complete; production live executor/remote
supervision acceptance নয়। পুরোনো “next” entries historical। Next real step existing
scope-এ available GPU environment-এর bounded preflight; owner-confirmed GPU absent
বলে blocked। Environment বদল ছাড়া পুনরায় probe নয়। Live dispatch/নতুন phase বন্ধ।
