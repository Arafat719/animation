# Request-bound draft policy — offline implementation ফল

2026-09-21। **অনুমোদিত offline wrapper/fixtures implementation সম্পন্ন।**
[Design](local-planner-contract-run-design-review.md)-এর পরে owner
“ok porer kaj suru kor” বলে কাজ শুরু করতে বলেছেন। Model calls ০।

## কী বদলেছে

Ignored `data/planner-smoke/request-bound-policy-v1/`-এ `policy.py`, fixture generator,
`test_policy.py`, 17 fixtures/manifest, schema/size evidence ও textual reviewer record।

- Deep-copied schema-র শুধু `o.id` ও `b[].e.object` leaf-এ `const=notebook`। Shared
  ID dictionary in-place mutate করা হয়নি; cast IDs/পুরোনো SCHEMA অপরিবর্তিত।
- Strict parsing/shape → REQUEST_OBJECT → field-specific PLACEHOLDER → existing
  semantic candidate checks। Python equality enforce হয়; runtime grammar নির্ভর নয়।
- `s=shared setting`, `m=mood`, `l=lighting` casefold exact-match হলে reject।
  Concrete phrase-এ substring match নয়; raw value normalize/rewrite নয়।
- সফল input আগের assembly-তে যায়; ফল REVIEW_REQUIRED। Narrative mismatch নিজে
  সংশোধন বা accepted label দেওয়া হয় না।

## Verification

**৬ targeted test methods, ১৭ fixture outcomes ও compile PASS।**
Wrong root/event ID, missing keys, তিন placeholder-এর exact/case variants, padding,
precedence, downstream custody error ও unchanged L3 rejection covered।

Tests নিশ্চিত করেছে: schema-তে শুধু দুই intended leaf বদলেছে; raw input/sidecar
অক্ষত; baseline mapping ও deterministic trace একই; rejected input-এ assembly
ডাকা হয় না। L3 raw original model output-এর সঙ্গে হুবহু মেলে। Old contract-এ
REFERENCE `$.b[4].e.object`, নতুন wrapper-এ REQUEST_OBJECT `$.o.id`—নতুন ID
convention-এর কারণে প্রত্যাশিত পার্থক্য; raw repair নয়।

Old validator hash unchanged; আগের ৯ tests/28 fixtures baseline পুনর্ব্যবহার,
সেই suite নতুন করে চালানো হয়নি। Reversed-text fixture automated REVIEW_REQUIRED;
Codex textual review FAIL। Valid/concrete synthetic fixtures review PASS, model
output বা owner approval নয়।

## Overhead ও সীমা

| UTF-8 compact serialization | আগে | এখন |
| --- | --- | --- |
| Schema | 1,947 bytes | 1,985 bytes |
| Request, শুধু schema substitution | 4,222 bytes | 4,260 bytes |

Size-only request-এ পুরোনো prompt আছে; নতুন notebook-ID/concrete-scene নির্দেশসহ
run-ready request নয়। Token cost ও pinned runtime-এর `const` compatibility অমাপা।
768-token/300s cap বাড়ানো হয়নি; tokenizer/model load হয়নি।

Known-placeholder rejection generic scene relevance নয়। Fixed object ID দিয়ে
reference error কমার সম্ভাবনা আছে, কিন্তু action/event agreement বা storytelling
প্রমাণ হয় না। Raw actions model-authored থাকছে; derived বাক্য দিয়ে gap পূরণ নয়।

## Recovery ও next step

Evidence: নতুন directory-তে `checks.json`, `schema.json`, `size-only-request.json`,
`reviewer-evidence.json` ও `fixtures/manifest.json`। পুরোনো validator/fixtures/harness,
raw evidence, production/API/DB/UI/master অপরিবর্তিত; dependency install/commit নয়।
Document links, RESUME <60 lines, scope/status, plan drift ও whitespace PASS।
Full app suite/model run হয়নি; আগের model acceptance FAIL বহাল।

পরবর্তী bounded কাজ: exact ID/concrete-scene prompt, measured overhead ও narrative
rubric-সহ [এক-call model-test proposal](local-planner-request-bound-test-proposal.md)
owner-এর পরবর্তী নির্দেশে সম্পন্ন; execution অনুমোদন pending। Offline PASS থেকে automatic
run বা 3.10 নয়। আরও narrative failure হলে design অনুযায়ী owner suitability review,
অন্তহীন prompt/rejection-policy loop নয়।
