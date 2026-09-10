# পরিকল্পনা সংশোধনের audit — ২০২৬-০৯-০৯

এই কাজের scope শুধু plan/documentation correction। কোনো application code,
test code, dependency, configuration, runtime database বা media বদলানো হয়নি।
কোনো implementation step, install, model download বা GPU কাজ চালানো হয়নি।

## সংশোধন

1. Master plan-এর দুইটি hardcoded “এখন 0.1 করো” নির্দেশ সরিয়ে evidence অনুযায়ী
   resume rule বসানো হয়েছে। Phase 0 checklist ঐতিহাসিক reference হিসেবে আছে;
   missing পুরোনো inventory report থেকে নতুন completion দাবি বা restart নয়।
2. Master plan V2.1 এবং current ledger-এ সম্পন্ন/আংশিক/বাকি কাজ, test evidence-এর
   তারিখ, এবং source বনাম historical checkpoint-এর ব্যবহার স্পষ্ট করা হয়েছে।
3. 1.11-এর পুরোনো PASS কেবল implemented slice-এর regression ফল হিসেবে রাখা হয়েছে।
   full Phase 1 এখনো PARTIAL; completed settings/pages/provider/runner/dispatch/web
   integration আবার বানানোর নির্দেশ নেই।
4. পুরোনো step IDs রেখে অবশিষ্ট Phase 1 কাজকে 1.12–1.17 করা হয়েছে: artifact API,
   preview UI, logging, formatter, startup, পূর্ণ phase gate। এটি ভবিষ্যৎ queue,
   এই plan-only অনুরোধের implementation authorization নয়।
5. Section 6-এর row এবং Section 7-এর বিস্তারিত requirements দুটোই phase gate-এ
   প্রয়োজন। Canonical contract-এর Phase 1 typed/schema baseline এবং পরবর্তী
   feature fields আলাদা করা হয়েছে; baseline gaps শুধু পরে করার mapping দিয়ে
   complete বলা যাবে না। StoryPlan 3.1-এর কাজ, minimal shots table তার সমান নয়।
6. Phase 2 helper থাকাকে পুরো composer সম্পন্ন বলা বন্ধ করা হয়েছে। Fixture
   provenance, normalization/audio checks, concat paths/list-file handling,
   mixing/fades, subtitle/manifest এবং media/disk UI errors-এর ঘাটতি রাখা হয়েছে।
7. Restart persistence বনাম automatic crash recovery, metadata voice বনাম TTS,
   fixed sample বনাম 30–60s prompt-specific output আলাদা করে লেখা হয়েছে।
8. Report/permission নির্দেশে আগে দেওয়া authorization-এর পুনরাবৃত্তি বন্ধ করা
   হয়েছে; phase change/paid action-এর বিদ্যমান approval gates রাখা হয়েছে।
   Plan-only কাজের জন্য অপ্রয়োজনীয় application test/install-এর নির্দেশ নেই।
9. অনুমোদিত mock/fixture tests-কে error লুকানোর fake success-এর সঙ্গে গুলিয়ে
   ফেলা, Phase 3-এর “real AI নয়” অথচ real planner row থাকা, এবং 13 GB model-এর
   উপস্থিতি ধরে নেওয়া ঠিক করা হয়েছে। Model preflight estimates ও benchmark-এর
   পর measured results আলাদা; exact model/license/hardware পুনরায় verify করার
   প্রয়োজন আছে, এই audit তা করেনি।
10. Phase 9-এর দুই-shot/10–15s checks isolated smoke-test scope; production
    V1 Project duration 30–60s বদলায়নি। 5.5 existing artifact UI পুনর্ব্যবহার করবে।
11. Starter plan-এর 4-test ফল ও real-pipeline-first order ঐতিহাসিক হিসেবে
    চিহ্নিত; active master/ledger links যোগ হয়েছে। Historical checkpoints-এর
    মূল বিবরণ পুনর্লিখন করা হয়নি। পুরোনো web README-এর demo নির্দেশ current
    ledger দ্বারা superseded বলে চিহ্নিত; operational README refresh বাকি।

## Evidence ও যাচাই

Source, test definitions এবং existing checkpoint দুটো পৃথক read-only review-এ
মিলিয়ে দেখা হয়েছে। বিশেষভাবে dispatcher log-এ চারটি context field ইতিমধ্যে আছে
এবং shots table-এ minimal status column আছে—এগুলো missing বলে লেখা হয়নি।

Documentation validation-এ local links, Markdown table/fence structure, original
step IDs অক্ষত থাকা, fixed V1 product decisions অপরিবর্তিত থাকা, 0.1 restart prompt
না থাকা, এবং master/ledger-এর 1.12–1.17 queue মিলিয়ে দেখা হয়েছে। Before/after hash
comparison দিয়ে নিশ্চিত করা হয়েছে পরিবর্তন শুধু এই চারটি planning document-এ:

- `AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md`
- `# Project plan: Animation Studio Starter.prompt.md`
- `docs/current-build-status.md`
- `docs/plan-reconciliation-2026-09-09.md` (এই নতুন report)

Application tests এই audit-এ চালানো হয়নি। “১৭২ পাস” হলো পূর্ববর্তী
[web fixture checkpoint](web-fixture-checkpoint.md)-এর ফল; নতুন test result নয়।
No phase completion, model readiness, active runtime DB revision বা remote CI
success দাবি করা হয়নি।
