# Mock submission receipt ও read-only lookup

2026-09-27। Phase 4 local/mock micro-step সম্পন্ন।

- [Ledger](../animation_studio/providers/gpu_attempts.py)-এর reservation-এ optional
  `MockSubmissionReceipt`: provider `mock-gpu`, bounded mock job ID ও `submitted`।
  Raw prompt/request/token সংরক্ষণ হয় না। এটি historical acceptance, completion নয়।
- [Dispatch](../animation_studio/providers/gpu_mock_dispatch.py) সফল submit-এর পরে
  একই locked atomic/fsync writer দিয়ে receipt সংরক্ষণ করে, তারপর job ফেরায়।
  Receipt persistence failure caller-এর কাছে propagate হয়; attempt consumed থাকে।
- `lookup(render_id, shot_id, attempt_key)` atomic file snapshot পড়ে: reservation
  না থাকলে None; reservation আছে কিন্তু receipt নেই মানে outcome unknown। Identity
  mismatch reject; missing/corrupt ledger error, কখনো empty/unknown success নয়।
- Lookup কোনো file write, lock-file creation, provider status বা submit করে না।
  Replay আগের মতো `AttemptAlreadyReserved`; exception reservation-এ receipt থাকলে
  সেটিও পাওয়া যায়। Receipt lookup-এর ভিত্তিতে automatic retry নেই।
- v1 format-এ optional additive receipt field; পুরোনো absent field → None। Missing
  receipt rewrite-এ omitted থাকে; পুরোনো ledger-এর count/identity অক্ষত। Destructive
  migration নেই; backward-read tested। পুরোনো binary নতুন receipt পড়তে পারবে না।

## Checks ও সীমা

[Receipt tests](../tests/test_gpu_mock_receipt.py) + dispatch/ledger/budget/provider:
**119 PASS**। Prior 110-test evidence retained। Process-exit persistence, read-only
lookup, legacy unknown, identity conflict, accept-then-timeout, receipt file/directory
fsync failure, corrupt receipt ও missing file verified। Ruff lint/format এবং docs
links/plan drift/whitespace/RESUME length PASS।

Mock jobs memory-only; job IDs নতুন provider instance-এ পুনর্ব্যবহার হতে পারে।
Receipt দিয়ে নতুন provider instance-এর status মিলানো যাবে না। Submit ও receipt
write-এর মাঝখানে crash/lock contention/write failure হলে outcome unknown থাকতে
পারে; directory sync failure-এর পরে receipt দৃশ্যমানও হতে পারে। Read-only lookup
পরবর্তী write-এর আগের snapshot দেখাতে পারে। Exactly-once completion দাবি নয়।

পরের অনুমোদিত local/mock micro-step: budget → reservation → dispatch → receipt
lookup-এর bounded offline acceptance scenario, success/unknown/replay report সহ।
Production wiring/runtime/spend ও real GPU acceptance বাকি। No install/download/
cloud call/payment/commit; paid GPU ও CPU model experiments স্থগিত।
