# Mock lifecycle deadline/cleanup checkpoint

2026-09-26। অনুমোদিত 4.7 local prerequisite micro-step সম্পন্ন।

- [Controller](../animation_studio/providers/gpu_lifecycle.py) শুধু exact MockLifecycle
  backend গ্রহণ করে; কোনো RunPod/cloud mutation যুক্ত নয়। Already-created এক
  disposable resource-এর ID capture; অন্য ID-তে mutation reject।
- Monotonic caller tick-এ exact deadline/finished/failed হলে session closed এবং
  inspect → stop → terminate → inspect। Stop ব্যর্থ হলেও terminate fallback।
- Cleanup failure session reopen করে না; পরের tick reconciliation করতে পারে।
  Observed absent resource আবার terminate নয়। Raw backend error echo নয়।
- Compute absent এবং storage none দুটো হলেই cleanup complete। Retained/unknown
  storage আলাদা দেখায়; storage delete নেই। Inspection failure unknown; false PASS নয়।
- [Tests](../tests/test_gpu_lifecycle.py): exact boundary, early completion/failure,
  repeated cleanup, stop/terminate/inspect failures, resource scope, invalid clocks।
- Lifecycle + budget + GPU tests **99 PASS**; ruff format/lint ও docs checks PASS।
- এটি cooperative mock control, autonomous watchdog/hard billing cutoff নয়।
  Process crash/restart persistence, live adapter/polling ও independent shutdown
  fallback বাকি। Existing tested worker image/source অপরিবর্তিত; rebuild প্রয়োজন নেই।
- No install/download/publish/paid call/commit। GHCR target namespace `arafat719`; registry publication হয়নি।
- পরের micro-step: concrete GHCR publication handoff (exact tested artifact,
  private access/credentials ও digest verification plan); publish explicit scope
  ছাড়া নয়। 4.7 final preview/live lifecycle readiness এখনও অসম্পূর্ণ।
