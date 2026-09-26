# Micro-step 1.14 — structured pipeline logging

Implementation/checks: 2026-09-10. Documentation and resume ledger completed:
2026-09-11. Step 1.14 PASS; full Phase 1 remains PARTIAL.

Extended the existing worker exception logging into structured lifecycle events.
The application now configures a scoped JSON stderr handler, and queue admission,
runner claim/progress/finalization, cancellation, outcome reuse and infrastructure
failures carry job/project/shot/step context. Successful transition events follow
the database commit. API cancellation is recorded even when no worker is present;
it is distinct from a committed cancellation outcome.

Allowlisted fields replace raw exception messages/tracebacks. Invalid provider
values remain rejected but no longer leak through Pydantic serialization warnings.
Default sink errors do not dump raw exceptions; logging failures do not convert
a persisted successful job into failure. No dependency or schema change.

Implementation and tests:

- `animation_studio/observability.py` — validated events, JSON formatter, safe sink,
  scoped configuration and error classification.
- `animation_studio/persistence/runner_store.py` — wrap the existing transaction
  boundaries to observe commits/rollbacks and emit state/progress events.
- `animation_studio/pipeline/dispatcher.py` — queued/submission/worker events,
  preserving admission and cancellation behavior.
- `animation_studio/pipeline/fake_runner.py` — suppress raw serialization warnings
  while retaining validation of provider progress/results.
- `apps/api/main.py` — lifespan configuration through graceful worker shutdown;
  log only cancellation updates that actually changed a row.
- `tests/test_pipeline_logging.py` — 24 new cases; existing dispatcher log assertions
  now require safe error codes and prohibit raw exception text.

Completed validation before the interruption:

- Existing focused runner/dispatch baseline: **43 passed**.
- Final full backend suite: **230 passed**, two existing dependency deprecation
  warnings. The synthetic private-input serialization warning found during testing
  was fixed and is explicitly checked to remain absent.
- New coverage includes real-provider lifecycle, persisted progress, no early
  completion, provider/input errors, event/DB cancellation races, reused outcomes,
  actual transaction rollback on commit failure, two concurrent project contexts,
  failed submission, shutdown ordering, orphan/no-op cancellation, sensitive data
  exclusion, nested configuration and broken sinks.
- A real Uvicorn process was launched twice against one disposable database.
  Each generation emitted exactly six JSON events with correct context/progress;
  completed state survived restart, no duplicate events appeared, and a synthetic
  private prompt/token/path did not appear in captured process stderr. Normal
  Uvicorn signal re-raising was checked alongside completed application shutdown.

Final suite command:

```bash
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
```

Checks used approved local execution and temporary test data. On the September 11
resume the implementation/tests were already present in the clean workspace;
the remaining edits were documentation and link/status/whitespace verification.
Application tests were not rerun just for those documentation edits. No frontend
code changed in 1.14; its last build/lint/browser evidence remains
[step 1.13](sample-preview-checkpoint.md). Remote CI was not run.

No user runtime database, fixture originals, dependencies, model/GPU resources or
public deployment were changed by this step. Existing user work was preserved.
Logs are diagnostic, best-effort output; they do not add retention, a durable audit
trail, recovery or a global third-party redaction policy. See the
[event contract and operational limits](pipeline-logging.md).

Next unfinished step: **1.15 — backend/frontend formatter configuration/check**.
The remaining startup and contract work and full 1.17 phase gate are still pending.
