# Supplied cast ID/name — bounded policy ও test specification

2026-09-23। Owner পরের কাজ করতে বলেছেন; policy ও tests নির্ধারণ সম্পন্ন।
ভিত্তি: [fidelity review](planner-request-fidelity-review.md),
[fresh-plan checkpoint](planner-fresh-plan-checkpoint.md),
[PlannerRequest/injector](../animation_studio/providers/planner.py) ও
[repair runner](../animation_studio/providers/planner_repair.py)। Implementation হয়নি।

## প্রস্তাবিত internal runner policy

Caller-এর supplied characters-কে required cast subset হিসেবে ধরবে। প্রত্যেক supplied
ID output cast-এ থাকতে হবে এবং একই ID-এর name validated request-এর name-এর সমান
হতে হবে। Extra output characters এবং ভিন্ন cast order গ্রহণযোগ্য; duplicate IDs
existing schema-তেই reject হয়। Supplied cast খালি হলে নতুন restriction নেই।

Comparison existing request/output validation-এর whitespace normalization-এর পরে;
case folding, transliteration, fuzzy matching বা Unicode normalization যোগ নয়।
একই name-এর অন্য ID দিয়ে missing supplied ID পূরণ হবে না। চরিত্র cast-এ থাকলেই
এই policy satisfied; প্রতি shot-এ visible থাকা বাধ্যতামূলক নয়। Offscreen dialogue
ও unused supplied cast গ্রহণযোগ্য, existing reference validation বহাল।

এটি proposed runner-local request-fidelity contract; shared StoryPlan schema-তে
নতুন cast restriction নয়। Existing injector supplied IDs subset চায়; এই design
তা বজায় রেখে caller name preservation যোগ করার প্রস্তাব। Product/master requirement
পরিবর্তন করা হয়নি; traits/semantic acceptance-এর পূর্ণ সংজ্ঞা দাবি নয়।

## Diagnostics, precedence ও repair

Schema → duration → fresh lifecycle → supplied cast। আগের layer ব্যর্থ হলে আগের
issues-ই ফেরত যাবে। Cast issues request.characters order-এ; প্রতিটি requested ID-তে
missing অথবা name mismatch, দুটো একসঙ্গে নয়।

| Condition | Code | Path ও message |
| --- | --- | --- |
| Supplied ID নেই | CAST_MISSING | ('characters',); message-এ missing expected ID—অস্তিত্বহীন output index নয় |
| ID আছে, name বদলেছে | CAST_NAME_MISMATCH | ('characters', output_index, 'name'); message-এ expected ID/name |

Raw output edit/rename/reorder নয়। Existing max_retries 0–2/default 0 budget-এ
feedback; প্রতিটি repaired output সব checks পেরোবে। Exhaustion-এ typed failure;
success REVIEW_REQUIRED। Caller snapshot ও provider-exception semantics অপরিবর্তিত।
Trait injection, API integration, public schema, persistence ও model execution নয়।

## Implementation-এর প্রয়োজনীয় tests

1. Valid supplied ID/name; reordered cast; extra cast; empty supplied cast—PASS।
2. Missing one/multiple ID; একই name কিন্তু ভিন্ন ID—CAST_MISSING; request-order
   feedback এবং message-এ expected ID।
3. Matching ID কিন্তু changed name, Bengali name ও case-only difference—mismatch;
   surrounding whitespace normalized হলে match। Reordered output-এ সঠিক output path।
4. Mixed missing/name errors-এ deterministic order; schema duplicate ID failure,
   duration mismatch ও nonfresh lifecycle-এর precedence অক্ষত।
5. Invalid cast → fake repaired cast success; raw unchanged; always-invalid output-এ
   0/1/2 budget exhaustion; repaired output নতুন cast সমস্যা করলে আবার reject।
6. Supplied character invisible/offscreen/unused হলেও cast retained থাকলে PASS;
   existing schema-invalid reference গ্রহণ নয়।
7. Existing nested mutation-isolation test-এর valid() default mock cast requested
   hero-কে বাদ দেয়। নতুন guard-এ সেই fixture expected request cast দিয়ে বানাতে হবে;
   input-preservation assertions অক্ষত রাখবে, test skip বা guard bypass নয়।

Files: `animation_studio/providers/planner_repair.py`, `tests/test_planner_repair.py`।
Targeted repair/mock-planner/StoryPlan এবং character-traits suites চালাবে।
Baseline: পূর্ববর্তী ৮৪ targeted tests PASS; এই docs-only step-এ rerun হয়নি।

## Outcome ও next step

Policy/test specification সম্পন্ন; blocker নেই, নতুন chat প্রয়োজন নেই।
পরবর্তী একমাত্র bounded কাজ উপরোক্ত supplied cast guard ও tests implement করা;
Owner-এর পরবর্তী নির্দেশে সম্পন্ন; [checkpoint](planner-cast-checkpoint.md)।
Traits prompt ownership/duplication ও narrative review বাকি থাকবে।
CPU-model experiment queue বন্ধ; download/run/adapter অনুমোদিত নয়।
Docs links/RESUME/status/scope/plan drift/whitespace PASS; source/master/assets
অপরিবর্তিত; app tests বা commit হয়নি।
