# Offline semantic contract — implementation ফল

2026-09-21। **অনুমোদিত offline validator/fixtures implementation সম্পন্ন।**
[Proposal](local-planner-semantic-contract-proposal.md)-এর পরে owner
“ok porer kaj suru koro” এবং “kaj shesh koro” বলেছেন। এই কাজের model calls ০।

## কী তৈরি হয়েছে

Ignored `data/planner-smoke/semantic-contract-v1/`-এ standalone `contract.py`,
`build_fixtures.py`, `test_contract.py`, 27 fixture files ও manifest।
Validator strict shape, unique identity, role/reference, case A owner/initial holder,
event endpoints, ordered custody, onscreen/offscreen visibility এবং courier→owner
return/final holder যাচাই করে। Error-এ stable code ও field/shot path থাকে।

Checks pass হলে শুধু `REVIEW_REQUIRED`; candidate StoryPlan ও original semantic
sidecar আলাদা। V2-এর existing deterministic assembly import করে ব্যবহার করা হয়েছে;
সেই file পরিবর্তন হয়নি। Raw actions অক্ষত; role/object/event fields production
StoryPlan-এ ঢোকানো হয়নি। ছয়টি 5s shot, pending/default execution fields বজায় থাকে।

## Checks ও evidence

- **৬ targeted unittest methods PASS**, compile PASS; 27 manifest cases-এর expected
  outcome মিলে গেছে। Manifest variants proposal-এর ১২ negative family প্রসারিত করেছে।
- Positive mention/offscreen cases, role/reference/case/custody/visibility rejection,
  return/final-holder rejection, তিন review-only এবং দুই unchanged legacy case covered।
- Generic malformed/duplicate/nonfinite JSON, boolean/numeric coercion, blank/length,
  unknown field, count/enum checks; stable error code/path ও layer priority যাচাই।
- Deterministic custody trace `C,C,C,C,O,O`, owner O অপরিবর্তিত; input immutability,
  candidate mapping, repeat equality ও returned evidence-এর independence PASS।
- R1/R2 narrative mismatch ও R3 ambiguity স্বয়ংক্রিয়ভাবে semantic PASS হয় না:
  automated ফল REVIEW_REQUIRED; Codex textual fixture review যথাক্রমে FAIL,
  FAIL, UNRESOLVED। P1–P3 fixture review PASS, owner human approval নয়।
- L1/L2 original bytes অপরিবর্তিত; নতুন contract-এ SHAPE reject। পুরোনো semantic
  FAIL evidence pass-এ রূপান্তর হয়নি।

Evidence: `checks.json`, `schema.json`, `baseline-candidate.json`,
`reviewer-evidence.json`, `size-only-request.json`, `fixtures/manifest.json`।
Synthetic fixtures-এর origin manifest-এ স্পষ্ট; model-produced success নয়।

## Overhead ও সীমা

একই UTF-8 compact JSON serialization:

| মাপ | Compact v2 | Semantic contract |
| --- | --- | --- |
| Schema | 930 bytes | 1,947 bytes |
| Request | 2,485 bytes | 3,506 bytes, শুধু schema/name substitution |
| Synthetic baseline draft | — | 1,427 bytes |

3,506-byte example-এ পুরোনো V2 prompt রাখা হয়েছে **শুধু size comparison-এর জন্য**;
এটি নতুন contract-এর run-ready request নয়। উপযুক্ত নতুন prompt-এর overhead ও token
cost অমাপা; tokenizer/model load হয়নি। 768-token/300s budget বাড়ানো হয়নি।

Validator declared facts-এর consistency যাচাই করে; গল্পের সত্যতা, action text বনাম
metadata বা arbitrary semantic quality স্বয়ংক্রিয়ভাবে বোঝে না। Single notebook,
এক event/shot ও ছয় event kinds-এর সীমা বহাল। Offline fixture PASS real planner gate নয়।

## Recovery ও next step

Production source/API/DB/UI/master এবং পুরোনো harness/raw evidence অপরিবর্তিত।
নতুন dependency, server, download, GPU, repair বা 3.10 adapter হয়নি; commit হয়নি।
Document links, RESUME <60 lines, status/scope, plan drift ও whitespace checks PASS।
App tests পুনরায় চালানো হয়নি; scoped offline tests-ই প্রযোজ্য।

পরের bounded কাজ: এই contract-এর overhead ও সীমা বিবেচনায় একটি reviewable isolated
[model-test proposal](local-planner-semantic-model-test-proposal.md) owner-এর পরবর্তী
নির্দেশে সম্পন্ন। তার execution অনুমোদন pending; model run নিজে থেকে নয়। আগের compact v1/v2
semantic FAIL বহাল; Phase 3 real-adapter gate ও Bengali/বড় duration tests বাকি।
