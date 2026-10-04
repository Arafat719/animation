# Phase 5.4 — durable preflight integration

2026-10-03। Owner next-work নির্দেশে একটি offline micro-step সম্পন্ন।
`DurableComfyExecutor.execute`-এ inventory preflight এখন বাধ্যতামূলক।

## Ordering ও behavior

1. Request/graph validation, pre-cancel check এবং exclusive journal lock।
2. Existing journal থাকলে fail; কোনো inventory read বা submit নয়।
3. Lock ধরে six-node-class inventory preflight; এরপর cancellation আবার check।
4. Preflight PASS হলে intent atomic write/fsync, তারপর একবার submit;
   receipt persist, polling/download ও existing verified image path।

Preflight failure/cancellation-এ intent নেই, POST নেই; persistent lock file থাকতে
পারে। সমস্যা ঠিক হলে caller explicit retry করতে পারেন। Automatic retry নেই।
Intent লেখা হয়ে গেলে ambiguity-এর আগের fail-closed rule বহাল। Preflight চলার
সময় দ্বিতীয় caller lock নিতে বা submit করতে পারে না।

Recovery অপরিবর্তিত: journal/graph/receipt validate করে history/download GET-only;
node inventory আবার query বা submit/cancel করে না। Model alias পরে unavailable
হলেও আগের saved output উদ্ধার করা সম্ভব, যদি history/output এখনও থাকে।

Preflight ও execution-এর cooperative deadline আলাদা; combined hard wall-clock
limit নয়। Inventory-read ও submit atomic নয়; remote state বদলাতে পারে। Alias
বা port compatibility GPU/weights identity proof নয়। Raw HTTP executor এখনও
low-level ungated; durable provider path-এ আর opt-in flag প্রয়োজন নেই।

## Checks

219 baseline PASS; final **226 PASS**, seven relevant suites। Seven added cases:
missing inventory/HTTP/timeout/cancel failure → no intent/POST → explicit retry,
preflight-এর মধ্যে competing caller exclusion, inventory-independent recovery,
preflight শেষে intent-এর আগে cancellation। Existing journal persistence order,
write/fsync/crash tests নতুন six read ordering অনুযায়ী updated।

Synthetic `tests/fixtures/comfy_object_info.json` shared mock server-এ যোগ, যাতে
durable provider/shared contract ও actual subprocess restart tests পূর্ণ gated
path চালায়। Fresh-process verified recovery এখনও one submit; live sockets নয়।
Ruff lint/format, plan drift, docs/whitespace checks PASS। Schema পরিবর্তন,
install/download/GPU generation/API/UI change হয়নি।

## Next / limitations

এই gate কেবল existing mock-only path-এ verified; full Phase 5.4 real image gate
অসম্পূর্ণ। Next authorized offline micro-step: Comfy image path-এর readiness/gap
review—completed offline evidence ও বাকি GPU/runtime/live integration gates-এর
সুনির্দিষ্ট তালিকা। নতুন phase বা live dispatch নিজে থেকে শুরু নয়।
