# RunPod ছাড়াই local session report

2026-09-27। Owner RunPod বাদ দিয়ে local কাজ করতে বলেছেন। সেই নতুন scope-এ
existing read-only report-এর terminal entrypoint সম্পন্ন; নতুন phase নয়।

Repository root থেকে existing ledger ও original render ID দিয়ে চালান:

```sh
.venv/bin/python -m scripts.report_gpu_session --ledger /path/to/ledger.json --render-id render
```

`/path/to/ledger.json` উদাহরণ; বাস্তব local mock ledger path বসাতে হবে। Help:

```sh
.venv/bin/python -m scripts.report_gpu_session --help
```

[Command](../scripts/report_gpu_session.py) বাংলায় compute/storage আলাদা দেখায়,
saved admission/cleanup attempts এবং historical complete outcome জানায়। Report
সবসময় স্পষ্ট করে current GPU/billing verified নয়। Retained/unknown storage-এ
billing বন্ধ ধরে না নেওয়ার বার্তা থাকে। এটি GPU চালায়/বন্ধ করে না; provider,
recovery, initialization বা ledger write নেই। Python report implementation reuse।

Exit code 0 = report পড়া গেছে (cleanup success নয়); 1 = session record নেই;
2 = missing/unreadable/invalid ledger বা invalid arguments। Error output raw ledger
content বা validation input ছাপায় না। No session/observation মানে unknown।

## Checks ও সীমা

[CLI tests](../tests/test_gpu_session_report_cli.py) সহ report/durable session/cleanup
observation: **56 PASS**। তিন storage state-এ real subprocess entrypoint, active owner,
missing/corrupt/empty records, unchanged ledger bytes/sidecars verified। Lint fix-এর
পরে সাত CLI test আবার PASS; Ruff lint/format ও docs checks PASS। Prior 207-test
broader evidence retained; এই turn-এ full app suite নয়।

Existing local ledger প্রয়োজন; sample session generation এই step-এ নেই। Historical
mock report real inference/media proof নয়। Blocker নেই। পরের অনুমোদিত local
micro-step: আলাদা temporary directory-তে synthetic session তৈরি করে এই command
ব্যবহারের reproducible offline demo; personal data/model/network নয়।

RunPod quote/screenshot/payment request আর pending নয়; owner নির্দিষ্টভাবে
পুনরারম্ভ না চাইলে এই পথে ফিরবে না। No install/download/cloud call/commit।

2026-09-27 update: [এক command-এর offline demo](gpu-offline-demo.md) সম্পন্ন; আগের
next-demo নির্দেশ fulfilled। আলাদা local ledger ছাড়াই demo দেখা যায়।
