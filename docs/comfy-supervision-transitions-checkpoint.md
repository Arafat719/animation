# Phase 5.4 — guarded mock cleanup transitions

2026-10-04। Owner next-work নির্দেশে এক micro-step সম্পন্ন।

- `ComfySupervisionStore.transition` same-job lock ধরে কেবল not_requested → intent
  → observed/unknown মঞ্জুর করে। Intent reservation-এ attempt_count=1; intent,
  observed বা unknown থেকে আর intent নয়। Missing sidecar automatic permission নয়।
- প্রতিটি transition-এ strict bounded schema/context revalidation ও v2 generation
  accepted receipt exact match। Existing receipt, primary outcome ও created_at
  অপরিবর্তিত; updated_at পেছানো যাবে না। Generation journal bytes বদলায় না।
- Shared atomic writer file fsync → replace → directory fsync ব্যবহার করে। Write
  failure propagate হয়। Directory-fsync failure-এর পরে visible intent থাকলে retry
  blocked; pre-replace failure-এ পূর্বের state থাকে। কোনো dispatch এই API করে না।
- Observed cancellation acknowledgement compute/job terminal status তৈরি করে না।
  Same process-এর নতুন store দিয়ে restart boundary checked; actual process crash
  simulation এই step-এ নতুন করে করা হয়নি।

## Checks

Supervision storage/schema + generation storage/identity/journal suites:
**287 PASS** (12 new transition cases)। Ruff lint/format PASS; docs links, RESUME
length, plan excerpt drift ও whitespace PASS। Prior unchanged workflow baseline
reused; broader suite নতুন করে চালানো হয়নি।

Coverage: observed/unknown terminal guard, missing sidecar/journal, intent-only
journal, wrong receipt, outcome/time mutation, skipped transition, fsync failure,
reopen duplicate intent rejection ও generation bytes preservation।

## Limits / next

Guard cooperating callers-এর জন্য; create এখনও standalone validated mock snapshot
সংরক্ষণ করতে পারে, dispatch permission নয়। Transition legacy v1 journal গ্রহণ
করে না; existing v1 read/create compatibility অপরিবর্তিত। Evidence digest lookup,
resource monitoring, process supervision বা live cleanup নেই। Current HTTP executor
cancel memory-only-ই আছে; এই guard সেখানে wired নয়।

Next proposed owner-directed micro-step: mock executor cancellation-এর সঙ্গে
এই durable intent/observation integration; একমাত্র dispatch owner নির্ধারণ ও
failure/restart tests। Live transport/process launch/paid action নয়। Real 5.4 pending।
