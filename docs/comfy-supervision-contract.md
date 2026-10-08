# Phase 5.4 — offline Comfy supervision contract

2026-10-04। Owner-এর next-work নির্দেশে **design-only micro-step সম্পন্ন**।
এটি প্রস্তাবিত implementation contract; নিচের supervisor/schema এখনো implemented
বা live-verified নয়। Existing requirements, journal v1/v2 ও recovery আচরণ অপরিবর্তিত।

## 1. বর্তমান evidence ও ownership

[Auth integration](comfy-auth-workflow-checkpoint.md)-এর 541 PASS baseline বহাল।
[HTTP executor](../animation_studio/providers/comfy_http.py) receipt-scoped cancel
ও cooperative timeout দেয়; [v2 executor](../animation_studio/providers/comfy_v2_executor.py)
intent/receipt রাখে। Cancel observation বর্তমানে memory-only।
[Existing GPU supervisor](gpu-supervisor-checkpoint.md) একটি mock cleanup child
সামলায়; সেটি Comfy server supervisor বা remote stop proof নয়।

ভবিষ্যৎ composition-এ controller job/context ও deadline বহন করবে; executor workflow
I/O করবে; supervisor শুধুমাত্র explicitly owned worker/process সামলাবে। Remote
compute lifecycle adapter আলাদা থাকবে। Shared server বা unrelated process-এ kill,
global interrupt/queue clear নয়। Source-level mock guards সরিয়ে live করা যাবে না।

## 2. Resource ও time policy

| Policy | প্রস্তাবিত validation / enforcement |
| --- | --- |
| RAM | Positive integer byte limit ও host reserve; target host evidence দিয়ে নির্বাচন। Worker process tree-এর enforceable OS/container limit ও monitor capability live preflight-এ যাচাই; client RSS remote RAM নয় |
| VRAM | Selected device ও positive byte budget, sample interval/staleness bound; sampled use admission/abort signal, hard allocation cap-এর দাবি নয়। Backend isolation/enforcement unsupported হলে capability-তে স্পষ্ট এবং unattended acceptance blocked |
| Time | Finite positive overall run budget, cleanup reserve ও terminate/reap allowance। Preflight/submit/poll/download সব run budget-এর মধ্যে; cleanup reserve আলাদা, cancel event সেটি suppress করবে না |
| Restart | Monotonic deadline শুধু একই process lifetime-এ; persisted wall-clock timestamp দিয়ে নতুন full run budget নয়। Restart হলে generation resume নয়, accepted GET-only recovery বা explicit cleanup review |
| Missing telemetry | Stale/missing/invalid measurement-এ নতুন submit বন্ধ; running outcome unknown রেখে cleanup/manual attention। Memory/VRAM zero ধরে নেওয়া নয় |

এখন কোনো machine-specific limit অনুমান বা model run করা হবে না। Future policy-তে
সব limit explicit; NaN/inf/bool/zero/negative বা inconsistent reserve rejected।
Outer process supervision blocked stream থেকে local wait শেষ করতে পারে; client
kill remote work বন্ধ করে না। Parent/host failure ও uninterruptible kernel wait-এর
সীমা report করতে হবে; absolute wall-clock/billing guarantee দাবি নয়।

## 3. Durable cleanup observation — প্রস্তাবিত পৃথক record

Generation v2 journal rewrite/promotion নয়। ভবিষ্যৎ private same-job root-এ
`<job_id>.supervision.json`, নিজস্ব exact schema_version=1; bounded 4096-byte JSON,
strict types/extra rejection/duplicate-key rejection। Same job lock ও atomic
file+directory fsync policy reuse; observation persist failure success নয়।
Legacy job without sidecar valid থাকে; cleanup status হবে unknown।

Record-এ trusted execution context-এর সাত identity field, optional accepted
prompt_id, primary outcome code, cleanup phase, attempt count, bounded timestamps,
observation source ও independent job/worker/compute status থাকবে। Secret, raw
prompt/response, URL credentials বা arbitrary exception text নয়।

