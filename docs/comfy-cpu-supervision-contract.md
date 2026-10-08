# Phase 5.4 — real CPU telemetry/dummy supervisor integration contract

2026-10-05। Owner next-work নির্দেশে design-only micro-step। Existing
[RAM reader](comfy-ram-telemetry-checkpoint.md), [dummy supervisor](comfy-dummy-supervisor-checkpoint.md)
ও [resource design](comfy-resource-guard-design.md)-এর সীমিত composition; master
requirements বা real/live authorization পরিবর্তন নয়। নিচের integration implemented নয়।

## 1. CPU-only boundary

বর্তমান full ComfyResourceSample-এ VRAM ও selected GPU বাধ্যতামূলক। LocalRamReading
partial; সেটিকে fake zero VRAM দিয়ে full evaluator-এ পাঠানো যাবে না। নতুন explicit
CPU-only decision path শুধু fixed local dummy child-এর জন্য হবে। Existing synthetic
supervisor behaviour এবং full mock resource evaluator অপরিবর্তিত থাকবে।

Existing ComfySupervisionPolicy-এর RAM/reserve/time fields reuse; CPU decision-এ
GPU fields প্রয়োগ হবে না এবং result-এ `scope=local_cpu_dummy`, `vram_status=unknown`
স্পষ্ট থাকবে। CPU allow পূর্ণ image-job admission নয়। Mock execution context-ই
গ্রহণযোগ্য; network/model/server submission এই API-এর কাজ নয়।

## 2. Pure CPU guard contract — পরের একক implementation

Input: existing validated policy/context, expected owned PID/start_ticks, LocalRamReading
বা None, run start/current monotonic time। Start ticks reader-এর প্রথম identity-checked
sample থেকে owner pin করবে; external arbitrary PID API নয়। Guard নিজে কোনো I/O,
clock read, process action বা ownership discovery করবে না।

LocalRamReading dataclass frozen হলেও runtime types enforce করে না; guard অবশ্যই
exact type/field/provenance যাচাই করবে। PID/start_ticks exact positive/nonnegative
integer যথাক্রমে; bool/string rejected। RSS/available RAM exact nonnegative integer;
source local_procfs, coverage direct_child, vram_bytes None। Sample time finite,
nonnegative এবং start <= sampled_at <= now। Unknown status/forged values invalid।
Caller policy/context/time/expected identity malformed হলে ValueError; invalid sample
bounded reason দিয়ে abort। Reader failure value দিয়ে exception text প্রকাশ নয়।

| Condition | Running decision |
| --- | --- |
| Valid fresh reading, all bounds pass | allow, CPU scope only |
| None | abort / telemetry_missing |
| unavailable/invalid/identity_mismatch | abort / corresponding bounded telemetry reason |
| exited reading | abort / worker_exit_unconfirmed; parent poll exit confirm করবে |
| Wrong PID/start_ticks/provenance/types | abort / telemetry_invalid |
| now - sampled_at > stale_after | abort / telemetry_stale; equality fresh |
| RSS >= RAM limit | abort / ram_limit |
| MemAvailable <= host reserve | abort / host_reserve |
| now >= run deadline | abort / run_deadline |

Status failure হলে byte fields None হতে হবে; malformed failure record-ও invalid।
Valid sample-এর simultaneous stale/RAM/reserve/deadline breach সব fixed order-এ
ফিরবে; deadline reason failure telemetry-এর সঙ্গেও থাকবে। Remaining time clamp zero।
Existing run/cleanup/final arithmetic, finite overflow/precision-collapse rejection
ও no deadline reset semantics বহাল থাকবে; API breaking refactor নয়।

## 3. Startup ও admission (পরবর্তী wiring scope)

Owned child নেই এমন সময়ে RSS sample বানানো যাবে না। Fixed small dummy spawn হবে
explicit test bootstrap; সেটি successful RAM admission নয়। Bootstrap phase-এ dummy
শুধু অপেক্ষা করবে, model/large allocation/descendant নেই। প্রথম sample-এর অপেক্ষা
একই run window consume করবে। First-sample deadline = min(run_deadline,
start + stale_after_seconds); expiry বা read failure-এ abort।

