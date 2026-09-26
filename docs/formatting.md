# Formatting checks

Step 1.15 introduces pinned development formatters: Ruff 0.16.7 for Python and
Prettier 3.9.6 for web source/configuration and JavaScript helper scripts. Existing
runtime dependencies are unchanged. Install through `requirements-dev.txt` and
`npm ci` in `apps/web`. The check wrapper needs Git and Python 3.11 or 3.12;
frontend checks also need Node and the local web dependencies.

From the repository root:

```bash
.venv/bin/python scripts/check_format.py backend
npm --prefix apps/web run format:check
```

These read-only checks run separately from Oxlint, TypeScript and tests in CI.
They inspect tracked and non-ignored untracked files, including changes that have
not been staged. Deleted files, dependencies, generated output and the npm
lockfile are excluded. Generated `apps/web/public/schemas/` files are also excluded:
`.venv/bin/python -m scripts.export_schemas --check` checks them independently.
Python scope is repository `.py` files; frontend scope is
JS/JSX/MJS/CJS/TS/TSX/CSS/HTML/JSON under `apps/web` and `scripts`, plus the root
Prettier config. Markdown, SVG and media assets are outside this formatting gate.

## Existing formatting debt

At adoption, 29 Python and 14 frontend/helper files needed formatting. To avoid
an unrelated mass rewrite, `.format-baseline.json` records their exact SHA-256
hashes. Only unchanged bytes at the recorded path are exempt. An edit or new file
must pass its formatter in full. Renaming an unformatted file also removes the
allowance. The check prints both checked and exempted counts; a passing incremental
check does **not** mean all existing source is formatted.

Step 1.17a formatted the edited API module and removed its allowance. Current
remaining debt is 28 Python and 14 frontend/helper files; the initial adoption
counts above are historical.

To inspect all debt without changing source:

```bash
.venv/bin/python scripts/check_format.py backend --all
npm --prefix apps/web run format:check:all
```

These strict checks currently exit 1 because the recorded legacy debt remains.
Formatter/configuration failures propagate as nonzero exits. Missing or invalid
baseline data fails the wrapper instead of silently allowing all files.

Format only the files you are working on, then review the diff:

```bash
.venv/bin/python -m ruff format path/to/file.py
npm --prefix apps/web run format -- src/path/to/file.tsx
```

The frontend file argument is relative to `apps/web`. For the browser helper,
use `../../scripts/check_job_progress.mjs`. `ruff.toml` and `.prettierrc.json`
define the style, using single quotes, 100-column wrapping and LF line endings.
Prettier uses two spaces and no JavaScript semicolons. Ruff uses four spaces.

Do not refresh or extend baseline hashes to make a failing change pass. Remove
entries as the corresponding files are formatted or deleted; old entries cannot
exempt different content. The baseline is a one-time adoption record, with no
automatic update command. Changes to formatter versions/configuration or debt
allowances need explicit review, including the strict check. Existing local user
edits were included as-is in the adoption snapshot and were not reformatted.

CLI references: [Ruff formatter](https://docs.astral.sh/ruff/formatter/) and
[Prettier CLI](https://prettier.io/docs/cli).
