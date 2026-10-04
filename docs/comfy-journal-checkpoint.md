# Phase 5.4 — durable intent/receipt ও explicit recovery

2026-10-03। Owner next-work নির্দেশে একটি offline micro-step সম্পন্ন।
`DurableComfyExecutor` existing mock-only HTTP executor wrap করে; প্রতি logical
job-এর জন্য caller একটি স্থায়ী journal path দেয়। একই job-এর path বদলানো বা
ambiguous journal মুছে retry করা অনুমোদিত recovery নয়।

## Persistence ও recovery boundary

- Private existing local directory, Linux `flock` nonblocking exclusive lock;
  পুরো submit/poll বা recovery operation lock ধরে রাখে। Lock inode স্থায়ী।
- Network submit-এর আগে version-1 `intent` record: graph SHA256, mock mode,
  state; raw prompt/model files/media/credential নেই। Temporary 0600 file,
  file fsync, atomic replace, parent directory fsync-এর পরে submit হতে পারে।
- Valid acknowledgement পাওয়ার সঙ্গে সঙ্গে, polling-এর আগে `accepted` record
  ও canonical prompt UUID persist। Receipt-write failure হলে caller original
  in-memory receipt-সহ typed `io_error` পায়; polling/automatic resubmit হয় না।
- Existing journal থাকলে `execute` বন্ধ—successful, ambiguous বা corrupt যাই
  হোক। Crash-before-submit intent-ও conservatively blocked থাকে।
- Explicit `recover(graph)` record/version/schema ও graph digest যাচাই করে।
  Accepted receipt থাকলে existing prompt-এর bounded history/download GET চলে;
  submit/cancel POST নয়। Intent-only/missing/corrupt/mismatched record fail closed।
- Recovery নতুন bounded read deadline নেয়; আগের execution deadline revive করে না।
  Timeout/cancellation-এ receipt-সহ error আসে; recovery server mutation করে না।
- Record read maximum 4096 bytes, duplicate fields rejected, symlink journal/lock
  rejected। Version-1 intent-এর optional receipt অনুপস্থিত থাকাও readable; তা
  accepted হয় না। Existing application DB/schema বদলায়নি; migration নেই।
- HTTP executor-এর optional receipt callback ও GET-only recovery method যোগ;
  direct non-durable executor-এর আগের behavior/contract অক্ষত। Durable protection
  পেতে wrapper ও একই logical job-এর একই journal ব্যবহার করতে হবে।

## Checks

Prior 141 PASS baseline reused; final **166 PASS**, পাঁচ suites:
`test_comfy_journal.py`, `test_comfy_http.py`, `test_comfy_image.py`,
`test_comfy_workflow.py`, `test_image_provider.py`। 25 new cases cover persistence
ordering, exclusive ownership, lost ack, crash before HTTP, fsync/receipt-write
failure, immutable blocked intent, missing/corrupt/oversize/version/schema/symlink
records, workflow mismatch, GET-only timeout/cancel recovery ও initial v1 read。

Actual subprocess `os._exit(7)` after receipt persisted; fresh process recovered
same PNG via GET; combined request log-এ **একটিমাত্র POST /prompt**। Ruff
lint/format, plan drift ও docs/whitespace checks PASS। Install/GPU/live calls নেই।

## Limits ও next

Local filesystem durability assumes filesystem honors fsync/atomic rename;
network filesystem বা malicious directory owner supported নয়। Receipt missing
হলে remote identity অজানা, reconciliation/manual resolution বাকি। Cancellation
observation journal-এ নেই; record accepted মানে submission acknowledged, current
job state/success নয়। Recovery bytes-এর PNG verification existing image adapter-এর
দায়িত্ব; real media/GPU acceptance নয়। Raw HTTP executor নিজে duplicate-protected নয়।

Next authorized offline micro-step: durable submission/recovery-কে ImageProvider
result verification-এর সঙ্গে integrated acceptance-এ যুক্ত করা, fresh-process
recovery-সহ mock provenance/PNG/checksum পরীক্ষা। Phase 5.4 real image gate ও
GPU runtime preflight deferred; paid/live scope অনুমোদিত নয়।
