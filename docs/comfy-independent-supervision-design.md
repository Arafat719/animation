# Phase 5.4 — D2 independent offline supervision boundary

2026-10-10। Owner next-work নির্দেশে একক design micro-step সম্পন্ন। Source/tests
implementation নয়; existing Phase 5.4 offline gap-এর decomposition, নতুন requirement নয়।

## Evidence ও reuse

[D1](comfy-shared-deadline-checkpoint.md) shared cooperative clock/run/cleanup ceilings
দেয়; blocked synchronous call-এর বাইরে independent owner নেই।
[Dummy supervisor](../animation_studio/providers/comfy_dummy_supervisor.py) fixed child
stop/kill/reap করে, offline session চালায় না। [I1 acceptance](comfy-supervised-recovery-checkpoint.md)
test-local Popen substitution দিয়ে durable crash/recovery দেখায়; production composition নয়।
[C3 cleanup](comfy-cpu-cleanup-checkpoint.md) original error ও unconfirmed child/sampler
handle retain করার precedent। Completed dummy/I1/C3 কাজ পুনরায় বানানো হবে না।

## নির্বাচিত boundary

প্রথম integration Linux same-host, fixed mock-only child entry point হবে। Parent
নিজে এক child spawn/own করবে; arbitrary command, callback, existing PID, shared
Comfy server বা remote worker গ্রহণ করবে না। Child descendants তৈরি করবে না।
Thread-only wrapper blocked child/GIL/native call থেকে parent isolation দেয় না।

| Owner | দায়িত্ব | যা তার evidence নয় |
| --- | --- | --- |
| Parent | Immutable original deadlines, bounded control/result IPC, owned child poll/signal/reap, retained cleanup ownership | Remote job cancel, target RAM/VRAM enforcement, GPU/compute/storage stop |
| Child | OfflineDurableComfySession, fixture admission/transport, same-lock generation journal, D1 ceilings, single durable cancel, fixture PNG validation | Live inference বা real target telemetry |
| Restart caller | Child exit confirmed হলে same root/context দিয়ে explicit GET-only recovery | Automatic relaunch/resubmit বা cleanup retry |

Parent HTTP/session/store lock-এ ঢুকবে না, request চালাবে না, child-owned generation
বা supervision journal লিখবে না। Transport/client/lock parent থেকে fork-inherit নয়;
child-তেই তৈরি ও close হবে। Parent-created separate process session ও retained Popen
handle ownership দেবে; direct-child signal যথেষ্ট, unrelated process/group kill নয়।

## Deadline এবং clock contract

1. Validated policy থেকে existing evaluator-এর arithmetic reuse:
   run = start + overall − cleanup − reap; cleanup = start + overall − reap;
   final = start + overall। Parent start spawn-এর আগে; startup/handshake run time খরচ করে।
2. Linux same-kernel monotonic clock parent/child share করবে; immutable start ও
   policy/control-session identity bounded startup input-এ যাবে। Child ready/progress
   message deadline বাড়াতে পারবে না। Persisted timestamps পরের process-run budget নয়।
3. Child সেই start/policy দিয়ে D1 admission বানাবে; fresh fixture observation/sample
   fixture হিসেবেই থাকবে। Parent deadline child-কে বিশ্বাস করে গণনা করবে না। D1-এর
   ছোট timeout_seconds child-কে আগে stop করাতে পারে, parent ceiling বাড়ায় না।
4. Run expiry বা caller cancel-এ parent bounded nonblocking stop notification পাঠাবে।
   Child control watcher local cancel Event সেট করবে; শুধু child durable path receipt
   থাকলে একবার prompt-scoped cancel পাঠাবে। Parent parallel cancel করবে না।
5. Cleanup deadline-এ child এখনও চললে owned-child SIGKILL; final reserve-এ bounded
   wait/reap। SIGTERM default process exit-কে cooperative durable cancellation বলা
   যাবে না। Unresponsive child-তে stop notification delivery-ও acknowledgement নয়।
6. Final deadline-এ unconfirmed exit হলে needs_manual_cleanup + retained handle;
   timeout reset/relaunch/unbounded wait নয়। Ready না আসলেও একই escalation চলে।

Parent monitor-এ blocking pipe read/write, communicate(), implicit Popen context
wait, blocking child-owned lock বা unbounded result decode থাকবে না। Spawn/OS
scheduling/kernel wait এবং parent death-এর absolute hard guarantee নেই; owned-child
isolation সাধারণ blocked I/O-তে bounded termination পরীক্ষা করার ব্যবস্থা।

## IPC ও failure ownership

- Fixed launch entry point ও enum fixture scenario; shell command/string execution
  বা caller-supplied executable নয়। Inputs explicit private root, matching mock
  context/validated graph, policy/start ও fresh control-session ID। Synthetic token
  child-local; token argv/environment/IPC/result/log-এ নয়।
- Startup/result protocol bounded JSON, maximum 64 KiB per message; strict fields,
  no pickle, no exception traceback/raw response। Input serialization limit spawn-এর
  আগে যাচাই। Nonblocking partial reads accumulate up to cap; EOF/oversize/malformed/
  duplicate terminal/wrong session বা wrong job identity failure। Poll cadence deadline
  অনুযায়ী clamp; status flooding deadline check আটকে রাখতে পারবে না।
