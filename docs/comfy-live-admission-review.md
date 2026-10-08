# Phase 5.4 — L4.4 live admission/supervision gap review

2026-10-08। Owner next-work নির্দেশে source/checkpoint review সম্পন্ন; docs-only।
**Offline composition PASS; live admission NOT READY; পূর্ণ L4 ও 5.4 অসম্পূর্ণ।**

## বর্তমান evidence এবং যা এখনও বাকি

| অংশ | বর্তমান evidence | Live acceptance-এর বাকি কাজ |
| --- | --- | --- |
| Transport | [L2](comfy-transport-checkpoint.md): verified-TLS/no-proxy/no-retry standalone factory; offline fault tests | Selected target-এর actual TLS/auth, object_info/history/view এবং prompt-scoped cancel capability যাচাই |
| Durable storage | [L4.1](comfy-live-storage-checkpoint.md): live generation v2 store; [L4.2](comfy-live-supervision-checkpoint.md): separate live supervision v2, mock backward-read/no relabel | Trusted runtime/model/deployment context live executor থেকে bind করা; schema-valid claims evidence verification নয় |
| Executor composition | [L4.3](comfy-offline-session-checkpoint.md): mock session ordering, receipt/one cancel/GET-only recovery, fixture provenance, 113 PASS | HTTP executor এখনও require_mock; durable executor mock stores ব্যবহার করে। Live stores-কে executor/supervisor-এর সঙ্গে production composition করা হয়নি |
| Runtime/model | [Installed evidence](comfy-local-preflight.md): 107 versions ও native imports PASS; CUDA unavailable/count 0 | Available GPU-তে bounded native/CUDA operation, target model identity/alias, native node/prompt validation |
| RAM/VRAM/ownership | [CPU integration](comfy-cpu-cleanup-checkpoint.md): fixed dummy direct-child RAM/cleanup | Target worker/process-tree ownership, RAM enforcement, VRAM measurement/isolation limits, stale/missing telemetry failure behavior |
| Deadline/cleanup | Per-I/O cooperative timeout; retained local cleanup handle; mock durable cancel | Independent run/cleanup/reap supervision covering selected worker; preflight ও execution-এর পৃথক budgets-কে combined run policy-তে বাঁধা; local client exit remote stop নয় |
| Result | Mock PNG verification/model/seed checks | Actual image/full decode/checksum ও trusted model/seed/runtime provenance; owner visual review; API delivery 5.5 আলাদা |

এগুলো source/evidence gaps; নতুন runtime probe বা fault injection-এর ফল নয়।
L4.1–L4.3 storage/offline support পূর্ণ L4 live-mode composition-এর বিকল্প নয়।

## গুরুত্বপূর্ণ boundary

- `create_comfy_transport` standalone request করতে সক্ষম; “live বন্ধ” বলতে
  workflow admission/integration বন্ধ বোঝায়, package-wide network kill switch নয়।
  এই review কোনো request বা server launch করেনি।
- [HTTP executor](../animation_studio/providers/comfy_http.py) construction ও dispatch-এ
  mock transport check করে; [offline session](../animation_studio/providers/comfy_offline_session.py)
  live context reject করে। Flag বদলে live-ready ঘোষণা করা যাবে না।
- [Durable executor](../animation_studio/providers/comfy_v2_executor.py) এখনও mock
  generation/supervision store compose করে। Live store-এ synthetic receipt লিখে
  integration বা real provenance দেখানো যাবে না।
- [RAM reader](../animation_studio/providers/comfy_ram_telemetry.py) direct-child
  coverage ও VRAM unknown দেয়। [CPU dummy](../animation_studio/providers/comfy_cpu_dummy_integration.py)
  fixed child চালায়; arbitrary Comfy server/remote descendants supervise করে না।
- Live observation-এর source/status/digest caller claims; শুধু schema parse বা
  cancel acknowledgement actual worker/job/compute/storage stop প্রমাণ করে না।
- Same root/job context ছাড়া global deduplication নেই। Lost receipt intent retained,
  no automatic resubmit; accepted recovery GET-only, cleanup action নয়।

## পরের কাজ ও প্রয়োজনীয় তথ্য

পরের real micro-step: available owner-selected GPU environment-এ bounded runtime/
CUDA preflight। Existing 5.4 authorization বহাল, কিন্তু environment না থাকায় blocked।
Owner ইতিমধ্যে GPU নেই বলেছেন; একই local probe বা completed mock কাজ পুনরায় নয়।

Environment পাওয়া গেলে প্রথমে exact host/local-or-remote setup, interpreter ও pinned
Comfy checkout/model location শনাক্ত করতে হবে। Remote হলে নির্বাচিত HTTPS origin,
auth setup, dedicated/shared worker ownership এবং stop/telemetry capability লাগবে।
Credentials docs/journal/chat report-এ সংরক্ষণ নয়। Target/ownership না জেনে remote
supervisor design-এর deployment-specific সিদ্ধান্ত বা process kill করা যাবে না।

এরপর target অনুযায়ী live admission/supervised composition-এর একক implementation
scope নির্ধারণ করতে হবে; bounded failure/restart tests এবং actual target evidence
দুটিই প্রয়োজন। Current offline approval paid resource, >2 GB download, live launch
বা নতুন phase-এর অনুমোদন নয়। এই review কোনো নতুন phase শুরু করে না।

## Checks/outcome

Sources ও L2/L4.1–L4.3 checkpoint cross-check; readiness matrix-এর stale mock-only
storage/transport description সংশোধিত। Recent tests reused: L4.1 290, L4.2 337,
L4.3 113 PASS; overlapping suites, সংখ্যাগুলো যোগ করে unique total নয়।
Docs links/RESUME length, excerpt drift ও whitespace PASS। App tests/install/model/
GPU/server/network probe চালানো হয়নি; source/schema/requirements অপরিবর্তিত।
Review blocker নেই; live execution-এর target/hardware ও implementation gaps বহাল।

## পরবর্তী offline scope — 2026-10-08

Owner GPU-free next-work নির্দেশে [admission contract](comfy-admission-contract.md)
প্রস্তুত। Next owner-directed A1 pure evaluator/tests; target evidence collection বা
live admission enabling নয়। উপরের real preflight blocker অপরিবর্তিত।
