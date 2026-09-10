# React + Vite + TypeScript

## Local development

Use Node.js 22.12 or newer. From `apps/web`:

```bash
npm ci
npm run dev -- --host 127.0.0.1
```

Start the FastAPI backend on `127.0.0.1:8000` using the root README.

```bash
npm run typecheck
npm run lint
npm run build
```

`build` runs strict TypeScript checking before bundling. The browser source is
in `src/App.tsx` and `src/main.tsx`; `tsconfig.json` covers the browser code.
Project response types match the current backend; they do not perform runtime
JSON validation. Vite configuration remains JavaScript.

## Characters

Open **Characters** from the home page, or use `#/characters`. Save a name
(1–120 characters after trimming) and an optional description (up to 4000
characters). Profiles are stored in the Studio SQLite database and survive
refresh/restart. The page supports loading, empty, saving and error/retry states.

The legacy renderer's `characters.json` remains separate and is not imported.
Reference uploads, image generation, editing/deletion and assigning characters
to projects are outside this page's current scope. Names are not unique;
different profiles may share a name and are distinguished by their IDs.

## Voices

Open **Voices** from the home page, or use `#/voices`. Save a required name
(1–120 characters after trimming), optional language (up to 80 characters)
and optional style (up to 400). Blank optional values are stored as null.
POST/GET `/voices` use the existing SQLite table; new profiles have the
`built_in` type. Extra request fields, including custom type and audio paths,
are rejected. Existing rows retain their stored type and remain readable.

The page handles loading, empty lists, saving, success, list retry and save
errors. Failed saves preserve all input and reload the list before allowing
retry; POST requests are not automatically repeated. Names may be shared by
different profile IDs. Refresh and API restart preserve saved profiles.

These are metadata profiles, not a catalog of installed TTS voices. Language
and style are free-text notes, not verified model capabilities. Audio generation,
preview, custom samples, cloning, edit/delete and project assignment are future
steps. No provider or sample storage is connected by this page.

## Settings

Open **Settings** from the home page, or use `#/settings`. This read-only page
loads the current database path from GET `/settings`. The API returns only
`database_path`, as an absolute path; relative environment overrides are shown
relative to the API process working directory. Reading it does not open,
initialize or modify the database. The path indicates the configured location,
not a database health or file-existence check.

The page supports loading, errors and Retry, including an invalid response
without a database path. Refresh reads the current configuration again.
Configuration editing remains a later step; environment configuration is
documented in the root README.

## Project workspace

Choose **Open workspace** beside a saved project. The URL `#/projects/<id>`
opens its title, prompt, duration, status and sample jobs, and survives refresh.
**Back to projects** returns to the list; browser Back/Forward also works.
Missing projects and failed requests have clear messages and a retry control.

A workspace displays only its selected project's jobs and saved sample previews.
The home page shows all jobs. Browser polling only reads progress/results;
the API worker advances sample jobs. Project details remain read-only; editing,
shots and real AI-generated artifacts are not implemented yet.

## Sample generation and media

Create a project with a prompt, then choose **Generate sample**. The API creates
a background fixture job. Polling reads SQLite-backed jobs/results every two
seconds and never calls the legacy demo tick endpoint. Work continues after
leaving the page; refresh restores saved progress and results. An active sample
job prevents another submission for the same project.

Completed samples show image, video and audio cards. Video/audio have native
playback controls and never autoplay; the audio fixture is silent, with no speech.
The current video fixture contains just one frame over one second.
These are fixed shared samples, not animation generated from the prompt, and
they do not match the project's target duration. Failed jobs display their saved
error. Legacy jobs without outcomes show **No saved result available for this job**.

Each card loads independently from `/jobs/{id}/artifacts/{kind}` and shows its own
loading/error state. **Retry preview** rereads only that media. Missing or changed
files show a clear error; other loaded cards and job progress stay visible.
Browser decoding failures also offer retry and download. Result polling keeps
existing media URLs stable, so it does not restart playback or refetch media.
Leaving the page aborts requests and releases temporary blob URLs.

**Download image/audio/video** makes a fresh read using `?download=true`, then
starts a browser download with a safe job-based filename. Duplicate clicks are
guarded while the read is pending. A failed download stays on the page with
**Retry download** and preserves any already loaded preview. **Download started**
means the browser received the file, not that it has been saved to disk. No
download request is retried automatically. Preview snapshots remain visible
until leaving/reloading the page or retrying, even if the underlying file changes.

Queued/running jobs have a **Cancel job** button. It shows **Cancelling…** while waiting
for the API and only reports cancellation after the server responds. Cancelled
jobs keep their last progress through refresh/restart and no longer advance.
A failed request shows an error and allows retry after the status is refreshed.

Browser integration check (from the repository root after building):

```bash
node scripts/check_job_progress.mjs
```

Requires Node 22, the backend `.venv` and Chrome (default
`/opt/google/chrome/chrome`, override with `CHROME_BIN`). It starts an isolated
API and SQLite database in `/tmp`, forwards browser API requests to that API,
injects controlled failures, and checks real media decoding/playback, all three
downloads against fixture bytes, preview/download retry, stable polling URLs,
responsive layout and cleanup on navigation. It also checks refresh/API restart
persistence, cancellation/error recovery, project isolation, Characters/Voices
save/list flows, and Settings loading/path/error/retry. Binary responses and query
strings are forwarded intact. Controlled 410 responses exercise missing-media UI;
the Python artifact tests cover actual missing files. Browser forwarding does not
test production CORS configuration. Screenshots and test downloads are written
only to the disposable directory printed by the script.
