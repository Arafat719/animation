# Local durable shot-attempt reservation

2026-09-27। Phase 4 local budget follow-up micro-step সম্পন্ন; ledger-only।

- [Source](../animation_studio/providers/gpu_attempts.py): `LocalAttemptLedger`
  explicit `initialize()` ও `reserve()` API। Existing/missing/corrupt ledger
  automatic reset নয়। Version 1 strict local format; production DB/schema অপরিবর্তিত।
- Validated workload/config দিয়ে existing estimator আগে চলে; over-budget বা
  unknown shot-এ কোনো reservation হয় না। Render ID-এর সঙ্গে workload/budget digest
  স্থির থাকে। Config/workload representation বদলালেও conservative conflict হতে পারে।
- Global attempt-key digest একই render/shot-এ replay হলে একই ordinal ফেরে;
  অন্য render/shot বা বদলানো workload/config reject। New key planned shot attempt
  cap অতিক্রম করতে পারে না। Shot ও render আলাদাভাবে হিসাব হয়।
- Linux `flock` nonblocking lock; contention-এ `BlockingIOError`, blind success নয়।
  Private temp file → file fsync → atomic replace → directory fsync। File mode 0600;
  persistent lock কখনো delete নয়। Caller private existing local directory দেবেন।
- Commit-এর পর process exit/crash-এ reservation consumed থাকে। Write/fsync failure
  propagate হয়; replace হয়ে গেলে result ambiguous হতে পারে, একই key পুনর্ব্যবহার
  করতে হবে। Automatic refund নেই। Missing required state fields reject।
- Disk-এ raw prompt/request/token/asset নয়; render/shot/key/workload identity hashes
  এবং attempt limits/ordinals থাকে। Hash encryption নয়; private directory প্রয়োজন।

## Checks

- Baseline budget/provider: 79 PASS।
- [Ledger tests](../tests/test_gpu_attempts.py) + budget/provider: **100 PASS**, warnings নেই।
- Replay at cap, independent shots/renders, conflicting identities, invalid inputs,
  zero-budget rejection, missing/corrupt state, replace/file/directory fsync failure,
  spawned-process abrupt exit এবং concurrent final-slot contention verified।
- Ruff lint/format, plan excerpt drift, document links, RESUME length ও whitespace PASS।

## সীমা ও পরের কাজ

Local trusted Linux filesystem, cooperating processes ও একই ledger/IDs প্রয়োজন।
Deletion/rollback/manual edits/new ledger বা নতুন render ID দিয়ে accounting bypass
সম্ভব; tamper-proof/global quota নয়। Full JSON ledger rewrite হয়; ছোট local test scope।
Ledger schema v1 নতুন format; unknown versions reject, migration এখন প্রয়োজন নেই।

Reservation পাওয়া provider submit/retry permission নয়; replay থেকে dispatch করা
হয় না। Existing `submit_budgeted_shot` ও HTTP provider অপরিবর্তিত; production gate,
actual spend, runtime shutdown ও remote exactly-once execution এখনও অসম্পূর্ণ।

পরের একই Phase 4 local/mock micro-step: reservation-এর সঙ্গে mock-only dispatch
যুক্ত করা, যাতে replay/ambiguous failure-এ দ্বিতীয় submit না হয়। Real provider wiring,
GPU rental/payment এবং CPU model experiments স্থগিত। No install/download/cloud call।
