# Website visual refresh

Date: 2026-09-08

The owner paused pipeline development and requested a premium, Apple-inspired
website redesign. This step updates the shared visual design and project page:
soft white/sage palette, system typography, more whitespace, translucent persistent
navigation with active-page semantics, a two-column project workspace, refined
forms/cards/status displays, and consistent styling across the existing pages.

Added a local SVG landscape illustration and a simple studio mark in
StudioChrome.tsx. They are decorative interface artwork, not generated project
outputs. No external fonts, image service, dependencies or Apple brand assets are
used. Small-screen layouts stack the cards, wrap content, and use 16px form text.
Keyboard focus states and reduced-motion preferences are supported.

Verification:

- Frontend baseline build/lint passed before edits.
- Final strict TypeScript check, production build and Oxlint passed.
- Browser script syntax and git diff --check passed.
- Full existing browser regression passed with real isolated FastAPI/SQLite:
  project creation, progress/cancel, reload/restart persistence, workspace,
  Characters, Voices and Settings, including loading/empty/error/retry flows.
- The first browser run exposed test synchronization assumptions: navigation is
  now always present, and the helper stopped its API while forwarding job reads.
  The intermediate run still recorded two failed job forwards. The final helper
  waits for Home content, leaves the page and drains forwarding before API restart.
  Unexpected errors remain failures; no assertions were removed. The final run
  recorded three expected navigation-cancelled interceptions and no browser errors.
- Separate direct-browser checks passed home at 1440px/390px, Characters at
  390px/320px, Voices at 1440px and Settings at 390px. Verified active navigation,
  page loading and no horizontal overflow; inspected desktop/mobile screenshots.
- No backend implementation changed; the Python suite was not rerun in this
  visual step. The browser regression exercises the real backend.

Files changed: apps/web/src/App.tsx, App.css, index.css,
scripts/check_job_progress.mjs. New: apps/web/src/StudioChrome.tsx and this report.
Existing-file copies/hash snapshot were kept in the temporary directory
/tmp/animation-before-redesign-0u8qse44. Comparison confirmed only the four intended
existing files changed; prior backend/pipeline work and other uncommitted files
were preserved. No Git commit or dependency installation occurred.

Local preview was started at http://127.0.0.1:5173/ with backend port 8000 and a
separate disposable database /tmp/animation-design-preview-e88roz97/demo.db.
It does not show prior saved user projects. Preview processes and temporary data
are session resources, not a permanent public deployment or durable backup.

Pipeline/API runner integration remains paused at the owner's request. This
redesign does not enable real AI generation, voice playback or generated-video
preview. The existing demo job remains accurately described as a progress demo.
