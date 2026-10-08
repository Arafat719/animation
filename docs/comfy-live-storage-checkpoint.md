# Phase 5.4 — L4.1 live-mode journal storage

2026-10-08। Owner L4 next-work নির্দেশে প্রথম একক implementation micro-step
সম্পন্ন: standalone live-mode v2 journal persistence ও backward compatibility।
পূর্ণ L4 durable live executor composition/supervised acceptance এখনও অসম্পূর্ণ।

## পরিবর্তন

[Storage](../animation_studio/providers/comfy_storage.py)-এ explicit
`LiveComfyJournalStore` যোগ হয়েছে। Existing `ComfyJournalStore` শুধু mock context
নেয়; নতুন constructor শুধু live context নেয়। Constructor কোনো file/network খুলে
না। Same validated context, private root, atomic fsync/replace write, same job path
ও permanent lock reuse করে। একই root/job-এ mode পাল্টিয়ে intent bypass হয় না;
context mismatch-এ read/accept বন্ধ, existing record overwrite হয় না।

Schema অপরিবর্তিত: v2-তে `mode=live` আগে থেকেই ছিল। তাই নতুন migration নেই।
v1 mock journal original parser-এ readable থাকে; v2 store v1-কে upgrade করে না।
Existing v2 mock/live bytes read-এ rewrite হয় না; কোনো mock-to-live relabel নেই।

Live storage একটি local bookkeeping capability; trusted runtime/GPU/model বা
endpoint attestation নয়। Caller-supplied context/receipt-এর syntax যাচাই করে,
receipt remote server থেকে এসেছে এমন প্রমাণ দেয় না। Existing mock executor ও
supervision store live context/store reject করে; তাদের live gate খুলে দেওয়া হয়নি।

## Checks

Relevant pre-change baseline **242 PASS**। Final **290 PASS**, যার মধ্যে shared
storage suite mock/live দুই mode-এ চলে; net 48 additional cases। Socket/DNS
forbidden fixture; local process-exit test lock release/intent persistence যাচাই করে।

```sh
.venv/bin/python -m pytest -q tests/test_comfy_storage.py tests/test_comfy_identity.py tests/test_comfy_journal.py tests/test_comfy_v2_executor.py tests/test_comfy_supervision_storage.py
```

[Tests](../tests/test_comfy_storage.py): roundtrip/restart, permission/lock/thread,
symlink/FIFO, fsync/replace failure, each identity mismatch, mode collision,
v1/v2 backward-read/no migration, invalid context ও unchanged execution/supervision
gates PASS। Ruff/format, plan excerpt drift, docs links/RESUME length ও whitespace PASS।

## সীমা ও next

L4.1 complete; L4 overall incomplete। No actual network/TLS/GPU/image/server run,
install বা billable resource। Root ancestors caller-trusted; same job-এর জন্য
same root প্রয়োজন, অন্য root/job বানানো duplicate prevention নয়। Durability দাবি
local filesystem fsync semantics-এ সীমিত। Existing dirty work preserved; commit নয়।

Next L4.2: live supervision observation contract/storage-এর offline support ও
compatibility, execution enable করার আগে। এটি বর্তমান L4 authorization-এর অংশ;
পরের একক micro-step হিসেবে করা যাবে। Subsequent durable composition ও supervised
acceptance বাকি; actual target/GPU gates blocked। Live dispatch, paid resource,
>2 GB download ও Phase 5.5 onward এই offline কাজের অনুমোদনে অন্তর্ভুক্ত নয়।
