# Phase 5.4 — D4 supervised fixture child RAM integration design

2026-10-10। GPU অনুপস্থিতির blocker জানানোর পরে owner আবার next-work বলেছেন;
GPU-free next-scope বিকল্প অনুসারে এই docs-only design সম্পন্ন। নতুন phase নয়।
D3 time/process supervision complete; real image/GPU acceptance এখনও blocked।

## Source finding ও reuse

[D3 parent](../animation_studio/providers/comfy_session_supervisor.py) resource evaluator
থেকে deadlines নেয়, sample=None-এর missing-telemetry decision admission হিসেবে ব্যবহার
করে না। Child start হলে startup payload পাঠায়; parent-এ RAM sampler নেই। তাই D3-কে
measured RAM admission বলা যাবে না। Child-এর samples synthetic, সেটিই থাকবে।

Existing [OwnedChildRamReader](../animation_studio/providers/comfy_ram_telemetry.py)
Popen/PID/start-ticks binding দিয়ে Linux direct-child RSS ও host MemAvailable পড়ে।
[RamSampler](../animation_studio/providers/comfy_ram_sampler.py) serialized background
read, non-I/O-waiting snapshot ও absolute-deadline close দেয়।
[CPU guard](../animation_studio/providers/comfy_cpu_guard.py) identity/freshness/RAM/
reserve/time checks দেয়; VRAM unknown, scope local_cpu_dummy। এগুলো reuse করতে হবে;
নতুন reader/guard বা completed C1–C3 restart নয়। Existing scope label-কে target worker
বা live admission হিসেবে relabel নয়; supervised fixed fixture child-ই coverage।

## পরের একক implementation: D5 parent RAM admission/monitoring

- D3 parent owned child spawn করার পরে existing reader/sampler শুরু করবে। First
  valid reading-এর start_ticks pin করে expected PID/start-ticks-এ CPU guard চালাবে।
  Initial sample deadline min(original run_deadline, start + stale_after_seconds)।
  Missing first sample-এর জন্য শুধু এই bounded bootstrap window; explicit reader
  failure/invalid identity/over-budget হলে সঙ্গে সঙ্গে abort সিদ্ধান্ত।
- First allow-এর আগে startup JSON child-কে পাঠানো হবে না। Child existing stdin
  bootstrap read-এ অপেক্ষা করবে; নতুন ready/GO protocol দরকার নেই। ফলে প্রথম RAM
  rejection-এ inventory/intent/submit নেই। Interpreter/import startup sampling-এর
  আগে allocation করতে পারে; এটি process launch বা allocation hard cap নয়।
- Bootstrap rejection/cancel-এ unsent payload discard করে stdin বন্ধ করতে হবে;
  startup parser-এ bare stop byte দিয়ে আটকে রাখা নয়। Partial payload পাঠানোর পরে
  abort হলে আর payload/GO complete নয়—stdin close, original cleanup ladder বহাল।
  Full payload sent হলে existing one-stop notification ও child-only cancel path।
- Admission-এর পরে প্রতিটি parent monitor cycle latest sampler snapshot CPU guard-এ
  যাবে। Missing/stale/invalid/mismatched/over-budget বা sampler failure-এ abort;
  failure হলে পুরোনো allow reading ধরে চালানো নয়। Sampler sequence/freshness থাকবে,
  parent loop-এ synchronous procfs read বা sampler restart নয়।
- Parent-confirmed exit telemetry failure-এর আগে handle করবে। Exited reading একা
  reap proof নয়। Resource rejection original run/cleanup/final deadlines বাড়াবে না;
  early abort-ও existing cleanup ceiling মানবে। Parent HTTP cancel করবে না।
- Cleanup-এ sampler stop, owned child kill/reap, sampler close ও pipe close independent
  attempts; সব bounded by original final deadline। Blocked sampler থাকলে child reaped
  হলেও needs_manual_cleanup; normal result ও exception উভয়েই sampler + child handle
  retain করতে হবে। C3 exceptional ownership semantics reuse, raw errors repr-এ নয়।

## Provenance ও compatibility

Parent result-এ local procfs/direct-child RAM evidence, measured RSS/available RAM,
sampler state/sequence ও bounded guard reasons আলাদা থাকবে। Child inference/mock
admission samples এখনও synthetic; একটি overall source label দিয়ে real RAM ও fake
VRAM মেশানো যাবে না। VRAM unknown; OS memory hard cap বা target process tree claim নয়।

Policy owner/caller explicit দেবেন; production default RAM budget অনুমান নয়। Existing
D3 test-এর 1024-byte synthetic threshold বাস্তব interpreter-এর জন্য নয়—নতুন tests-এ
স্পষ্ট small-process-appropriate policy বা injected readings ব্যবহার করতে হবে। কোনো
বড় allocation, OOM experiment বা model load নয়। D3 scenario API, journal schema,
child mock provenance ও caller-directed GET-only recovery অপরিবর্তিত থাকবে। Result/
cleanup dataclass extension হলে existing caller regression checks লাগবে।

## Pass checks

1. Fresh matching local reading-এর আগে startup payload/intent/POST নেই; first allow-এর
   পরে normal fixture PNG, child exit ও sampler stopped evidence।
2. Bootstrap missing/invalid/wrong PID/start ticks/RAM limit/host reserve rejection-এ
   no generation journal; threshold equality existing guard semantics reuse।
3. Accepted run-এর সময়ে stale/failed reader ও budget breach-এ single stop/cancel or
   bounded kill; same journal retained, explicit confirmed-exit GET-only recovery।
4. Blocked reader parent deadline আটকায় না; child reaped কিন্তু sampler unknown হলে
   retained cleanup handle। Parent exception/failed kill/failed close-এ primary error
   ও independent cleanup preserved; tests finally blocked reader release/join করবে।
5. Initial/partial startup write cancellation fail-closed; startup/sample delay original
   run budget consume করে। Unrelated sentinel child unaffected; no socket/DNS/GPU।
6. Existing D3 time/IPC/cancel/unknown-exit ও D1/A3 regressions pass; local measured RAM
   evidence কখনো real generation/target VRAM success হয় না।

## Checks, outcome ও authorization

D4 design complete; D5 implementation পরবর্তী owner next-work নির্দেশে এই সীমায় করা
যাবে। এই turn source/test/schema/feature requirements বদলায়নি; master edit নয়।
D3 214 PASS এবং existing C3 checkpoint evidence reused; app tests rerun বা hardware
probe প্রয়োজন হয়নি। Docs links, RESUME length, plan drift ও whitespace PASS।
Real GPU/native preflight আগের authorization-সহ blocked; environment পরিবর্তন ছাড়া
একই probe নয়। Paid resource/new phase/5.5/live dispatch অনুমোদিত নয়।
