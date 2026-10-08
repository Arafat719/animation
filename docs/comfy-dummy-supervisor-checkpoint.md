# Phase 5.4 — owned dummy-child supervisor

2026-10-05। Owner next-work নির্দেশে [resource design](comfy-resource-guard-design.md)
P1–P3 micro-step সম্পন্ন। Existing 223 PASS relevant baseline পুনর্ব্যবহার করা হয়েছে।

## Implementation

[Supervisor](../animation_studio/providers/comfy_dummy_supervisor.py) শুধু তিনটি fixed
stdlib dummy mode চালায়: normal, cooperate, ignore_stop। Arbitrary command/PID,
callback, real Comfy server, model বা descendants launch interface নেই। Child নিজের
নতুন session-এ চলে; signal শুধু owned Popen child-কে যায়। Shell ব্যবহার হয় না।

Parent existing evaluator দিয়ে synthetic mock telemetry admission/running সিদ্ধান্ত
নেয়। Missing-at-admission হলে zero spawn; ready byte-এর পরে telemetry হারালে abort।
এক start থেকে startup/run/cleanup/reap deadlines; progress বা signal-এ reset নয়।
SIGTERM dummy cooperative stop, cleanup deadline-এ SIGKILL, final deadline পর্যন্ত
poll/reap। Ready pipe nonblocking, output fixed one byte; stdout backpressure বা
blocking telemetry callback নেই। No automatic relaunch, no remote cancellation।

Normal exit বা stop race-এ return code ও reaped status থাকে। Failed reap-এ
needs_manual_cleanup/worker unknown; job/compute/storage সবসময় unknown। Synthetic
telemetry source explicit; fake zero RSS/VRAM বাস্তব reading হিসেবে report নয়।
Exception-path cleanup-ও bounded; Popen context manager-এর implicit unbounded wait নেই।

## Checks

[15 new tests](../tests/test_comfy_dummy_supervisor.py): real child normal exit,
cooperative stop, ignore-stop kill/reap; telemetry disappearance; admission denial;
invalid/live input no launch; simulated exit/signal race; unrelated live child
untouched; simulated unkillable/reap timeout; parent setup error cleanup।
Real child-এ waitpid ChildProcessError দিয়ে already-reaped verification।
1.2-second test policy-তে scheduling tolerance 0.75s; এটি production SLA নয়।
Reap-failure fixture ও signal race deterministic simulations, real kernel failure নয়।

`.venv/bin/python -m pytest -q tests/test_comfy_dummy_supervisor.py
 tests/test_comfy_resource_guard.py tests/test_comfy_supervision.py
 tests/test_comfy_supervision_storage.py tests/test_comfy_v2_executor.py`
(এক লাইনে): **238 PASS**। New source/tests Ruff lint/format PASS;
docs links/RESUME length/plan drift/whitespace checks PASS।

## সীমা, blocker ও next

এই supervisor dummy-only; target RAM/VRAM measurement বা hard memory cap নয়।
Owned direct child ছাড়া process-tree kill প্রমাণ নেই; fixed child descendants তৈরি
করে না। OS process creation/scheduling, uninterruptible wait বা parent/host death
absolute time guarantee-এর বাইরে। Failed reap-এ caller manual follow-up প্রয়োজন।
Local worker exit কখনো remote execution/billing stop proof নয়। No persistence বা
existing v2 executor wiring পরিবর্তন; valid artifact/journal integration এখনো বাকি।

Offline micro-step-এর blocker নেই। পরের owner-directed একক কাজ: I1-এর mock durable
executor/child-exit integration acceptance—accepted GET-only recovery, intent-only
no resubmit ও existing single-cancel guard অক্ষত থাকার evidence। Fixed dummy
supervisor-কে arbitrary/live process launcher করা এই authorization নয়। GPU image
ও production supervision deferred; new phase/paid action আলাদা gates বহাল।
