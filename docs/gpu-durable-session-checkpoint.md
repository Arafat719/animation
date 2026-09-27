# Durable mock session admission

2026-09-27। অনুমোদিত restart persistence micro-step সম্পন্ন।

- [Durable wrapper](../animation_studio/providers/gpu_durable_session.py)-এ explicit
  create/recover এবং context manager/release। Exact local mock components ছাড়া নয়।
- Attempt ledger-এ optional `sessions` map: workload/config digest, resource ID,
  original start/deadline, closed এবং bounded cleanup count। Fresh render identity
  ও session একই atomic write-এ bind হয়; existing/legacy used render পুনরায় create নয়।
- Ledger-wide owner flock lifetime lease: এক render-এর চেয়েও কঠোর, পুরো ledger-এ
  একজন owner। Lock order owner lease → ledger mutation lock; lock files delete নয়।
- Recovery identity মেলায়, নতুন clock উপেক্ষা করে, admission closed রাখে। Original
  deadline audit value হিসেবে অক্ষত; নতুন boot-এর monotonic clock দিয়ে resume নয়।
- Finish/fail/deadline/dispatch failure-এ closed intent ও cleanup count persist করার
  পরে existing mock cleanup। Persistence failure-তেও memory admission বন্ধ।
  Maximum তিন durable cleanup attempts; cap-এ unknown/manual follow-up result,
  নতুন mutation বা success দাবি নয়। Same owner closed tick পুনরায় cleanup করে না।
- `release()` owner lease ছাড়ে ও local admission বন্ধ করে; এটি cleanup success নয়।
  Active record থাকলেও পরের recover terminal হয়। Normal use context manager/finish।
- Existing `MockRenderSession`-এ cleanup hook ছাড়া আচরণ অপরিবর্তিত। Standalone API
  এই guard bypass করতে পারে; production enforcement নয়।

## Format ও checks

[Ledger](../animation_studio/providers/gpu_attempts.py)-এর v1 format-এ additive optional
sessions field; absent legacy field → None, unused field serialized নয়। পুরোনো
attempt/receipt data অপরিবর্তিত; destructive migration নেই। Legacy used render
lookup চলে কিন্তু durable session auto-enrol নয়। পুরোনো binary নতুন session field
পড়তে পারবে না; production DB/schema পরিবর্তন হয়নি।

[Tests](../tests/test_gpu_durable_session.py) + session/lifecycle/offline/receipt/
dispatch/ledger/budget/provider: **170 PASS**। Fresh/duplicate owner, receipt,
normal close/recover, spawned abrupt exit, before/after/invalid new clock, identity
conflict, legacy ledger, missing/corrupt file, file/directory fsync failure, closed
intent failure, deadline/provider failure ও bounded recovery verified।
Ruff lint/format, plan drift, relative links, RESUME length ও whitespace PASS।

## সীমা ও পরের কাজ

Cooperating single-caller Linux/local-file mock scope; no background timer, live
GPU shutdown, automatic inference resume বা spend accounting। Provider/resource
state process-local। Ledger rollback/deletion/new IDs ও unguarded APIs bypass করতে
পারে। Owner descriptor fork করে অন্য process-এ রাখা সমর্থিত নয়; tests spawn ব্যবহার করে।
Cleanup result persist নয়; cap-এ conservative unknown, storage deletion নেই।

পরের অনুমোদিত local micro-step: durable session create→submit→process exit→recover→
blocked submit ও receipt lookup-এর integrated offline acceptance/report। Existing
watchdog পুনর্লিখন নয়। Paid GPU/model runs স্থগিত; no install/download/cloud call/commit।
