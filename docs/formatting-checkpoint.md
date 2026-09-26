# Micro-step 1.15 — backend/frontend formatter checks

Date: 2026-09-14. Step 1.15 PASS with incremental adoption; full Phase 1 remains
PARTIAL. Whole-repository formatting is not claimed.

Added pinned development-only Ruff 0.16.7 and Prettier 3.9.6, style configuration,
a shared read-only check wrapper, npm commands and independent CI formatter
steps. Ruff is installed in the existing `.venv`; Prettier is installed in
`apps/web/node_modules` and recorded in the npm lockfile. No existing dependency
version was upgraded and runtime requirements did not change.

The repository already had formatting debt and unrelated local edits. The new
`.format-baseline.json` records only files that actually failed a formatter check:
29 Python files and 14 frontend/helper files. An allowance applies only to the
same path and exact content hash; new, renamed or edited files must pass. There
is no automatic baseline refresh. Existing application source, CSS, media and
user edits were not reformatted. The [formatting guide](formatting.md) explains
scope, commands and the limitations of this initial adoption.

Files changed by this step:

- `ruff.toml`, `.prettierrc.json`, `.prettierignore`, `.format-baseline.json` and
  `scripts/check_format.py` — configuration, immutable-content allowances and checks.
- `requirements-dev.txt`, `apps/web/package.json`, `apps/web/package-lock.json`,
  `.github/workflows/ci.yml`, `.gitignore` — installation, commands, CI and cache ignore.
- `tests/test_format_check.py` — 11 gate behavior cases.
- Root/web READMEs, formatting guide/checkpoint, master plan and current build
  ledger — usage, evidence and resume position.

Validation:

- Backend incremental check: PASS, 13 checked and 29 unchanged debt files exempted.
- Frontend incremental check: PASS, 6 checked and 14 unchanged debt files exempted.
- Full strict checks: expected exit 1, reporting exactly 29 Python and 14 frontend
  formatting files; these are recorded debt, not a full-format PASS.
- Actual Ruff/Prettier smoke checks in a disposable Git repository: unchanged debt
  allowed; strict mode rejects it; edited debt and new unformatted files fail;
  corrected files pass; paths containing spaces work; check mode preserves bytes.
- New tests cover exact hash enforcement, untracked/ignored/deleted discovery,
  paths containing spaces, both formatter exit codes (0/1/2), strict mode and
  missing/malformed baseline structure.
- Full backend suite: **241 passed**, two existing dependency deprecation warnings,
  Python 3.12.3. `pip check`: PASS.
- Frontend Oxlint, TypeScript and Vite production build: PASS, Node 22.22.3.
- `git diff --check`: PASS.

The initial sandboxed backend run stalled in Starlette TestClient startup and was
interrupted. The bounded retry outside the sandbox completed in 31 seconds:

```bash
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
```

Package registry access also needed sandbox escalation. Local automatic approval
allowed those actions. Tests used disposable data; no user runtime database was
opened or migrated by this step. Remote CI, Python 3.11 and browser playback were
not run. The existing local UI edits were built/typechecked, not visually reviewed.
No commit was created in the already dirty worktree.

Next unfinished micro-step: **1.16 — one-command local startup**, including API/web
start/stop and port-conflict behavior. The owner's instruction authorizes continuing
the current work; no new permission is needed for that local step. Phase 1's full
1.17 contract/regression gate remains outstanding before Phase 2.
