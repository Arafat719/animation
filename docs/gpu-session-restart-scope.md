# Mock session restart persistence scope

2026-09-27। Source/test review সম্পন্ন; implementation পরের micro-step।

## বর্তমান evidence

- [MockRenderSession](../animation_studio/providers/gpu_mock_session.py) প্রতি constructor-এ
  clock থেকে নতুন deadline তৈরি করে; closed শুধু memory-তে। Ledger reservation ও
  receipt durable হলেও নতুন session wrapper তৈরি করলে সময়ের allowance reset হয়।
- [MockSessionJournal](../animation_studio/providers/gpu_journal.py) Pod cleanup record:
  UTC deadline, cleanup intent, resource identity, bounded recovery attempts।
  [Journal tests](../tests/test_gpu_journal.py)-এ future deadline থাকলেও restart recovery
  cleanup করে; deadline renew হয় না। এটি shot admission record নয়।
- [Session tests](../tests/test_gpu_mock_session.py)-এ cooperative boundary/failure
  coverage আছে; durable session identity বা reopen admission বন্ধ করার coverage নেই।

## সিদ্ধান্ত: restart-এ admission বন্ধ, automatic resume নয়

পরের একটি local micro-step-এ durable mock session admission যোগ হবে। Existing
cleanup journal-এর recovery semantics অনুসরণ করবে; তার Pod record format বা
watchdog/supervisor পুনর্লিখবে না। Monotonic timestamp অন্য boot-এর clock-এর সঙ্গে
তুলনা করে অবশিষ্ট সময় অনুমান করবে না। Restart-এর পরে session নতুন submit নেবে না,
deadline record audit-এর জন্য অক্ষত থাকবে; receipt lookup চলবে।

নির্দিষ্ট scope:

1. Existing attempt ledger-এর সঙ্গে session identity bind: render/workload/config
   digest, mock resource ID, original start/deadline ও terminal closed marker। Raw
   prompt/token নয়। একই render/ledger-এ দ্বিতীয় fresh session allowance নয়।
2. Explicit fresh creation বনাম reopen/recovery পৃথক API। Fresh record durable
   হওয়ার আগে submit নয়। Existing record-এ constructor পুনরায় deadline লিখবে না।
   Record ছাড়া legacy ledger থেকে পুরোনো session allowance অনুমান নয়: নতুন durable
   session path legacy used render reject করবে; receipt lookup backward-compatible।
3. একই session-এর একটিমাত্র active owner; persistent lock file-এর lifetime lease
   দিয়ে দ্বিতীয় owner reject। Process exit lease ছাড়লেও durable record থাকবে।
   Ledger mutation lock ও owner lease-এর fixed acquisition order নথিভুক্ত করতে হবে।
4. Finish/fail/deadline/provider failure-এ durable closed intent cleanup-এর আগে।
   Write failure-এ current owner admission বন্ধ ও error propagate; পরের reopen
   পুরোনো active record-কেও closed ধরে। Cleanup failure কখনো reopen নয়।
5. Reopen resource/workload/config identity verify করে admission terminal করবে;
   clock rollback/future deadline-এও নতুন allowance নয়। Existing mock cleanup
   reuse; storage unknown/retained-কে cleanup-complete বলা নয়। Recovery cleanup
   bounded থাকবে; নতুন unbounded retry loop নয়।

## Pass checks

- Fresh submit/receipt; duplicate owner rejection; normal close→reopen blocked।
- Spawned owner process abrupt exit→reopen blocked, original deadline unchanged;
  before/after deadline ও বদলানো clock-এ একই conservative result।
- Identity conflict, missing/corrupt state, intent/fsync failure-এ zero new submit।
- Legacy ledger backward read; existing attempts/receipts অক্ষত; legacy used render
  auto-enrol নয়। Concurrent owner attempt ও cleanup failure-এ admission বন্ধ থাকে।
- Existing session/ledger/dispatch/lifecycle regression PASS; real-time sleep,
  GPU/network/package install ছাড়া deterministic fixtures ব্যবহার।

## সীমা ও authorization

এটি local mock crash-safe admission; unfinished work automatic resume বা live
billing protection নয়। Ledger deletion/new path/new IDs/standalone API bypass-এর
সীমা বহাল। Resource mock state process-local; old receipt current job status নয়।
নতুন persisted fields/version হলে explicit migration/backward-read test লাগবে;
production DB/UI/schema অপরিবর্তিত থাকবে।

একই Phase 4 local/mock authorization বহাল; পরের implementation-এ নতুন phase
approval প্রয়োজন নেই। Paid GPU/payment/model experiments স্থগিত। Requirements
অপরিবর্তিত; master edit নয়। Source/test consistency, document links, plan drift,
RESUME length ও whitespace PASS; docs-only বলে app tests নয়। Prior 157-test session
ও 126-test supervisor evidence retained।
