# 5.7c — saved profile to planner adapter

2026-10-11। Owner next-work নির্দেশে GPU-free mapping/identity contract-এর একক
pure adapter ও tests সম্পন্ন। API/project selection wiring এই step-এ নয়।

## Contract

[Adapter](../animation_studio/providers/character_profile_adapter.py)-এর
`to_planner_character(saved, expected_character_id=...)` caller-selected positive
signed-64-bit ID-এর সঙ্গে saved snapshot ID মিলিয়ে canonical `character-<id>` দেয়।
Snapshot name ব্যবহার হয়; legacy metadata name দিয়ে silent substitution নয়।
দুই character-এর নাম একই হলেও ID আলাদা; arbitrary alias/cast lookup নেই।

Existing SavedCharacterProfile/CharacterProfileDraft revalidation, strict schema
version=1 ও nested unchecked-copy validation আছে। Expected ID mismatch-এ rejection;
এই pure function caller-supplied snapshot সত্যিই DB থেকে এসেছে এমন attestation নয়।
Production caller-কে repository থেকে নির্বাচিত profile read করতে হবে।

Structured traits fixed order: face, hair, eyes, outfit, প্রতিটি color, প্রতিটি
accessory। Labels English; supplied Unicode trait values অক্ষত। Negative traits
অপরিবর্তিত list-এ যায়। Description, created_at, storage metadata prompt-এ ঢোকে না।
ফলে সর্বোচ্চ 44 visual traits, প্রতিটি সর্বোচ্চ label+500 characters; PlannerCharacter
limits মানে। তবে সব traits + prompt মিলিয়ে 4000-character shot limit ছাড়াতে পারে:
existing assembler fail করে, truncate নয়। Profile save হওয়া মানেই সব prompt-এ fit নয়।

Existing injection/assembly পুনরায় লেখা হয়নি। Adapter output independent mutable
PlannerCharacter, stored nested frozen snapshot অপরিবর্তিত। Database/provider/network
I/O নেই; no auto-selected cast, overwrite বা retry।

## Checks

[14 new cases](../tests/test_character_profile_adapter.py); existing profile/traits/
assembly-সহ **71 PASS**:

```sh
.venv/bin/python -m pytest -q tests/test_character_profile_adapter.py tests/test_character_profile.py tests/test_character_traits.py tests/test_planner_traits.py
```

Exact Unicode mapping/order, independent output, invalid/mismatched ID, unchecked
schema/nested payload, same-name distinct identity/visible-shot injection, duplicate
assembly rejection, oversized combined prompt failure এবং temp DB save/reopen/map
verified। প্রথম run-এ schema_version=True Literal validation-এ 1 হয়ে যাচ্ছিল;
raw version type check যোগ করে failure closed। No assertion skip।
Prior 5.7b 148 PASS baseline reused; API/schema/migration untouched। Ruff/format,
docs links/RESUME length, plan drift ও whitespace PASS। No install/model/GPU/server/
paid/commit; unrelated dirty কাজ preserved।

## Next ও সীমা

পরের GPU-free micro-step: explicit character IDs গ্রহণ করে saved profiles read →
এই adapter → existing mock planner service দিয়ে preview API composition। Missing
profile/unknown/duplicate IDs reject; old no-cast endpoint compatibility বজায়;
preview persistent project assignment, plan approval বা real generation নয়।
বর্তমান GPU-free নির্দেশে পরবর্তী এই bounded integration করা যাবে; এই turn হয়নি।
Description-to-traits extraction, upload conditioning, real image ও full 5.7 এখনও
অসম্পূর্ণ; saved traits ব্যবহার AI extraction বা visual consistency proof নয়।
