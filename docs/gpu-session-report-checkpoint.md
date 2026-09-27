# Read-only session/cleanup report

2026-09-27। [Scope](gpu-session-report-scope.md)-এর implementation সম্পন্ন।

- [Ledger](../animation_studio/providers/gpu_attempts.py)-এ
  `LocalAttemptLedger(path).session_report(render_id='render')` যোগ হয়েছে।
  Frozen typed `SessionReport` original times, saved closed flag, cleanup count ও
  optional observation দেয়। `source` saved/unknown, compute/storage unknown fallback,
  `complete` historical outcome only; `live_state_verified` সবসময় false। এগুলি
  Python properties; persisted ledger schema বা serialization fields বদলায়নি।
- Reader একবার read-only/no-follow open করে whole ledger validate করে; lock,
  initialization, provider, recovery বা cleanup চালায় না। Active owner থাকলেও চলে।
  Unknown/legacy session → None; missing/corrupt ledger error propagate করে।
- Snapshot stale হতে পারে; saved closed flag owner liveness নয়, monotonic deadline
  audit-only। Saved absent/none বর্তমান resource/billing verification নয়।

## Checks

[নতুন tests](../tests/test_gpu_session_report.py) সহ ledger/durable session/cleanup
observation/durable acceptance/mock session/dispatch/receipt/offline acceptance/
lifecycle/budget/provider: **201 PASS**। Active/released/recovered owner, unknown
observation, storage variants, failure/auth result, invalid ID, missing/legacy/
corrupt/symlink file, immutable report ও atomic replacement after open verified।
Ledger bytes/directory entries অপরিবর্তিত এবং mutation/cleanup calls নিষিদ্ধ রেখে
reader পরীক্ষা হয়েছে। Ruff lint/format, plan drift, links ও whitespace PASS।

Command: `.venv/bin/python -m pytest -q` দিয়ে উপরের সংশ্লিষ্ট 12টি test file।
Direct `.venv/bin/pytest` launcher পুরোনো directory-র shebang-এর কারণে চলেনি;
বিদ্যমান interpreter দিয়ে tests PASS, environment edit/install করা হয়নি।

## সীমা ও পরের কাজ

Local trusted mock ledger only; CLI/UI/API/live inspection নয়। কোনো blocker নেই।
পরের একই-phase local micro-step: accumulated mock work-এর remaining-gap review;
completed acceptance restart বা নতুন feature নিজে থেকে যোগ নয়। Existing local
authorization বহাল; paid/model/production কাজের সীমা অপরিবর্তিত।
No install/download/cloud call/payment/commit।