- Child result bounded status/reason ও fixture verification claim; PNG bytes/base64
  IPC-তে নয়। Child existing PNG validator ব্যবহার করবে। Exit 0/ready byte একা image
  success নয়; valid terminal result + confirmed exit প্রয়োজন। API delivery 5.5 নয়।
- Parent normal return ও exceptional exit উভয়েই cleanup চেষ্টা করবে। Poll/signal/
  reap/pipe-close-এর এক failure অন্য independent cleanup বাদ দেবে না। C3-এর মতো
  primary exception অক্ষত রেখে retained cleanup session যোগ করতে হবে; bounded public
  error codes, private errors repr/log-এ নয়। Unknown child handle কখনো ফেলে দেওয়া নয়।
- Deadline পেরিয়ে ফল এলে তাকে timely success বলা যাবে না। Already-verified result ও
  cleanup failure আলাদা evidence; cleanup failure original result/error মুছবে না।

## Durable outcome ও recovery

| Kill/failure boundary | Durable interpretation | পরবর্তী কাজ |
| --- | --- | --- |
| Intent-এর আগে | No journal/submit evidence | Automatic retry নয়; caller নতুন explicit attempt বেছে নেবে |
| Intent persisted, receipt absent | Unknown, request হয়ে থাকতে পারে | Same-job execute reject; no guessed receipt/cancel |
| Accepted receipt persisted | Accepted context retained | Confirmed child exit-এর পরে explicit GET-only recovery |
| Cancel intent persisted, ack absent | Cleanup unknown/attempt consumed | No second cancel; journal/sidecar preserve |
| Cancel observed | Acknowledgement only | Recovery GET-only; job/worker/compute stop unknown |

Parent lock নিতে গিয়ে blocked child-এর deadline হারাবে না। Child exit নিশ্চিত না
হলে recovery deferred; confirmed exit-এর পর existing exclusive lock এখনও unavailable
হলে bounded failure। Corrupt/partial/incompatible journal existing reader reject করবে;
parent নিজে repair/relabel করবে না। New root/job ID global deduplication নয়।

## পরের একক implementation: D3 fixed offline session child supervision

Owner-এর পরবর্তী next-work নির্দেশে bounded parent launcher + fixed mock child entry
point এবং তার integration tests। One feature: existing OfflineDurableComfySession-কে
independent parent deadline-এর অধীনে চালানো। Existing dummy public API পরিবর্তন নয়;
এই কাজ live composition, telemetry collector, CPU sampler refactor বা UI যোগ করবে না।

Fixed scenarios: normal fixture completion, startup hang, inventory read hang,
accepted history read hang, cooperative caller cancellation। Test-only hooks পরে
specific journal-write/cleanup fault inject করতে পারবে; arbitrary child command API নয়।
Normal child real monotonic সময় ব্যবহার করবে; parent startup admission fresh fixtures
explicitly mock। Unknown RAM/VRAM-কে measured zero বলা যাবে না; D3 time/process
supervision evidence, resource admission samples synthetic এবং disclosed।

Pass checks:

1. Normal child session exact mock provenance/PNG validation + confirmed exit; one
   submit, owned pipes/child cleaned; no sockets/DNS in parent or child।
2. Startup/inventory/native-like blocking fixture সত্ত্বেও original deadlines-এ
   stop notification→kill→bounded reap; documented scheduling tolerance, no relaunch।
3. Cooperative accepted cancel সর্বোচ্চ এক POST; stuck accepted read parent kill হলে
   retained accepted journal, fresh GET-only recovery, no parent cancel।
4. Intent-only/cancel-intent failure injection-এ ambiguity/attempt guard অক্ষত;
   confirmed exit-এর আগে recovery নয়; existing I1 evidence reuse করে নতুন composition যাচাই।
5. IPC malformed/oversize/wrong identity/EOF, parent exception/KeyboardInterrupt,
   failed signal/reap/close-এ primary failure ও cleanup ownership retained।
6. Unrelated sentinel child untouched; all test-owned children finally reaped;
   shared clock/startup delay budget reset করে না। Tests bounded external timeout রাখবে।

## Outcome, checks ও সীমা

D2 design সম্পন্ন; D3 implementation এই turn-এ হয়নি। Relevant D1 598 PASS, C3 320
PASS ও I1 checkpoint evidence reused, overlapping counts যোগ করা হয়নি। Source/test
পরিবর্তন নেই; app tests, process/GPU/network probe বা install চালানো হয়নি।
Changed-doc links, RESUME length, excerpt drift ও whitespace PASS। Master feature
requirements unchanged; master/excerpts edit প্রয়োজন নেই। Existing dirty কাজ preserved।
Real native/GPU preflight আগের authorization-সহ hardware absence-এ blocked; একই probe
নয়। Real worker tree/VRAM telemetry/enforcement, target supervision, live dispatch ও
real PNG acceptance D3 fixture completion দিয়েও পূরণ হবে না।

## D3 update — 2026-10-10

Owner নির্দেশে [fixed session supervision](comfy-session-supervision-checkpoint.md)
সম্পন্ন; 29 new cases, combined 214 PASS। উপরের proposed implementation historical;
real target supervision/live composition ও hardware gate এখনও অসম্পূর্ণ।
