# Durable admission থেকে mock dispatch

2026-09-27। অনুমোদিত local/mock micro-step সম্পন্ন।

- [Dispatch](../animation_studio/providers/gpu_mock_dispatch.py)-এর
  `submit_mock_budgeted_shot` শুধু exact `MockGPUProvider` ও `LocalAttemptLedger`
  গ্রহণ করে; অন্য provider/subclass reservation-এর আগেই reject। Live transport নেই।
- [Ledger](../animation_studio/providers/gpu_attempts.py)-এ internal `_reserve_once`
  একই lock-এর মধ্যে fresh/replayed result নির্ধারণ করে। Fresh durable write সফল
  হলে মাত্র বর্তমান caller একবার submit করে। Public `reserve()` return অপরিবর্তিত।
- Replay-এ `AttemptAlreadyReserved` reservation identity ফেরায়; provider call করে
  না, fake success/job result দেয় না। আগের ledger-only reservation-ও একইভাবে blocked।
- Timeout/provider error propagate হয়; reservation consumed থাকে। Reserve-এর পর
  submit-এর আগে crash হলেও automatic retry নয়। Directory fsync failure-এ durable
  outcome অনিশ্চিত থাকতে পারে, কিন্তু সেই call provider submit করে না।
- Ledger v1 schema অপরিবর্তিত; পুরোনো record backward-read tested। Raw request/job
  result persist নয়; application DB/schema, HTTP/production provider অপরিবর্তিত।

## Checks ও সীমা

[Dispatch tests](../tests/test_gpu_mock_dispatch.py), ledger, budget ও provider:
**110 PASS**। Success/replay/cap, existing v1, preflight/conflict, exact mock guard,
accept-before-timeout, failure-before-accept, file/directory sync failure, spawned
process crash ও concurrent same-key submit verified। আগের 100-test baseline retained।
Ruff lint/format, docs links, plan drift, RESUME length ও whitespace PASS।

একই ledger ও stable IDs-এর cooperating local callers-এর জন্য at-most-once submit
attempt; exactly-once completion নয়। Success-এর job receipt disk-এ নেই, ফলে replay
বা restart-এ outcome unknown থাকে। Mock provider jobs memory-only। নতুন key নতুন
attempt হিসেবে allowance নেয়; এটি unknown outcome retry করার নির্দেশ নয়। Existing
unguarded submit API bypass করতে পারে; production gate/runtime/spend এখনও বাকি।

পরের অনুমোদিত একই Phase 4 local/mock micro-step: successful mock submission-এর
minimal durable receipt ও read-only outcome lookup; replay থেকে submit নয়,
missing receipt-কে unknown রাখা। Paid GPU/model experiments স্থগিত। এই step-এ
install/download/cloud call/commit হয়নি।
