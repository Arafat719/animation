# Phase 5.6 — GPU-free reference upload validation

2026-10-11। Owner আপাতত GPU ছাড়া কাজ চালাতে বলেছেন; একই Phase 5-এর independent
reference upload validation micro-step নির্বাচন ও implementation সম্পন্ন।
Master scoped exception হালনাগাদ, generated Phase 5 excerpt sync করা হয়েছে।
5.4 real image/5.5 integration deferred; তাদের acceptance সম্পন্ন নয়।

## API ও policy

`POST /reference-images/validate` raw PNG/JPEG body গ্রহণ করে। Headers:
`Content-Type: image/png` অথবা `image/jpeg`, `X-Filename: reference.png`।
Multipart/form-data নয়; নতুন dependency লাগেনি। Response-এ filename/media type,
size_bytes, width/height, SHA256 এবং `stored: false` থাকে। কোনো file/database
write, character attachment, provider call, GPU বা image generation হয় না।

- Maximum 8 MiB; Content-Length থাকলে precheck, না থাকলেও প্রতি chunk-এ limit।
  Declared/actual length mismatch reject; upload read timeout 15 seconds।
- Filename 1–120 ASCII characters; প্রথম অক্ষর alphanumeric, পরবর্তী অক্ষরে
  alphanumeric/space/dot/underscore/hyphen। Slash/backslash, `..`, encoded path ও
  hidden basename reject। Filename কখনো filesystem path হিসেবে ব্যবহার হয় না।
- MIME, extension ও detected format match; PNG/JPEG শুধু; APNG/animated input reject।
- প্রতি dimension 1–4096 inclusive; Pillow verify এবং reopen/full pixel decode।
  Empty, truncated বা corrupt input reject; image content/error body echo হয় না।
- Wrong media/encoding 415; oversized bytes 413; malformed image/name/dimensions 422;
  malformed/mismatched Content-Length ও disconnect 400; upload timeout 408।

[Validator](../animation_studio/media/reference_image.py),
[API route](../apps/api/reference_images.py), [registration](../apps/api/main.py),
[tests](../tests/test_reference_images.py)। Decode thread-এ চলে; upload deadline
native decode-এর hard CPU deadline নয়। Concurrent-request aggregate RAM cap বা
public multi-user upload service এই local prototype step-এর scope নয়।
Metadata strip/re-encode, persistence/retention, reference conditioning ও upload UI
এখানে নেই। Existing character schema/reference_image_paths অপরিবর্তিত।

## Checks ও known regression

নতুন suite **28 PASS**: valid PNG/JPEG metadata/no write, unsafe names, wrong MIME/
extension/content, truncated PNG/JPEG, dimensions equality/excess, animation, byte
limit equality/excess, missing/false Content-Length stream limit, valid chunked
upload, timeout ও disconnect। Existing API/schema regression-সহ **66 PASS, 4 FAIL**:

```sh
.venv/bin/python -m pytest -q tests/test_reference_images.py tests/test_characters_api.py tests/test_character_contract.py tests/test_projects_api.py tests/test_null_compatibility.py tests/test_health.py
```

চারটি failure `test_character_migrations_preserve_all_fields_and_list_reads`-এ:
expected `0003_fixture_jobs`, actual `0004_plan_approval`। Test/database source এই
step-এ বদলায়নি। নতুন router import/registration সাময়িক সরিয়ে baseline চালিয়ে একই
চার failure পুনরুৎপাদিত: **28 PASS, 4 FAIL**; finally-তে source ফিরেছে। এটি নতুন
upload feature regression নয়; combined suite সম্পূর্ণ PASS দাবি করা হচ্ছে না।
Next একক GPU-free fix: character migration test-এর stale expected revision
সংশোধন, current head থেকে backward preservation assertions সম্পূর্ণ চালানো।
বর্তমান GPU-free কাজের নির্দেশে এই bug fix scope বহাল; নতুন phase নয়।

প্রথম sandbox runs existing TestClient baseline-সহ thread/event-loop wait-এ আটকে
ছিল; diagnostic timeout trace নিয়ে pending runs বন্ধ করা হয়েছে। Local API tests
sandbox-এর বাইরে চলে; network server/model launch হয়নি। Ruff/format, plan drift,
docs links, RESUME length ও whitespace PASS। Dependency upgrades/commit হয়নি।

## Migration regression update — 2026-10-11

[পৃথক fix](character-migration-test-checkpoint.md) সম্পন্ন। Stale expected head
সংশোধন ও current-head re-init case যোগ করে combined API/DB suite **78 PASS**।
উপরের 4 FAIL baseline historical; বর্তমান নির্বাচিত regression suite green।
