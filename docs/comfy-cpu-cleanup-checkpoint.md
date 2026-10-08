# Phase 5.4 — C3 exceptional cleanup ownership fix

2026-10-08। Owner next-work নির্দেশে readiness review-এর একক bug fix সম্পন্ন।

[Source](../animation_studio/providers/comfy_cpu_dummy_integration.py): parent বা
cleanup exception-এর original type/object/traceback propagate হয়; তার
cpu_dummy_cleanup attribute-এ frozen CpuDummyCleanup session থাকে। Owned child,
sampler ও original final deadline retained; worker/sampler status, bounded error
codes ও closed/needs_manual_cleanup outcome থাকে। Original cleanup exceptions
private errors tuple-এ থাকে, repr-এ নয়; parent exception-এর আসল text অপরিবর্তিত,
সেটি public log-এ প্রকাশের অনুমোদন নয়।

Stop, poll, kill, bounded reap, sampler close, pipe close ও final poll স্বাধীনভাবে
চেষ্টা হয়। একটি action failure অন্য cleanup বাদ দেয় না। TimeoutExpired মানে
unknown worker; deadline reset/retry/unbounded wait নয়। Parent error থাকলে সেটিই
primary; না থাকলে first cleanup error propagate হয়। KeyboardInterrupt-ও cleanup
শেষে original object হিসেবে propagate। Normal result/API আচরণ অপরিবর্তিত।

Caller exception.cpu_dummy_cleanup ধরে রাখবে এবং unknown worker/sampler-এর
cleanup পরে confirm করবে। Cleanup action error হলে conservative manual-cleanup
status; failed pipe close-এর handle-ও retained child-এর মাধ্যমে পাওয়া যায়।
OS/GIL starvation বা দ্বিতীয় asynchronous interruption-এর hard guarantee নেই;
blocked read force-kill করা হয় না। Real/live/model/paid scope পরিবর্তন নেই।

## Checks

[Tests](../tests/test_comfy_cpu_dummy_integration.py)-এ **5 new cases**:
OSError/KeyboardInterrupt + hung sampler; sampler stop/close failures; parent
error + failed kill + unknown worker। Original exception identity, bounded wait,
independent cleanup, handle retention ও repr privacy asserted। Fixtures finally
blocked read release/join ও child reap করেছে।

Existing 315 PASS baseline reused; combined **320 PASS**:
```sh
.venv/bin/python -m pytest -q tests/test_comfy_cpu_dummy_integration.py tests/test_comfy_ram_sampler.py tests/test_comfy_cpu_guard.py tests/test_comfy_ram_telemetry.py tests/test_comfy_resource_guard.py tests/test_comfy_supervision.py
```
Ruff lint/format, plan excerpt drift, doc links/RESUME length ও whitespace PASS।
Unrelated dirty files সংরক্ষিত; commit/install/model/GPU run হয়নি।

## Next

C3 review finding resolved; এই scoped fix-এর blocker নেই। পরের pending real 5.4
micro-step available GPU environment-এ bounded CUDA/native runtime preflight;
আগের authorization বহাল, GPU/environment বদলের তথ্য ছাড়া একই probe পুনরায় নয়।
GPU gate এখনও blocked। Live transport/supervised production composition বাকি;
5.5/new phase বা paid launch অনুমোদিত নয়।
