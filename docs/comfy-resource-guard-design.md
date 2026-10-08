# Phase 5.4 — offline resource admission ও deadline design

2026-10-05। Owner GPU-independent next-work নির্দেশে এক design-only micro-step।
এটি [supervision contract](comfy-supervision-contract.md)-এর অসম্পূর্ণ resource/time
অংশের বিস্তারিত; নতুন feature requirement বা master-plan scope পরিবর্তন নয়।
কোনো enforcement, process launch বা live integration এই step-এ implemented নয়।

## বিদ্যমান অংশ পুনর্ব্যবহার

- [Policy/schema](../animation_studio/providers/comfy_supervision.py): explicit
  RAM/reserve/VRAM/device/sample/staleness/overall/cleanup/reap fields ও strict
  validation আছে। নতুন duplicate policy/schema নয়।
- [V2 executor](../animation_studio/providers/comfy_v2_executor.py): same-job lock,
  intent/receipt, durable one-attempt cancel আছে; accepted recovery GET-only।
- [Crash acceptance](comfy-cancel-crash-checkpoint.md) completed; আবার implementation নয়।
- [HTTP executor](../animation_studio/providers/comfy_http.py): preflight ও execute
  আলাদা deadline তৈরি করে; cancel-এর আলাদা 5-second budget। Outer shared budget,
  telemetry admission বা process-tree enforcement এখানে নেই।

## পরের pure evaluator-এর contract

Input হবে validated existing policy, expected execution context, explicitly selected
worker identity, lifecycle stage (`admission`/`running`), run start, current monotonic
সময় এবং optional resource sample। কোনো clock read, filesystem, network বা process
I/O evaluator-এর মধ্যে নয়। Mock context ছাড়া এই প্রথম implementation reject করবে।

Sample-এ context/worker identity, device index, sampled monotonic time, target worker
process-tree RSS bytes, target host available RAM bytes ও selected-device used VRAM
bytes থাকবে। Bytes exact nonnegative integer; bool/string/negative reject। Sample
missing হলে unknown; zero কেবল valid measurement হলে গ্রহণযোগ্য। Client RSS বা
অন্য device/worker-এর data target telemetry হিসেবে গ্রহণ নয়। Fake sample দিয়ে
policy test GPU ছাড়াই সম্ভব; mock reading বাস্তব hardware evidence নয়।

Run start/current/sample time finite nonnegative number; bool/NaN/inf reject।
`now < start`, future sample বা `sampled_at < start` হলে invalid। একই process-local
clock domain adapter-এর দায়িত্ব; restart-এর persisted clock দিয়ে evaluator resume নয়।
Strict types/extra-field rejection; sample mismatch/invalid data কখনো allow নয়।

Decision pure data: `allow`, `deny` (admission) অথবা `abort` (running), bounded
reason codes-সহ। একাধিক breach থাকলে deterministic fixed-order reasons ফিরবে;
`allow` কেবল empty reasons-এ। Decision নিজে cancel/kill/POST বা stop-proof নয়।
Invalid policy/context/call arguments validation error; missing/invalid sample
telemetry reason। এই distinction tests-এ স্পষ্ট থাকবে।

| Condition | Decision reason; boundary |
| --- | --- |
| No sample / invalid identity, type or timestamp | telemetry_missing / telemetry_invalid |
| `now - sampled_at > stale_after_seconds` | telemetry_stale; exact equality fresh |
| RSS `>= ram_limit_bytes` | ram_limit; equality-তেও নতুন কাজ নয় |
| Available RAM `<= host_reserve_bytes` | host_reserve; equality-তে reserve ব্যবহার নয় |
| Device used VRAM `>= vram_limit_bytes` | vram_limit; mock-only device-level pressure signal |
| `now >= run_deadline` | run_deadline; equality expired |

Remaining run time = max(0, run_deadline - now)। Arithmetic ফল finite হতে হবে;
finite inputs যোগে overflow হলেও validation error। Admission allow শুধু বর্তমান
sample-এ configured guard পাস; model fit বা পরের allocation সফল হওয়ার proof নয়।
Sampled RSS/VRAM guard transient spike ঠেকানোর hard memory cap নয়। CPU dummy process
test-এর জন্য fake VRAM sample স্পষ্টভাবে mock; live GPU requirement এতে বাদ যায় না।

