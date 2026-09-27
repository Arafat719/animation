# বিনা খরচে পরের local কাজের scope review

2026-09-27। এই micro-step শুধু scope review; source implementation নয়।

## যাচাই করা বর্তমান অবস্থা

- [Phase 4](plan/phase-4.md)-এর hard attempt limit requirement এখনও প্রাসঙ্গিক।
  Completed 4.4 estimator আবার তৈরি করার প্রয়োজন নেই।
- [Budget source](../animation_studio/providers/gpu_budget.py)-এ
  `estimate_render` caller-এর planned attempts যাচাই করে।
  `submit_budgeted_shot` প্রতিবার নতুন করে preflight করে; পূর্বের dispatch-এর
  durable count নেই। তাই repeated calls/restart-এর across attempt limit enforce হয় না।
- [Tests](../tests/test_gpu_budget.py)-এ estimate boundaries, one-call submit,
  over-budget zero calls ও ambiguous failure propagation আছে; durable reservation নেই।
- [Existing journal](../animation_studio/providers/gpu_journal.py)-এর attempt count
  Pod cleanup retry-এর জন্য; shot inference attempt-এর বিকল্প নয়। এটি বদলানো লাগবে না।
- [Budget checkpoint](gpu-budget-checkpoint.md)-এ এই সীমা আগে থেকেই deferred ছিল।
  এটি নতুন feature requirement বা নতুন phase নয়।

## নির্বাচিত পরের micro-step: local durable shot-attempt reservation

Phase 4 budget guardrail-এর একটি সীমিত follow-up: আলাদা local ledger-এ render/shot
ও caller-supplied attempt key ধরে reservation লিখে রাখা। প্রথম সংস্করণ ledger-only;
provider submit, HTTP transport বা production orchestration-এ wiring এই step-এর বাইরে।
Python standard-library storage ব্যবহার; package/model/GPU/cloud account লাগবে না।

Pass checks:

1. Render-এর validated workload ও budget identity স্থির রেখে planned shot attempts
   অতিক্রম করা reservation reject; over-budget workload ledger-এ admitted হবে না।
2. একই attempt key পুনরায় দিলে একই reservation ফেরে, count বাড়ে না; conflicting
   render/workload/shot reuse reject। এটি আবার provider submit করার অনুমতি নয়।
3. নতুন ledger object/process দিয়ে খুললেও count বজায় থাকে; restart allowance reset নয়।
4. একসঙ্গে শেষ slot reserve করার প্রতিযোগিতায় limit অতিক্রম হয় না; durable write
   failure/corrupt state-এ success ফেরে না।
5. Reservation-এর পর crash হলেও slot consumed থাকে; automatic refund/retry নেই।
   Raw prompt/token/personal asset ledger-এ নয়; identity-এর জন্য digest যথেষ্ট।

এটি actual spend, runtime deadline, exactly-once remote execution বা paid dispatch
protection সম্পূর্ণ করবে না। Reservation ও dispatch integration পরবর্তী পৃথক কাজ।

## সীমা, authorization ও checks

আগের Phase 4 local/mock authorization বহাল; এই follow-up-এ নতুন phase approval
লাগে না। বর্তমান review turn-এ implementation করা হয়নি। Paid GPU, quote/payment
handoff ও CPU model experiment স্থগিত থাকবে; Phase 3/4 real acceptance অসম্পূর্ণ।

Source/test/checkpoint consistency ও relative links যাচাই; plan excerpt drift,
whitespace এবং RESUME length checks PASS। Documentation-only বলে app tests নয়।
Existing owner edits সংরক্ষিত; master requirements অপরিবর্তিত।
