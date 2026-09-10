# Micro-step 1.12 — saved fixture artifact API

Date: 2026-09-10. Step 1.12 PASS; full Phase 1 remains PARTIAL.

Resumed from the reconciled build ledger. Yesterday's plan correction already
had a completed report; the owner's continuation request was applied to the next
unfinished implementation step, 1.12.

Added `GET /jobs/{job_id}/artifacts/{image|audio|video}` with optional
`?download=true`. It loads the saved outcome, allows only the three expected
fixture paths, reads a bounded regular file without following symlinks, verifies
its saved SHA-256, and returns that same byte snapshot. Fixed MIME types and safe
job-based filenames support inline media and attachment downloads. Successful
responses and handled artifact/result errors disable caching so retries can
observe completion or restored files.

Invalid IDs/kinds/query fields, absent jobs/outcomes/files, stored corruption,
disallowed paths, changed/empty/oversized/non-regular files, and I/O failures have
explicit responses. Artifact failures use fixed Bangla messages with no saved
filesystem paths. Existing result/dispatch behavior and schemas are preserved.

Validation on Python 3.12 with disposable databases and fixture copies:

- Relevant existing job-result/runner checks: **37 passed**.
- New artifact API checks: **34 passed**.
- Final full backend suite, including the subsequent error-cache fix:
  **206 passed**, two existing dependency deprecation warnings.
- The new tests check all three media types, inline/download headers, client
  reopening, DB/media preservation, forbidden provider execution, request
  validation, and the failure cases above, including traversal, symlinks and FIFO.
- Independent code review found no blocking issue; its error-cache observation
  was fixed before the full regression run.
- Documentation links/status consistency and changed-file whitespace checked.

The first sandbox TestClient baseline stalled and was stopped. Checks passed with
approved local execution; no new dependency install was needed. Final command:

```bash
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
```

No frontend code changed or browser checks rerun in this API-only step. Prior web
checks remain dated evidence in [web fixture checkpoint](web-fixture-checkpoint.md).
No user runtime database was opened/migrated, fixture originals changed, models
downloaded, paid GPU activated, or Git commit created. Remote CI was not run.

Implementation files: `apps/api/main.py`, `animation_studio/media/artifacts.py`,
`tests/test_artifacts_api.py`. Usage/status documentation was updated in README,
the master plan, current ledger, historical starter banner, result/dispatch docs,
and [artifact API contract](artifact-serving.md).

Limits: fixed shared sample media only; 16 MiB per file; Linux filesystem opens;
full HTTP 200 bodies without byte-range streaming; owner-only local API. Artifacts
must still exist at their exact saved default fixture paths. No prompt-specific
animation or automatic crash recovery. Next unfinished step: **1.13 — browser
sample preview/download UI**, with its own browser acceptance checks.
