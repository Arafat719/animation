# Phase 5.4 — deterministic v2 mock journal storage

2026-10-04। একটি অনুমোদিত micro-step সম্পন্ন। New `comfy_storage.py`-তে
`ComfyJournalStore`; existing executor/v1 storage অপরিবর্তিত।

## Behavior

- Validated mock context থেকে private existing root-এর `<job_id>.json` path;
  live context rejected। Root owned directory ও group/other permissions বন্ধ
  হতে হবে। Root ancestors caller-trusted; hostile filesystem owner isolation নয়।
- `locked()` permanent `.json.lock` inode-এ nonblocking flock রাখে। একই thread-এর
  active lock ছাড়া read/create/accept নয়; caller future full transaction জুড়ে lock
  ধরে রাখতে পারবেন। Concurrent owner, nested lock ও cross-thread operation rejected।
- `create_intent` existing path (corrupt/v1/symlinkসহ) overwrite করে না। `accept`
  existing v2 identity-matched intent ছাড়া কাজ করে না; accepted receipt বদলায় না।
- Write-এর আগে serialized bytes cap ও identity validation; private temp file,
  file flush/fsync → atomic replace → directory fsync। Failures propagate; automatic
  retry নেই। Replace-এর পরে directory fsync failure হলে visible record থাকতে পারে,
  durability অজানা; existing-record guard বহাল, resubmit নয়।
- Read bounded 4097 bytes, no-follow/nonblocking open, regular-file check ও existing
  context matcher ব্যবহার করে। FIFO/symlink rejected। Temp files normal exception-এ
  cleanup হয়; permanent lock unlink হয় না। Abrupt crash-এর orphan temp cleanup এই
  step-এ নেই; temp file কখনো authoritative job record হিসেবে পড়া হয় না।
- Migration boundary: v1 files preserved, no in-place promotion। Existing v1 parser/
  executor regressions বহাল; নতুন store v2-only, existing DB schema অপরিবর্তিত।

## Checks

**357 tests PASS** = previous 337 + 20 storage cases; nine suites (storage, identity,
journal, durable image, HTTP, image, workflow, image provider, preflight)।
`.venv/bin/python -m pytest -q` দিয়ে চালানো হয়েছে।
New tests: deterministic path/restart/0600 permissions, lock ownership/release,
legacy/corrupt/oversize preservation, symlink/FIFO rejection, invalid receipt/context,
file-fsync/replace/directory-fsync failure states, fsync ordering, write-size guard,
unsafe root/live rejection, actual subprocess abrupt exit → retained intent/no
recreate, failure-before-replace explicit retry। Ruff lint/format checks PASS।

## Limits / next

Storage এখনো execution/submission-এর সঙ্গে wired নয়। Same logical job-এর জন্য একই
private root/job ID রাখতে হবে; নতুন root/ID দিয়ে global duplicate prevention নেই।
Caller-controlled local receipt storage remote receipt authenticity proof নয়।
Install/network/GPU/model load হয়নি; Phase 5.4 real-image gate অসম্পূর্ণ।

Next authorized offline micro-step: mock v2 durable executor integration—lock ধরে
preflight → intent → single submit → receipt persist; identity-matched accepted
GET-only recovery। v1 compatibility ও no-resubmit failure testsসহ; live enable বা
নতুন phase/5.5 নয়। Owner installation ও paid-resource restrictions বহাল।
