# Phase 5.4 — D1 shared cooperative deadline integration

2026-10-10। Owner next-work নির্দেশে D1 source/tests সম্পন্ন।

## পরিবর্তন

- [Per-attempt budget](../animation_studio/providers/comfy_deadline.py) caller clock
  validates; nonfinite/negative/bool/backward/throwing clocks bounded failure দেয়।
  Existing resource decision-এর run/cleanup ceiling ও start/policy/worker/clock-session
  binding ধরে; recheck দিয়ে budget identity বদলানো যায় না।
- [Offline session](../animation_studio/providers/comfy_offline_session.py) synchronous
  execute attempt-এ scoped budget দেয়; finally-তে clear করে। Resource sample refresh
  recheck করা যায়, কিন্তু policy/start relabel করে ceiling বাড়ানো যায় না।
- [HTTP executor](../animation_studio/providers/comfy_http.py) preflight/submit/poll/view
  একই run ceiling ব্যবহার করে। প্রথম HTTP budget-এর ছোট timeout_seconds cap-ও
  retained; পরের stage সেটি reset করে না। Chunk checks ও poll wait remaining budget
  মানে। [Transport](../animation_studio/providers/comfy_transport.py)-এ injected clock
  mock-only; session/HTTP/transport একই guarded clock ব্যবহার করে। Live factory unchanged।
- [Durable executor](../animation_studio/providers/comfy_v2_executor.py)-এ final
  deadline check intent-এর আগে। Intent লেখার পর expiry হলে record থাকে/no submit
  retry। Accepted receipt timeout-এ existing single durable cancel owner বহাল;
  cleanup budget min(now + 5, original cleanup_deadline)। Cleanup exhausted হলে
  attempt intent/unknown persist হয়, কোনো cancel dispatch নয়। Ack stop proof নয়।
- Session recovery active generation budget clear হওয়ার পরে আগের মতো fresh bounded
  host-clock GET-only; admission/sample clock লাগে না। Raw legacy mock callers-এর
  timeout/cleanup behavior unchanged। Schema ও live admission gates অপরিবর্তিত।

## Checks

A3 baseline 348 PASS evidence reused। Initial integration-এর পরে 284 relevant PASS;
expanded regression 595 PASS; final suite **598 PASS**, session **98 cases**।
D1-এ 17 নতুন cases; পুরোনো admission tests clock-call count-এর বদলে actual admission
callback বা inventory phase ব্যবহার করে, কারণ clock এখন প্রতি-I/O check-এও লাগে।

```sh
.venv/bin/python -m pytest -q tests/test_comfy_offline_session.py tests/test_comfy_http.py tests/test_comfy_transport.py tests/test_comfy_transport_composition.py tests/test_comfy_v2_executor.py tests/test_comfy_preflight.py tests/test_comfy_auth_workflow.py tests/test_comfy_cancel_crash.py tests/test_comfy_resource_guard.py tests/test_comfy_admission.py
```

নতুন coverage: inventory→submit→history→view decreasing budget; initial/inventory/
pre-intent/post-intent expiry; retained intent/no retry; accepted cleanup remaining
2/1/0 seconds; same-session/restarted GET-only recovery; policy/start/clock identity
replacement; invalid/throwing clock; bounded poll wait এবং slow stream close।
Network/DNS forbidden fixtures; GPU/model/native execution নয়। Ruff/check/format,
docs links/RESUME length, plan drift ও whitespace PASS। পুরোনো dirty কাজ সংরক্ষিত;
commit/install/download/server launch হয়নি।

## সীমা ও next

D1 cooperative scheduling/checks মাত্র; blocked synchronous/native work, native image
decode বা OS scheduling force-stop করে না। Concurrent shared-session use supported
নয়; single-owner synchronous lifecycle বহাল। Caller clock-domain labels hardware
attestation নয়; actual target collector/resource enforcement/live composition বাকি।
Final/reap reserve evaluator-এ আছে, কিন্তু এই HTTP client process reap করে না।

Real 5.4 GPU/native preflight আগের অনুমোদনসহ hardware না থাকায় blocked; unchanged
probe নয়। Next proposed owner-directed D2: offline session-এর independent supervision
boundary design (blocked I/O, owned child, durable recovery ও cleanup ownership),
existing dummy supervisor পুনরায় implementation নয়। D2 design-এর পর implementation
scope আলাদা হবে; এখন live/new phase/paid কাজের অনুমোদন নয়।
