# 5.7a — GPU-free immutable character profile contract

2026-10-11। Owner GPU-free কাজ চালাতে বলেছেন। Existing source gap যাচাই করে একক
pure profile contract/tests সম্পন্ন; full 5.7 নয়।

## Finding ও পরিবর্তন

Existing Character v1 শুধু metadata/opaque reference text রাখে। PlannerCharacter
caller-supplied flat traits prompt-এ inject করে; extraction/persistence দেয় না।
Master CharacterProfile heading-এর face/hair/eyes/outfit/colors/accessories অনুযায়ী
[নতুন contract](../animation_studio/domain/v1/character_profile.py) যোগ হয়েছে।
Existing planner/CharacterRecord/API/schema বদলায়নি; completed injection পুনরায় নয়।

CharacterProfileDraft-এ required name/description এবং structured VisualTraits।
Face/hair/eyes/outfit ও অন্তত একটি color explicit দিতে হয়। Accessories ও negative
traits optional empty tuples। source শুধু user_provided। Description থেকে traits
guess করা হয় না; uploaded path/model/approval metadata এই draft-এ গ্রহণ করে না।
Name 120, description 4000, trait text 500 characters; colors/accessories সর্বোচ্চ
20, negatives সর্বোচ্চ 100। Text strip করে nonempty validation, numeric coercion
reject। Nested frozen models + tuples caller list mutation থেকে independent snapshot
দেয়; unchecked model_copy পুনরায় validation-এ reject। Frozen model নিজে storage-level
immutability নয়; future repository boundary-তেও revalidation দরকার।

## Checks

[নতুন tests](../tests/test_character_profile.py) **25 cases**; existing character traits
ও planner assembly-সহ **57 PASS**, 0.38s:

```sh
.venv/bin/python -m pytest -q tests/test_character_profile.py tests/test_character_traits.py tests/test_planner_traits.py
```

Unicode JSON roundtrip, deep immutability, missing required traits, limits/coercion,
extra/provenance/path rejection, optional defaults ও unchecked nested copy covered।
আগের 78 API/DB PASS baseline reused; API/database untouched বলে পুনরায় run নয়।
Ruff/format, docs links/RESUME length, master/excerpt drift ও whitespace PASS।
No GPU/model/server/network/install/commit; unrelated dirty work preserved।

## পরের একক কাজ

5.7b: existing character ID-এর সঙ্গে explicit profile snapshot database-এ save/read,
পৃথক table/migration ও repository/API। Existing opaque reference_image_paths migrate
বা interpret নয়। Profile overwrite না করে immutable saved snapshot semantics,
unknown character rejection এবং invalid input-এ no write দরকার। Migration-এ legacy
ও সব existing revisions থেকে row preservation; restart/read persistence ও existing
API response compatibility পরীক্ষা হবে। Current GPU-free নির্দেশে এই next কাজ
অনুমোদিত; একক step হিসেবে পরে শুরু হবে। UI/semantic extraction/conditioning নয়।
5.7a-তে persistence হয়নি; 5.7 pass gate এখনও অসম্পূর্ণ। Full description-to-profile
extraction-এর provider scope ভবিষ্যৎ কাজ; user-entered traits-কে AI extraction বলা নয়।
