# Durable cleanup observation

2026-09-27। Cleanup outcome persistence/recovery reuse micro-step সম্পন্ন।

- [Ledger](../animation_studio/providers/gpu_attempts.py)-এ optional typed observation:
  resource ID, attempt ordinal, compute/storage, allowlisted errors/provider codes।
  Observation-এর resource/count/closed association validate হয়; raw error text নয়।
- [Durable recovery](../animation_studio/providers/gpu_durable_session.py)-তে intent
  write → cleanup → result write। নতুন intent পুরোনো observation clear করে।
  Result/fsync failure propagate; admission closed ও attempt count retained।
- Absent বা unauthorized observation-এ recovery আর backend call/count increment
  করে না। Nonterminal result bounded retry করে; cap-এ saved result থাকলে সেটি,
  না থাকলে unknown। Retained/unknown storage complete নয়।
- `ObservedCleanupResult` source current_call/saved/unknown ও observed_attempt
  দেয়; live_state_verified সবসময় false। state/complete শুধু ওই observation-এর
  অর্থ বহন করে; saved complete live cleanup/billing verification নয়।
- v1 session record-এ additive optional field: legacy absent → None; no destructive
  migration। পুরোনো binary নতুন field reject করবে। Receipt/deadline/lock ও production
  DB/schema অপরিবর্তিত। Existing cap test এখন repeated failure fixture ব্যবহার করে,
  কারণ একবার successful absent হলে নতুন semantics-এ cleanup আর repeat হয় না।

## Checks

[Observation tests](../tests/test_gpu_cleanup_observation.py) সহ durable acceptance/
session/lifecycle/offline/receipt/dispatch/ledger/budget/provider: **183 PASS**।
Saved absent তিন storage state, auth terminal, latest-attempt association, malformed
record, legacy unknown, result-write ও file/directory fsync failure, spawned process
exit before observation verified। আগের regression tests অন্তর্ভুক্ত। Ruff lint/format,
plan drift, links, RESUME length ও whitespace PASS।

## সীমা ও পরের কাজ

Historical mock observation; current resource state/query নয়। Directory fsync failure
এর পরে result file দৃশ্যমান হতে পারে—caller error পায়, subsequent recovery saved
observation দেখতে পারে। Missing result unknown, automatic success reconstruction নয়।
Cooperative mock/local trust ও তিন-attempt cap বহাল; live runtime/spend deferred।

পরের local micro-step: session/cleanup observation-এর read-only report scope review,
যাতে শুধু ফল দেখতে recovery/cleanup চালাতে না হয়। নতুন cleanup retry loop বা
completed acceptance restart নয়। No install/download/cloud call/payment/commit।
