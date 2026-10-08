# Phase 5.4 — supervised mock child-exit recovery acceptance (I1)

2026-10-05। Owner next-work নির্দেশে এক test-only micro-step সম্পন্ন।
[Dummy supervisor](comfy-dummy-supervisor-checkpoint.md)-এর পরে durable recovery
ও duplicate prevention-এর combined acceptance; production wiring নয়।

## Evidence

[New test](../tests/test_comfy_supervised_recovery.py) test-local Popen substitution
দিয়ে fixed mock executor child চালায়; production dummy-only API পরিবর্তন হয়নি।
Parent actual supervise_dummy/evaluator চালায়; child নির্বাচিত fsync/dispatch
boundary-তে ready byte পাঠিয়ে SIGTERM উপেক্ষা করে। Synthetic telemetry হারালে
parent abort→SIGTERM→SIGKILL→reap করে। Parent ও child execution context মেলে।

| Boundary | Generation journal | Submit / cancel count |
| --- | --- | --- |
| Intent fsync, submit-এর আগে | intent | 0 / 0 |
| Mock submit handled, receipt persist-এর আগে | intent | 1 / 0 |
| Accepted receipt fsync | accepted | 1 / 0 |
| Durable cancel observation fsync | accepted + observed sidecar | 1 / 1 |

প্রতি case-এ এক child, exit -SIGKILL, waitpid দিয়ে already-reaped proof;
job/compute/storage unknown। Request ledger flush/fsync হয়; child socket/DNS
forbidden। এরপর দুটি পৃথক fresh recovery process: duplicate execute rejected,
intent-only recovery rejected with zero requests; accepted recovery শুধু history/view
GET করে এবং fixture PNG bytes মেলায়। Generation/sidecar bytes অপরিবর্তিত।
Observed cancel case-এ explicit same-lock cleanup re-entry-ও নতুন cancel পাঠায় না।
Sidecar না থাকলে recovery নতুন sidecar বা guessed cancel তৈরি করে না।

## Checks

- Prior unchanged relevant baseline 238 PASS reused।
- Initial combined run: new supervised recovery + dummy supervisor + cancel crash +
  v2 executor + supervision storage: **75 PASS**।
- Context/state/sidecar assertions শক্ত করার পরে new 4 cases rerun: **4 PASS**।
  Counts overlapping, যোগ করা হয়নি।
- Ruff lint/format, docs links/RESUME length, plan drift ও whitespace PASS।

## Limits ও next

No production source/schema edits, real network/GPU/model/server বা paid action।
Fresh process mock server fixture reconstruct করে; এটি বাস্তব remote server
persistence, host power-loss durability বা remote stop proof নয়। Test-only launch
substitution production supervised executor integration-এর implementation নয়।
Recovery এখানে fixture PNG bytes verify করে; নতুন UI/artifact registration নয়।
Offline I1 acceptance-এর blocker নেই; real image gate এখনও GPU-dependent।

পরের owner-directed micro-step: consolidated readiness/gap review হালনাগাদ করে
completed R1–R7/P1–P3/I1 এবং remaining production telemetry/enforcement/composition
আলাদা করা, তারপর পরের কার্যকর GPU-independent scope নির্ধারণ। Completed crash
বা GPU prerequisite checks পুনরায় নয়। এই completion নতুন live/new phase অনুমোদন নয়।
