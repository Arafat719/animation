# Durable session restart: integrated offline acceptance

2026-09-27। এই local slice PASS; পূর্ণ Phase 4 acceptance নয়।

[Scenario](../tests/test_gpu_durable_acceptance.py)-এ spawned owner process একই
ledger-এ দুই shot চালায়। Pipe handshake দিয়ে owner জীবিত থাকা অবস্থায় দ্বিতীয়
owner rejection পরীক্ষা; real-time sleep বা external service নেই।

| ধাপ | Observed ফল |
| --- | --- |
| Fresh session, প্রথম submit | Submitted receipt পাওয়া যায় |
| Active owner থাকা অবস্থায় recovery | BlockingIOError; দ্বিতীয় owner rejected |
| দ্বিতীয় submit accepted, তারপর immediate process exit | Exit 7; reservation আছে, receipt নেই/unknown |
| একই render fresh create | LedgerConflict; নতুন allowance নয় |
| Clock 100 থেকে 0 দিয়ে recovery | Original start 100 ও deadline 700 অক্ষত; admission closed |
| Recovery cleanup | Fixture compute absent; storage unknown, complete false |
| পুরোনো accepted/unknown ও নতুন key submit | সব MockSessionClosed; zero new provider jobs |
| Receipt lookup | প্রথম receipt retained, দ্বিতীয় unknown, নতুন key absent |
| Final durable state | Closed true, cleanup attempt 1; reservation map অপরিবর্তিত |

Receipt current job availability/completion নয়। Crash-এর পর নতুন mock provider-এ
পুরোনো jobs নেই। Resource/storage observation recovery fixture-এর; real Pod নয়।

## Checks

```sh
.venv/bin/python -m pytest -q tests/test_gpu_durable_acceptance.py tests/test_gpu_durable_session.py tests/test_gpu_mock_session.py tests/test_gpu_lifecycle.py tests/test_gpu_offline_acceptance.py tests/test_gpu_mock_receipt.py tests/test_gpu_mock_dispatch.py tests/test_gpu_attempts.py tests/test_gpu_budget.py tests/test_gpu_provider.py
```

ফল: **171 passed**। Ruff lint/format, plan excerpt drift, document links, RESUME
length ও whitespace PASS। Source/production DB/UI/API অপরিবর্তিত; নতুন integration
test/report ও status update মাত্র। Existing edits retained।

## বাকি সীমা ও পরের কাজ

Cleanup observation durable session record-এ থাকে না; original journal-এর cleanup
outcome-এর মতো এটি সংরক্ষিত নয়। বর্তমানে recovery পুনরায় fixture cleanup করে এবং
cap-এ unknown দেয়। পরের local micro-step: durable cleanup outcome সংরক্ষণ ও
recovery-তে reuse-এর scope review; historical observation-কে live state বলা যাবে না।
Completed restart admission/receipt slice আবার restart নয়।

Production runtime/spend/live provider wiring ও real GPU acceptance deferred।
Paid GPU/quote/payment এবং CPU model experiments স্থগিত। No install/download/
cloud call/payment/commit; local fixtures কোনো real media/inference proof নয়।