First identity-checked sample দিয়ে reader start_ticks pin; তারপর CPU guard চালাবে।
প্রথম valid CPU decision-এর আগে result-এ admitted/success দাবি নয়। Child আগে exit
করলে parent returncode report করবে এবং telemetry admission unverified থাকবে।
Host reserve before-spawn guarantee এই bootstrap দেয় না; production admission বা
real model worker-এ এই exception প্রযোজ্য নয়।

## 4. Sampling parent deadline আটকাবে না

OwnedChildRamReader.read() synchronous procfs read; byte cap latency cap নয়। সরাসরি
supervisor polling loop-এ বসিয়ে hard timeout claim করা যাবে না। Future sampler:
এক session-এ একটি serialized sampler thread, at most one read in flight; bounded
single-slot latest reading, read-start timestamp freshness-এর উৎস। Slow read-এর
শেষে timestamp নতুন করে sample-কে fresh দেখানো নয়। Parent reader completion-এর
জন্য blocking wait করবে না; stale/missing হলে independently abort/stop/kill/reap।

Reader object ও Popen handle একই parent process-এ থাকবে; অন্য process-এ পাঠালে
reader-এর parent identity contract ভাঙে। Sampler শুধু read করবে, signal/restart নয়।
Parent stop event দিলে নতুন read শুরু হবে না; outstanding read শেষ হলে stop check
করে late publication বন্ধ। Thread join final deadline-এর remaining time পর্যন্ত।

Blocked OS read thread নিরাপদে force-kill করা যায় না: worker reaped হলেও sampler
না থামলে sampler_status=unknown এবং needs_manual_cleanup; fully closed নয়। One-shot
session পুনর্ব্যবহার নয়, নতুন sampler/retry তৈরি নয়। Future implementation এই leak
boundary ও caller shutdown obligation স্পষ্ট করবে; production unattended readiness
এই design দিয়ে PASS হবে না। Thread/GIL/kernel starvation-এর absolute guarantee নেই।

## 5. Parent action ও provenance

একবার abort হলে first primary reasons retain; late healthy sample outcome পাল্টাবে
না। Parent child.poll দিয়ে exit confirm করবে; শুধু owned direct child-এ cooperative
stop, cleanup boundary-তে kill, final পর্যন্ত reap। Reader exited claim parent-এর
exit observation-এর বিকল্প নয়। Job/compute/storage unknown, VRAM unknown।
Direct RSS tree aggregate/cgroup limit নয়; MemAvailable host estimate। Existing
v2 cancellation-এর parallel POST নয়। Durable journal/real executor integration
এই CPU-only কাজের বাইরে; completed I1 acceptance পুনরায় implementation নয়।

## 6. Acceptance এবং micro-step order

1. **C1 pure guard/tests:** good sample, equal/over boundaries, stale/missing/failure,
   forged dataclass/provenance/identity, invalid bool/NaN/inf, shared deadlines,
   multiple reasons, no I/O/GPU imports। এইটিই পরের owner-directed implementation।
2. **C2 sampler lifecycle/tests:** one in-flight read, bounded latest slot, delayed
   read/staleness, stop/late publication, bounded join ও unknown sampler status।
   Fixtures-এর blocked read test শেষে release করে thread join; orphan test thread নয়।
3. **C3 fixed dummy integration:** real small child RAM observation, low configured
   threshold দিয়ে abort (বড় memory allocation নয়), sample disappearance/hang,
   normal-exit race, independent parent deadline/reap এবং explicit CPU-only result।

C2/C3 পৃথক পরবর্তী scopes; এই design turn-এ source/test implementation নেই।

## Outcome/checks

Source contracts, startup ownership, partial telemetry ও deadline constraints
cross-check সম্পন্ন। Docs links/RESUME length/plan drift/whitespace PASS; existing
124 PASS evidence reused, নতুন app tests প্রয়োজন নেই। Offline design blocker নেই।
Next owner instruction-এ C1 pure guard/tests; live/full GPU admission/new phase নয়।
