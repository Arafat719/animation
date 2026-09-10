# Micro-step 1.4 — TypeScript checkpoint

Date: 2026-09-07

Migrated the existing React browser source from JSX to TSX. Added types for
project responses, form values, connection status and React events. Caught
errors are narrowed from unknown; the root DOM element is checked before use.
Response interfaces describe the current backend contract and do not provide
runtime JSON validation.

TypeScript 5.9.3 is pinned in package.json and package-lock.json. Strict browser
type checking runs through `npm run typecheck` and before every production build.
Existing Vite configuration remains JavaScript. CI now has a frontend job that
installs from the lockfile, runs lint and builds the app.

Validation (Node 22.22.3, npm 10.9.8):

- Before migration: production build passed.
- After migration: strict type-check, production build and Oxlint passed.
- Headless Chrome against the production build passed: initial loading,
  connected/empty state, saving button, successful project creation, numeric
  duration serialization, reload of the saved project response, submission
  error/button recovery and health-error state.
- No uncaught browser errors. Browser API responses were mocked; this does not
  claim live backend persistence was tested in this step.
- Browser check script: `/tmp/animation-ts-browser-check.mjs` (temporary).
- `git diff --check` passed. Remote GitHub CI has not been run.

Changed files: `apps/web/src/App.tsx` and `main.tsx` (renamed from JSX),
`apps/web/index.html`, `apps/web/tsconfig.json`, `apps/web/package.json`,
`apps/web/package-lock.json`, `apps/web/README.md`, `.github/workflows/ci.yml`,
and this checkpoint.

No models, GPU resources or paid services were used. Existing user changes
were retained; no Git commit was made in the already-dirty worktree.
Phase 1 as a whole is still incomplete; SQLite migrations are the next
previously identified gap after the existing health/project UI work.

Configuration references:

- https://vite.dev/guide/features.html#typescript
- https://www.typescriptlang.org/tsconfig/strict.html
