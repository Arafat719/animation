# 5.7l — version-aware profile read API

2026-10-12। Owner-এর পরের কাজের নির্দেশে [5.7k](character-reviewed-storage-checkpoint.md)
পরবর্তী bounded read API/legacy guard সম্পন্ন।

## Outcome ও files

[API module](../apps/api/character_profiles.py)-এ GET
`/v2/characters/{character_id}/profile` authoritative repository থেকে saved v1 অথবা v2
ফেরত দেয়। Response schema_version-discriminated union; existing character-এর profile
না থাকলে 200 null, character না থাকলে 404, invalid ID-তে DB open-এর আগেই 422।
V2 response-এ full values/origins/provenance, original REVIEW_REQUIRED report,
confirmed decision, is_mock marker ও server timestamps বজায় থাকে।

পুরোনো GET `/characters/{character_id}/profile` v2 profile-এ 409
`Unsupported character profile version` দেয়। Existing v1 GET/POST shape ও empty response
অক্ষত; old POST v2-এর পাশে manual profile save করতে চাইলে আগের conflict guard-এ 409।
নতুন route শুধু GET; POST/PUT/PATCH/DELETE 405। Corrupt manual/reviewed provenance,
unsupported stored schema বা duplicate rows হলে new GET sanitized 500; null/fallback নয়।

Callable discriminator integer version দিয়ে variant বেছে নেয়; OpenAPI-তে explicit
propertyName/mapping প্রকাশিত। Storage model-এর strict before-validator অপরিবর্তিত।
Initial field discriminator Pydantic schema generation-এ rejected হয়েছিল; model-level
validator experiment-এ nested strict tuple JSON round-trip failure ধরা পড়ে। Minimal
reproduction দিয়ে callable discriminator যাচাই করে storage change ফিরিয়ে নেওয়া হয়েছে;
final implementation-এ দুই regression closed, validation শিথিল করা হয়নি।

## Checks

[New API tests](../tests/test_character_profile_read_api.py): **30 cases**;
combined suite **123 PASS**, দুইটি existing TestClient deprecation warning।
Prior 5.7k 229 PASS baseline reused। Known sandbox TestClient limitation অনুযায়ী
API suite outside sandbox, শুধু temporary SQLite databases ব্যবহার করেছে।

```sh
timeout 120s .venv/bin/python -m pytest -q tests/test_character_profile_read_api.py tests/test_character_profiles_persistence.py tests/test_reviewed_character_profiles_persistence.py tests/test_character_contract.py tests/test_character_preview_api.py
```

V1 response equality, reopened v2 full round-trip, repeated GET/failed POST-এর পর DB
snapshot unchanged, 404/422/409/500/405, corruption sanitization, strict raw version tags,
OpenAPI discriminator ও existing migration/manual/preview compatibility verified।
Ruff/format on changed code, plan excerpt drift, documentation links/RESUME length ও
whitespace PASS। No install/model/GPU/server/commit; unrelated changes preserved।

## Limits ও next

Reviewed-save API নেই; trusted server-owned draft lookup/lifetime অসম্পূর্ণ। UI ও planner
adapter/preview এখনও v1-only; preview v2-কে fail-closed করে। Read API-র mock marker
সংরক্ষণ UI consumer support-এর বিকল্প নয়। Full 5.7 ও real extraction অসম্পূর্ণ।

Next proposed **5.7m pure version-aware planner profile adapter/tests**: v1 mapping বজায়
রেখে saved v2-এর final structured values থেকে planner traits তৈরি; identity/version ও
unchecked-copy validation, raw description/provenance prompt-এ না যাওয়া যাচাই। API
preview/UI wiring, draft store ও reviewed writer এই next bounded scope-এর বাইরে। Owner-এর
পরবর্তী next-work নির্দেশে শুধু এই implementation শুরু করা যাবে; এই turn-এ শুরু হয়নি।