## Shared deadline ও ভবিষ্যৎ enforcement boundary

Existing policy অনুযায়ী overall timeout-এর মধ্যেই cleanup ও reap reserve:
`run_deadline = start + overall - cleanup - reap`;
`cleanup_deadline = start + overall - reap`;
`final_deadline = start + overall`। Startup/preflight/submit/poll/download একই run
window consume করবে; poll/progress deadline reset নয়। Parent independent monitor
থাকবে, যাতে blocked child I/O parent-এর deadline check আটকায় না।

Pure evaluator-এর পরে আলাদা micro-step-এ bounded dummy-child supervisor হবে।
শুধু নিজের spawned child/process group; arbitrary PID, shared Comfy server বা remote
compute stop নয়। Run expiry-তে cooperative stop request, cleanup deadline-এ owned
process termination/escalation, final allowance-এ bounded reap/report। Signalling
ও exit observation আলাদা evidence; reap ব্যর্থ হলে unknown/manual attention,
কোনো relaunch নয়। Uninterruptible kernel wait/parent death-এর hard guarantee নয়।

পরে executor integration-এ existing durable cancel guard একমাত্র cancel owner থাকবে;
parent parallel cancel পাঠাবে না। Receipt না থাকলে guessed cancel নয়। Child kill
হলে journal/sidecar রেখে accepted GET-only recovery; intent-only outcome unknown।
Original failure ও verified artifact preserve; worker exit remote job/compute stop নয়।

Real RAM enforcement-এর আগে target process-tree OS/container capability যাচাই চাই;
RSS sampling, RLIMIT_AS বা client-only process stop-কে remote RAM cap বলা যাবে না।
VRAM hard cap unsupported হলে capability limitation স্পষ্ট থাকবে। এই design কোনো
machine-specific budget নির্বাচন বা existing CUDA address-space policy বদলায় না।

## Acceptance matrix — proposed, tests এখনও চালানো হয়নি

| ID | Case | Expected evidence |
| --- | --- | --- |
| R1 | Valid fresh sample, below limits | allow; input unchanged; deterministic remaining time |
| R2 | Each limit just below/equal/above | documented inclusive/exclusive boundary; deny/abort by stage |
| R3 | Missing, stale, future, pre-start sample | fail-closed; exact stale equality covered |
| R4 | Wrong context/worker/device; malformed bytes/time | no allow; bounded reason or argument validation error |
| R5 | Run/cleanup/final boundaries, overflow, reversed clock | no reset; finite coherent deadlines; run equality expired |
| R6 | Several simultaneous breaches | stable ordered reasons, no hidden breach |
| R7 | Purity | forbid socket/process/file calls; no wall-clock sleep or GPU import |
| P1 | Dummy child hangs / ignores cooperative stop | later supervisor terminates/reaps within documented test tolerance |
| P2 | Child exits normally or during stop race | correct local exit evidence; no relaunch/unrelated signal |
| P3 | Sample disappears while running | abort; remote/job/compute remain unknown |
| I1 | Accepted/intent-only journal after child exit | later integration: GET-only/no resubmit; cancel at most once |

R1–R7 পরের একক implementation scope। P1–P3 ও I1 আলাদা পরবর্তী micro-step;
completed cancellation crash tests তাদের বিকল্প নয়। Dummy tests ছোট allocation ও
short timeout ব্যবহার করবে; প্রকৃত OOM বা host memory exhaustion ঘটাবে না।

## Outcome, checks ও next

Existing source/contracts-এর সঙ্গে ownership, deadline ও recovery semantics মিলিয়ে
review সম্পন্ন। Docs links, RESUME length, plan drift ও whitespace যাচাই; source বা
requirements বদলায়নি, app tests প্রয়োজন নেই। GPU-independent design-এর blocker নেই।
Next: pure resource sample/admission/deadline evaluator + R1–R7 tests। বর্তমান
অনুমোদন design-only; পরবর্তী owner next-work নির্দেশে এই সীমিত implementation
করা যাবে। GPU/native generation deferred; নতুন phase/live/paid authorization নয়।
