# 5.7h — pure extraction contract ও fixture provider

2026-10-12। Owner next-work নির্দেশে [5.7g design](character-extraction-design.md)-এর
bounded pure contract/mock/tests সম্পন্ন। Existing manual profiles/API/UI/storage untouched।

## ফল

[Domain](../animation_studio/domain/v1/character_extraction.py): strict frozen request,
evidence/candidate/provider identity/report; nested instance revalidation, canonical
request SHA256, exact Unicode code-point span checks, ambiguity/duplicate/order/count
validation, derived missing_required ও fixed REVIEW_REQUIRED status। Report validation
expected request/provider metadata-এর সঙ্গে binding যাচাই করে।

[Provider](../animation_studio/providers/character_extraction.py): replaceable Protocol,
explicit fixture request→candidate mapping, duplicate registration rejection,
FixtureNotFound on unknown request, immutable mapping। Registration-এ evidence/report
validation; report method configured mock identity স্থির রাখে। Fixture candidate নিজে
provider/source metadata দিতে পারে না। No clock/random/network/DB/model/logging।

Request trims name/description once; evidence text normalize করে না। Candidate list
Python API-তে strict tuple; JSON roundtrip supported। Optional empty lists unknown/no
suggestion, absence fact নয়। All-unknown candidate valid review report, approved profile
নয়। Exact spans semantic/category/subject correctness প্রমাণ করে না। Generic report
builder configured metadata বিশ্বাস করে; provenance cryptographic attestation নয়।

## Checks

[41 new tests](../tests/test_character_extraction.py), combined **92 PASS**:

```sh
.venv/bin/python -m pytest -q tests/test_character_extraction.py tests/test_character_profile.py tests/test_character_profile_adapter.py tests/test_character_profiles_persistence.py
```

Bengali/English, emoji/combining code points, request/trait/count limits, bool rejection,
unknown/partial/ambiguous candidates, cross-request hash/context mismatch, source spoof,
wrong/out-of-range spans, duplicate/out-of-order evidence, nested unchecked copies,
immutability, JSON roundtrip, duplicate/unmatched fixtures, no network/SQLite/subprocess
calls covered। First pure suite 79 PASS; added max-boundary/provider strictness case,
final combined 92 PASS। Two existing TestClient deprecation warnings। Unused test import
lint finding removed; final Ruff check/format PASS। Persistence tests used temporary DB
outside sandbox due prior TestClient restriction; no user DB touched।

Docs links, RESUME length, plan drift ও whitespace PASS। No install/GPU/model/server/
commit; unrelated work preserved। Master requirements unchanged।

## সীমা ও next

এই mock arbitrary description থেকে traits extract করে না; explicitly configured fixture
ছাড়া typed failure। Real extraction/image generation/full 5.7 এখনও অসম্পূর্ণ। API/UI,
automatic profile conversion/save, persistence schema migration এই step-এ হয়নি।

Next proposed bounded task: **reviewed extraction save/provenance design review**।
Existing user_provided snapshots backward-compatible রেখে model/fixture-origin draft-এর
review confirmation, persisted provenance/versioning এবং immutable-save conflict policy
নির্ধারণ করবে। Documentation-only; migration/API implementation বা model execution নয়।
Owner-এর পরবর্তী next-work নির্দেশে এই review অনুমোদিত হবে; এই turn-এ শুরু হয়নি।
