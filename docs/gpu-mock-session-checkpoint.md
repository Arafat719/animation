# Cooperative mock render session

2026-09-27। অনুমোদিত runtime/admission/cleanup integration সম্পন্ন।

- [Source](../animation_studio/providers/gpu_mock_session.py): exact local mock
  provider/lifecycle/ledger নেয়; validated workload/config/render ID স্থির রাখে।
- Existing estimator pass হলে injected clock-এর start + configured maximum GPU
  minutes × 60 থেকে deadline। Absolute float deadline নিচের দিকে round করে;
  শূন্য/invalid/unrepresentable window reject। Deadline refresh হয় না।
- Submit-এর আগে existing controller tick; closed/deadline হলে MockSessionClosed,
  কোনো reservation/receipt/provider submit নয়। Successful submit-এর পর tick-এ
  observed overrun cleanup হয়। Returned queued job completion-এর দাবি নয়।
- Timeout/provider/persistence failure-এ cleanup ও original exception propagate;
  cleanup_result আলাদাভাবে পাওয়া যায়। Replay/cap/conflict এবং caller input rejection
  session বন্ধ করে না। Explicit finish/fail/tick আছে; queued receipt auto-finish নয়।
- Cleanup failure-তেও admission closed। Retained/unknown storage আলাদা থাকে;
  ledger lookup session বন্ধ হওয়ার পরেও independent read-only API।

## Checks

[Session tests](../tests/test_gpu_mock_session.py), lifecycle ও আগের offline/
receipt/dispatch/ledger/budget/provider tests: **157 PASS**। Exact boundary, fixed
deadline, early finish/fail, storage states, failed cleanup, timeout unknown receipt,
post-submit overrun, invalid clock/input, persistence failure, nonmock rejection
ও conservative float rounding verified। Ruff lint/format ও docs checks PASS।
Prior 120-test dispatch এবং 126-test supervisor evidence retained; supervisor unchanged।

## সীমা ও পরের কাজ

Single-caller, same-process cooperative wrapper। Blocking operation interrupt হয় না;
caller tick না করলে cleanup নিজে চলে না। Mock resource cleanup mock job queue cancel
করে না। Standalone API bypass সম্ভব; live runtime/billing cap দাবি নয়। Session clock/
closed state restart-persistent নয়; নতুন wrapper বানিয়ে deadline reset করা সম্ভব।
Ledger reservations/receipt-এর durability অক্ষত; production API/DB/schema অপরিবর্তিত।

পরের local micro-step: existing durable journal ও session identity মিলিয়ে restart-এ
deadline/closed state বজায় রাখার সীমিত scope review। Existing watchdog নতুন করে
তৈরি নয়; review-এর আগে নতুন persistence implementation নয়। Paid GPU/model runs
স্থগিত; no install/download/cloud call/payment/commit।
