# Phase 5.4 — D3 fixed offline session child supervision

2026-10-10। Owner next-work নির্দেশে D2-এর একক implementation scope সম্পন্ন।

## পরিবর্তন ও ownership

[Parent supervisor](../animation_studio/providers/comfy_session_supervisor.py) Linux
same-host fixed module entry point চালায়। Caller-owned private root, matching mock
context/graph এবং policy validate করে; spawn-এর আগে original run/cleanup/final
ceilings existing resource evaluator থেকে নেয়। Parent নিজে HTTP dispatch, generation
journal mutation, child-owned lock acquire বা automatic recovery করে না।

[Fixed child](../animation_studio/providers/comfy_session_child.py)-তে existing
OfflineDurableComfySession + D1 budget, synthetic inventory/admission/telemetry ও PNG
fixture compose করা হয়েছে। Tests package থেকে import নেই। Child socket/DNS নিষিদ্ধ;
secret synthetic এবং child-local। Arbitrary executable/PID/callback API নেই; fixed
normal/startup-hang/inventory-hang/history-hang/cooperative এবং intent/cancel-hang
fault scenarios মাত্র। Child descendants তৈরি করে না।

Parent nonblocking stdin/stdout IPC ব্যবহার করে; JSON প্রতি message সর্বোচ্চ 64 KiB,
strict field/identity/duplicate-key/nonfinite validation, partial-message buffering
ও terminal uniqueness check আছে। Child-এর PNG bytes/traceback/token IPC-তে যায় না।
Bounded terminal result এবং confirmed exit দুটো ছাড়া fixture success নয়। Deadline
পেরোলে late verified result retained হলেও timely success ঘোষণা করা হয় না।

Run expiry/caller cancel-এ parent এক stop notification queue করে; child watcher local
cancel Event সেট করে। Notification queue/delivery acknowledgement নয়। কেবল child
same-lock durable path receipt থাকলে cancel পাঠায়। Cleanup deadline-এ stuck owned
child-কে SIGKILL; final reserve-এ bounded reap। Parent parallel cancel বা job retry নয়।
Startup/handshake original window খরচ করে; child message/ready budget বাড়ায় না।

Primary exception/KeyboardInterrupt অক্ষত রেখে independent poll/kill/reap/pipe-close
cleanup চলে। Failed cleanup-এ exception.session_child_cleanup retained Popen handle,
original final deadline ও bounded error codes রাখে; exception.session_child_terminal
থাকলে আগের terminal result রাখে। Private errors repr-এ নেই। Normal unconfirmed exit
needs_manual_cleanup result-এ handle থাকে; returncode=None-কে exited বলা হয় না।

Accepted/intent/cancel-intent journal child-ই লেখে; kill-এর পরে byte-preserved record
থেকে caller-directed recovery। fixture_session helper দিয়ে explicit fresh fixture
GET-only recovery করা যায়; confirmed child exit এবং same root/context নিশ্চিত করা
caller-এর দায়িত্ব। এটি package-wide bypass prevention নয়; parent recovery চালায় না।

## Checks

D1 598 PASS ও D2-তে referenced C3/I1 evidence baseline হিসেবে reused।
[New suite](../tests/test_comfy_session_supervisor.py): **29 cases**। Final relevant
combined **214 PASS**:

```sh
.venv/bin/python -m pytest -q tests/test_comfy_session_supervisor.py tests/test_comfy_offline_session.py tests/test_comfy_v2_executor.py tests/test_comfy_cancel_crash.py tests/test_comfy_cpu_dummy_integration.py tests/test_comfy_supervised_recovery.py
```

Coverage: normal validated fixture PNG; unrelated sentinel child untouched; startup/
inventory/history/intent/cancel hangs; owned SIGKILL/reap; intent-only unknown and
accepted GET-only recovery; single cooperative cancel; cancel-intent attempt consumed;
malformed/oversize/duplicate/wrong identity/partial/EOF IPC; invalid launch zero spawn;
parent error/KeyboardInterrupt; failed kill/reap/pipe close; retained unknown exit;
startup clock shared without reset। All test-owned children bounded finally cleanup।

Initial combined run-এ এক history-hang test startup allowance কম হওয়ায় boundary-তে
পৌঁছায়নি: ledger-এ six inventory GET, journal নেই। Test-only policy run window 1.5s
থেকে 3s করা হয়েছে; production defaults/limits বদলায়নি। Hang tests original 3.75s
cleanup deadline, elapsed 3.5–6s scheduling tolerance এবং per-test 15s external
watchdog ব্যবহার করে। App source failure hide/test skip নয়।

Ruff/check/format, docs links/RESUME length, plan drift ও whitespace PASS। Existing
schema/requirements অপরিবর্তিত; migration/master edit প্রয়োজন নেই। আগের dirty কাজ
preserved; কোনো commit/install/GPU/model/server/live network/paid কাজ হয়নি।

## প্রকৃত সীমা ও next

এটি fixed offline session time/process supervision। RAM/VRAM sample synthetic;
client child exit remote job/worker/compute/storage stop proof নয়। Actual memory
measurement/enforcement, worker-tree ownership, target evidence collector ও live
production composition বাকি। Parent spawn/OS scheduling/kernel wait/parent death-এর
absolute hard guarantee নেই; IPC/monitor loop cooperative, blocked child separately
kill করা যায়। Trusted same-owner root/ancestors প্রয়োজন।

Fixture PNG existing image provider দিয়ে child-এ validate/save হয়; terminal message
একটি owned fixture-child claim, target image attestation নয়। Files private root-এর
fixture-images-এ থাকে; API/UI delivery 5.5 নয়। Caller retained cleanup handle হারাবে
না এবং unknown exit অবস্থায় recovery/relaunch করবে না।

D3 complete; full L4/5.4 incomplete। পরের নির্ধারিত real micro-step owner-selected
GPU environment-এ bounded native/runtime preflight; আগের authorization বহাল কিন্তু
hardware absence-এ blocked। একই GPU probe পুনরায় নয়। নতুন offline implementation
scope এই checkpoint নির্ধারণ করে না; live/paid/5.5/new phase অনুমোদিত নয়।
