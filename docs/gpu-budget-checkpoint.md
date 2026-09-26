# Phase 4.4 — budget config ও dry-run estimator

2026-09-25। অনুমোদিত micro-step 4.4 সম্পন্ন।

- [gpu_budget.py](../animation_studio/providers/gpu_budget.py): BudgetConfig-এ
  explicit USD limits: max_gpu_hourly_price, max_gpu_minutes_per_job,
  max_attempts_per_shot, max_estimated_cost_per_render। Implicit allowance নেই।
- RenderWorkload: caller-supplied hourly rate, startup minutes ও unique shot entries;
  প্রতিটি entry-তে GPUJobRequest, GPU minutes per attempt এবং total attempts।
  Attempts-এর মধ্যে initial run অন্তর্ভুক্ত; HTTP retry নতুন inference attempt নয়।
- Formula: reserved minutes = startup + sum(minutes per attempt × attempts)।
  Compute cost = reserved minutes × hourly rate / 60; USD 0.000001-এ upward rounding।
  Decimal arithmetic, finite/bounded inputs; zero allowance বৈধ, invalid input reject।
- estimate_render pure dry-run: provider/network/DB call নেই। সব violated limit
  ফেরে; exact limit অনুমোদিত। Minutes cap পুরো render job-এর reserved GPU minutes।
- submit_budgeted_shot পুরো render revalidate/estimate করে তারপর selected shot-এর
  initial attempt একবার submit করে। Over-budget → BudgetExceeded এবং zero calls।
  Selected request workload থেকেই নেওয়া; unknown shot reject। Provider failure
  propagate করে; gate নিজে retry করে না। Existing HTTP retry/idempotency অক্ষত।

## Checks

- [Budget tests](../tests/test_gpu_budget.py) + existing GPU contract: **79 PASS**।
- চার limit আলাদা/একসঙ্গে, exact boundary, attempts/startup arithmetic, upward
  rounding, invalid/nonfinite inputs, duplicate shot, provider failure এবং HTTP
  transport-এর আগেই rejection verified। Under-budget HTTP submission একবার হয়।
- Ruff format/lint, excerpt drift, document links/RESUME length/whitespace PASS।
- Existing Phase 4.3 112-test evidence retained; HTTP/server source অপরিবর্তিত।
  Full app/media suite বা real GPU check নয়; dependencies/DB/UI/public schema
  অপরিবর্তিত। Unrelated work অক্ষত; commit/download/paid action নয়।

## সীমা ও পরের ধাপ

এটি caller-provided estimates-এর compute-only preflight। Storage/egress/tax অন্তর্ভুক্ত
নয়; per-attempt minutes-এ প্রয়োজনীয় সব stage caller-কে ধরতে হবে। Live price lookup,
runtime shutdown, persistent spend/attempt ledger বা repeated dispatch accounting
নেই। Existing low-level provider.submit সরাসরি এই gate bypass করতে পারে; production
paid dispatch যুক্ত করার আগে orchestration-এ gate ও runtime accounting বাধ্যতামূলক।
Budget pass owner paid-resource approval নয়। কোনো production dispatch path যোগ হয়নি।

পরের অনুমোদিত micro-step **4.5 secret loading ও log redaction**। Phase 3 real planner
acceptance ও Phase 4-এর worker/artifact/resource lifecycle gates বহাল।
