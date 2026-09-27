# এক command-এ offline session demo

2026-09-27। অনুমোদিত temporary synthetic session demo সম্পন্ন।
Repository root থেকে চালান:

```sh
.venv/bin/python -m scripts.demo_gpu_session
```

RunPod account, GPU, model, personal input, package install বা আগে তৈরি ledger
লাগে না। [Demo script](../scripts/demo_gpu_session.py) নতুন temporary directory-তে
একটি synthetic mock session তৈরি করে existing [report command](gpu-local-report-command.md)
দিয়ে বাংলা ফল দেখায়। Existing ledger path নেওয়ার option নেই।

1. Cleanup-এর আগে saved observation নেই: compute/storage অজানা।
2. একবার `mock.noop` submit: queued acceptance; media completion নয়।
3. Mock cleanup ও owner release-এর পরে report: compute অনুপস্থিত, storage রয়ে গেছে,
   admission বন্ধ, cleanup attempt 1, historical complete না।
4. Demo শেষে শুধু তার নিজস্ব temporary directory মুছে যায়। Mock retained storage
   simulated observation; বাস্তব billable storage তৈরি হয়নি।

Fixture rate/budget zero, clock fixed; কোনো actual price বা elapsed-time benchmark
নয়। Expected local file/validation/provider error-এ exit 1 ও সংক্ষিপ্ত error বার্তা;
success exit 0। Temporary directory exception হলেও context manager দিয়ে পরিষ্কার হয়।
অপ্রত্যাশিত programming error success হিসেবে লুকানো হয় না।

## Checks

[Demo tests](../tests/test_gpu_session_demo.py) + CLI/report/durable session/cleanup
observation: **59 PASS**। Network socket নিষিদ্ধ রেখে দুইবার demo, user file অক্ষত,
temporary paths removed, injected write failure/nonzero exit ও real module entrypoint
verified। Agent সরাসরিও command চালিয়েছে: expected বাংলা report, exit 0। Ruff
lint/format, docs links/plan drift/whitespace/RESUME checks PASS।

## বর্তমান সীমা ও পরের ব্যবহার

এটি runnable mock behavior demo, animation/video/model inference নয়। Application
API/UI/DB ও provider implementation বদলায়নি। Blocker নেই; RunPod/quote/payment ও
CPU model experiments স্থগিত। Install/download/commit হয়নি।
এই command ও report slice সম্পন্ন। পরের ব্যবহারিক ধাপ owner-এর local demo দেখা ও
নির্দিষ্ট feedback; বর্তমান local scope-এর bug fix অনুমোদিত, নতুন feature/phase
নিজে থেকে শুরু নয়। নতুন অনুমোদিত concrete কাজ নির্দিষ্ট না হলে completed demo
বা acceptance আবার বানাবে না, RunPod তথ্যও চাইবে না।
