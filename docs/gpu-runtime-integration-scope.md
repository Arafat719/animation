# Budget runtime limit ও mock dispatch integration scope

2026-09-27। Scope review সম্পন্ন; এই ধাপে source implementation নয়।

## যাচাই করা gap

- [Phase 4](plan/phase-4.md)-এ maximum GPU minutes per job requirement আছে।
  [Budget estimator](../animation_studio/providers/gpu_budget.py) planned minutes
  limit যাচাই করে; elapsed session time enforce করে না।
- [MockSessionController](../animation_studio/providers/gpu_lifecycle.py) caller-এর
  monotonic tick-এ deadline/finished/failed হলে admission closed করে cleanup দেয়।
  [Tests](../tests/test_gpu_lifecycle.py)-এ exact deadline, early exit, cleanup failure,
  retained/unknown storage ও invalid clock coverage আছে। এটি পুনর্লিখতে হবে না।
- [Guarded dispatch](../animation_studio/providers/gpu_mock_dispatch.py)-এ budget,
  durable reservation ও receipt আছে; controller/deadline input নেই। ফলে session
  closed হওয়ার পরেও standalone dispatch function ব্যবহার করা সম্ভব।
- [Supervisor checkpoint](gpu-supervisor-checkpoint.md)-এর bounded child recovery
  cleanup runner-এর জন্য; shot admission wiring নয়। নতুন watchdog/server কাজ নয়।

## পরের একটি micro-step: cooperative mock render session

নতুন ছোট wrapper-এ exact local MockGPUProvider, MockLifecycle ও LocalAttemptLedger
নেবে; validated workload/config/render ID session তৈরির সময় স্থির থাকবে। Existing
estimator, guarded dispatch এবং MockSessionController reuse করবে। Mock REST/live
transport, production API/DB বা background service এই step-এর scope নয়।

1. Over-budget/invalid input session arm করার আগেই reject। Injected monotonic clock
   দিয়ে একবার start capture; duration = config.max_gpu_minutes_per_job × 60 seconds।
   Zero/nonfinite/unrepresentable time window reject; tiny float conversion যেন
   allowance বাড়িয়ে না দেয়। Planned minutes estimate ও elapsed cap আলাদা থাকবে।
2. প্রতি submit-এর আগে clock/controller tick। Deadline-এ বা closed session-এ
   কোনো নতুন reservation, receipt write বা provider submit নয়; cleanup result
   caller দেখতে পারবে। Existing receipt lookup session বন্ধ হলেও read-only থাকবে।
3. Deadline-এর আগে guarded dispatch reuse; attempt identity/replay/cap semantics
   অপরিবর্তিত। Submit শেষে আবার clock tick করে deadline overrun observe করবে।
   এটি blocking operation interrupt করার guarantee নয়।
4. Submit/provider/persistence failure-এ session closed ও existing cleanup;
   original failure propagate করবে, cleanup result আলাদাভাবে inspect করা যাবে।
   Replay/cap/preflight rejection-কে provider failure ধরে blanket cleanup নয়।
5. Explicit finish/fail/tick methods existing controller-এ delegate করবে। Receipt
   মানে queued acceptance; সেটিকে queue empty/completed ধরে automatic finish নয়।

## Acceptance checks

- Deterministic fake clock: cap-এর আগে admission, exact boundary-তে zero new calls/
  reservation এবং cleanup; later calls বন্ধ, fixed deadline কখনো renew নয়।
- Early finish/failure, observed overrun, cleanup failure-তেও session reopen নয়।
- Retained/unknown storage cleanup-complete বলে দেখানো নয়; resource identity অক্ষত।
- Ledger replay/cap/receipt regression PASS; timeout-এর পরে unknown receipt থেকে
  resubmit নয়। Invalid/non-monotonic clock ও nonmock input reject।
- GPU, network, model, package install বা real-time sleep ছাড়াই tests সম্ভব।

## সীমা ও authorization

এটি same-process cooperative mock integration; process restart-এ session deadline
পুনরুদ্ধার, separate watchdog admission wiring, persistent spend ও real billing cap
এখনও deferred। Existing standalone API bypass করা যায়; production guard দাবি নয়।
Mock resource cleanup provider-এর in-memory jobs বাস্তবে চালায়/বন্ধ করে না।

বর্তমান Phase 4 local/mock authorization-এ পরের implementation করা যাবে; নতুন
phase নয়। Paid GPU/payment ও CPU model experiment স্থগিতই থাকবে। Requirements
বদলায়নি; existing requirement-এর bounded implementation scope, master edit নয়।

Checks: source/test/checkpoint consistency, relative links, plan excerpt drift,
RESUME length ও whitespace PASS। Documentation-only, app tests পুনরায় নয়;
আগের dispatch acceptance 120-test ও supervisor 126-test evidence retained।
