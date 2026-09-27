# Budget থেকে mock receipt: bounded offline acceptance

2026-09-27। এই local slice-এর integrated acceptance PASS; পূর্ণ Phase 4 নয়।

## Scenario ও observed ফল

[Acceptance test](../tests/test_gpu_offline_acceptance.py) একই temporary ledger-এ
দুই shot, প্রতি shot সর্বোচ্চ দুই attempt এবং exact in-memory mock provider চালায়।
Fixture rate USD 1/hour, reserved GPU minutes 4, estimated compute USD 0.066667;
এগুলো synthetic estimate, live quote বা incurred spend নয়।

| ধাপ | যাচাইকৃত ফল |
| --- | --- |
| Zero-cost allowance দিয়ে admission | BudgetExceeded; zero provider calls, ledger unchanged |
| প্রথম shot submit | Receipt-এ mock job ID ও submitted outcome |
| দ্বিতীয় shot accepted, fixture response lost | Timeout caller-এ ফেরে; reserved slot, receipt absent/unknown |
| Ledger reopen ও নতুন mock provider | Submitted receipt ও unknown state দুটোই retained |
| দুই key replay | AttemptAlreadyReserved; zero additional calls, ledger unchanged |
| প্রথম shot-এর explicit পৃথক দ্বিতীয় attempt | Ordinal 2; আরও একটি mock submit |
| প্রথম shot-এর তৃতীয় attempt | AttemptLimitExceeded; কোনো অতিরিক্ত submit/reservation নয় |
| Unknown দ্বিতীয় shot | Unknown-ই থাকে; automatic retry করা হয়নি |

মোট observed submit calls 3; প্রথম provider-এ দুইটি accepted mock job, reopen-এর
পর provider-এ শুধু explicit পৃথক attempt। Lookup raw prompt persist করে না।
এটি deterministic fixture failure; real network/GPU/inference চালানো হয়নি।

## Reproduce ও checks

```sh
.venv/bin/python -m pytest -q tests/test_gpu_offline_acceptance.py tests/test_gpu_mock_receipt.py tests/test_gpu_mock_dispatch.py tests/test_gpu_attempts.py tests/test_gpu_budget.py tests/test_gpu_provider.py
```

ফল: **120 passed**। Ruff lint/format, plan excerpt drift, relative document links,
RESUME length ও whitespace PASS। Existing tests-এর process crash/concurrent admission/
write failure evidence এই suite-এ পুনরায় PASS; নতুন scenario আলাদা lifecycle refactor নয়।
Source API/DB/UI অপরিবর্তিত; শুধু acceptance test ও report/status যোগ হয়েছে।

## সীমা ও পরের scope

Receipt historical acceptance, execution success নয়। Mock provider memory-only;
নতুন instance-এর job ID পুরোনোটির সঙ্গে মিলে যেতে পারে, তাই receipt দিয়ে ওই নতুন
provider-এর live status দাবি করা হয়নি। Unknown outcome পুনরায় submit নয়। Local
trusted ledger/IDs-এর সীমা, production gate/runtime caps/spend accounting বাকি।
Phase 3 real planner এবং Phase 4 real health/inference/lifecycle acceptance deferred।
Paid GPU/quote/payment ও CPU model experiments স্থগিত। No install/download/cloud call।

এই budget/reservation/dispatch/receipt slice আবার restart নয়। পরের local micro-step:
বিদ্যমান runtime-cap requirement ও mock lifecycle source মিলিয়ে সীমিত integration
scope review; নতুন phase নয়, review শেষে একটি অসম্পূর্ণ কাজ নির্দিষ্ট করতে হবে।
