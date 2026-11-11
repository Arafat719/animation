# GPU-free character migration regression fix

2026-10-11। Owner GPU-free কাজ চালাতে বলেছেন; 5.6 checkpoint-এর নির্ধারিত একক
stale migration-test fix সম্পন্ন। App/database/schema পরিবর্তন হয়নি।

## কারণ ও পরিবর্তন

[Character contract test](../tests/test_character_contract.py) migration শেষে পুরোনো
`0003_fixture_jobs` আশা করছিল। [init_db](../animation_studio/persistence/db.py)
`head` পর্যন্ত upgrade করে; বর্তমান
[migration](../animation_studio/persistence/migrations/versions/0004_plan_approval.py)
`0004_plan_approval`। Existing test_db-ও এই revision যাচাই করে। আগের turn-এ নতুন
upload route ছাড়া baseline-তেও চারটি failure পুনরুৎপাদিত হয়েছে; সেই evidence reused।

Expected revision বর্তমান explicit head-এর সঙ্গে মিলেছে। Legacy/0001/0002/0003
upgrade cases অক্ষত রেখে current 0004 থেকে repeated-init case যোগ হয়েছে।
Exact stored rows, column/record contract, nullable/opaque reference text, repeated
API list reads এবং final database preservation assertions সব চালানো হয়েছে।
Test skip/assertion removal বা application migration downgrade হয়নি।

## Checks

**78 PASS**, 5.42 seconds:

```sh
timeout 120s .venv/bin/python -m pytest -q tests/test_reference_images.py tests/test_characters_api.py tests/test_character_contract.py tests/test_projects_api.py tests/test_null_compatibility.py tests/test_health.py tests/test_db.py
```

আগের combined suite-এর চার failure closed; current-head case ও DB regressions-সহ
সম্পূর্ণ নির্বাচিত suite green। দুটি existing TestClient/httpx/AnyIO deprecation
warning আছে; dependency upgrade এই fix-এর scope নয়। আগের sandbox event-loop hang
প্রমাণের ভিত্তিতে local tests outside sandbox চালানো হয়েছে; server/network/GPU নয়।
Ruff/format, docs links/RESUME length, plan drift ও whitespace PASS।

## Next ও সীমা

পরবর্তী GPU-free candidate: 5.7 character profile/traits persistence-এর existing
source/contract gap যাচাই করে একক implementation scope নির্ধারণ। Owner-এর GPU-free
কাজ চালানোর নির্দেশ বহাল; এই fix-এ 5.7 implementation হয়নি। Existing 5.6 scope-এর
বাইরের feature হলে master/excerpts-এ নির্বাচিত scope sync করতে হবে।
5.4 real image/5.5 real artifact integration hardware evidence ছাড়া সম্পন্ন নয়।
নতুন phase/paid/download/স্থগিত CPU model experiment শুরু হয়নি। Unrelated dirty
files preserved; commit নয়।