Cleanup phases: `not_requested`, `intent`, `observed`, `unknown`। Status fields
আলাদা: job `unknown/terminal`; owned worker `unknown/exited`; compute
`unknown/stopped/absent`; storage `unknown/present/absent`। Mock evidence সবসময়
mock provenance পাবে। Terminal observation-এর evidence reference identity-matched
local record নির্দেশ করবে; caller-supplied status flag stop proof নয়।

Cleanup attempt intent action-এর আগে persist হবে। Initial contract-এ একই job-এর
এক automatic attempt; crash/timeout/ambiguous acknowledgement হলে restart আর POST
করবে না। Existing executor-এর এক cancel attempt এবং supervisor-এর action একই
ownership boundary-তে রাখতে হবে, যাতে integration-এ duplicate cancel না হয়।
এই atomic ordering বসানো আলাদা implementation; বর্তমান memory-only path সেটি দেয় না।

## 4. State ও stop-proof contract

| অবস্থা | ফল / অনুমোদিত আচরণ |
| --- | --- |
| Preflight failure | Submit নয়; generation intent নেই; validation failure report |
| Intent আছে, receipt নেই | Submission unknown; resubmit/cancel-by-guessed-ID নয়; operator investigation |
| Accepted + timeout/cancel | Original failure retained; এক prompt-scoped cleanup attempt কেবল same identity ও durable attempt guard-এ |
| Cancel true/false | Dispatch/no-op observation মাত্র; job/compute stopped ঘোষণা নয় |
| Auth/network/cleanup failure | Primary error অপরিবর্তিত; cleanup unknown; automatic retry/fallback নয় |
| Owned worker killed/reaped | শুধু ওই local worker exited; remote job/compute unknown |
| Terminal job evidence | Same deployment+prompt-এর trusted terminal observation; GPU process বা billing stop proof নয় |
| Compute stop evidence | Selected resource-এর lifecycle provider/operator observation, resource/deployment identity ও time-সহ; storage আলাদাভাবে report |
| Valid image + cleanup unknown | Valid artifact রাখা যাবে; image validity এবং session cleanup status আলাদা; session fully closed নয় |
| Recovery | Existing accepted history/view GET-only; cleanup POST/lifecycle mutation recovery-তে যোগ নয় |

Cleanup observation generation receipt তৈরি/বদলাবে না। Auth failure বা lost receipt
রেকর্ড মুছে retry করার কারণ নয়। Whole server shutdown কেবল dedicated ownership ও
পৃথক action authorization থাকলে; shared server-এ অন্য কাজ ক্ষতিগ্রস্ত করা নয়।

## 5. Future acceptance matrix — এখন চালানো হয়নি

| পরীক্ষা | Pass evidence |
| --- | --- |
| Policy | Invalid units/types/bounds rejected; no dispatch; deterministic fake clock |
| Resource signals | Over-limit/stale/missing telemetry stops admission; unknown retained; client/server measurements পৃথক |
| Deadline | Hung mock child bounded termination/reap; no relaunch; remote stop দাবি নেই |
| Durable ordering | Cleanup intent fsync before action; crash before/after action no second automatic POST; concurrent callers serialized |
| Compatibility | Missing sidecar supported; v1/v2 journal bytes unchanged; corrupt/oversize/mismatched sidecar fail-closed |
| Failure/result | Original error retained; true/false ack does not become terminal; valid PNG survives unknown cleanup |
| Restart/recovery | Old budget not reset; accepted GET-only recovery; intent-only no resubmit; no cleanup in recovery |
| Provenance | Mock stop observation never real evidence; process exit/job terminal/compute/storage independently asserted |

## Outcome / next boundary

Design covers resources, durable observation, unknown receipt ও stop-proof gaps;
source/schema implementation হয়নি। Docs links/length/whitespace ও plan drift checks
এই step-এর verification; আগের 541 PASS evidence reused, app tests rerun নয়।

পরের প্রস্তাবিত একক micro-step: **offline supervision policy ও observation schema
validation/tests**, শুধু pure data contract; storage writer/process launcher/live
transport নয়। বর্তমান নির্দেশ design-only; পরবর্তী owner next-work নির্দেশ এই
সীমিত implementation-এর অনুমোদন হিসেবে গণ্য হবে। Model/runtime installation
owner করবেন; paid GPU/>2 GB download/new phase-এর আলাদা gates বহাল।
