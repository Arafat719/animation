# Read-only session/cleanup report scope review

2026-09-27। একই Phase 4 local/mock scope-এর review সম্পন্ন; implementation বাকি।

## বর্তমান evidence

- [Durable session](../animation_studio/providers/gpu_durable_session.py)-এর
  `recover()` owner lease নেয় এবং `_cleanup()` চালায়; শুধু ফল দেখার API নয়।
- [Ledger](../animation_studio/providers/gpu_attempts.py)-এর `lookup()` atomic
  snapshot read করে, কিন্তু শুধু একটি reservation/receipt ফেরত দেয়। Session ও
  cleanup observation-এর আলাদা public read-only reader নেই।
- `_write()` atomic replace ব্যবহার করে; একই descriptor থেকে পুরো ledger পড়ে
  `_State` validation করলে reader আগের বা পরের সম্পূর্ণ snapshot পেতে পারে।
  Concurrent writer থাকলে সবচেয়ে নতুন state পাওয়ার নিশ্চয়তা নেই।
- [আগের checkpoint](gpu-cleanup-observation-checkpoint.md)-এর 183-test evidence
  retained; source পরিবর্তন হয়নি, application tests পুনরায় চালানো হয়নি।

## পরের একক implementation micro-step

`LocalAttemptLedger`-এ render ID দিয়ে typed read-only session report যোগ হবে।
Provider/backend/workload/clock বা session construction দরকার হবে না।

1. Identifier validate করে `O_RDONLY | O_NOFOLLOW` দিয়ে একবার open/read এবং
   existing `_State` validation; initialize/write/recover/cleanup/lock acquisition নয়।
   `.lock` বা `.owner.lock` তৈরি হবে না; active owner থাকলেও snapshot পড়া যাবে।
2. Session না থাকলে `None`: unknown render ও legacy render without session—দুই
   ক্ষেত্রেই অর্থ শুধু durable session record নেই। Missing/corrupt ledger error
   propagate করবে; তা empty বা successful cleanup হিসেবে দেখানো যাবে না।
3. Report-এ persisted closed flag, original started_at/deadline, cleanup attempt
   count এবং optional typed observation থাকবে। Closed flag saved admission intent;
   active owner/liveness নয়। Monotonic times audit-only; remaining time গণনা নয়।
4. Observation থাকলে source `saved`, না থাকলে `unknown`; live_state_verified
   সবসময় false। Missing observation-এ compute/storage unknown; complete success
   অনুমান নয়। Saved absent/none historical cleanup outcome, current billing proof নয়।
5. Existing schema/version/cleanup retry policy বদলাবে না। Read report submit বা
   recovery authorization দেবে না; returned value বদলালেও ledger বদলাবে না।
   CLI/UI/API, reservation aggregation ও live resource inspection এই step-এর বাইরে।

## Implementation pass checks

- Active owner ও released/restarted session-এর snapshot; reader কোনো cleanup,
  provider call, write বা lock create করে না; ledger bytes ও directory entries একই।
- Saved absent-এর none/retained/unknown storage, nonterminal/auth failure এবং
  missing observation/legacy session state সঠিকভাবে historical/unknown থাকে।
- Missing session, missing file, malformed JSON/schema/observation association,
  invalid identifier ও symlink rejection পৃথকভাবে verify হবে।
- Concurrent atomic replacement-এ reader একটি valid whole snapshot পায়; stale
  snapshot বৈধ। Saved deadline থেকে live deadline বা owner status তৈরি হয় না।
- Relevant ledger/durable session/observation regression এবং lint/format checks।

## সীমা ও authorization

এটি existing feature-এর local read-only access design; master requirements বদলায়নি।
Same-phase local implementation authorization বহাল; পরের turn-এ এই একক step।
নতুন phase, paid GPU, install/download, production wiring বা commit অন্তর্ভুক্ত নয়।
এই review-এর blocker নেই; real GPU/runtime/spend acceptance deferred-ই আছে।
