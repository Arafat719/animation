# Micro-step 1.13 — sample preview and download UI

Date: 2026-09-10. Step 1.13 PASS; full Phase 1 remains PARTIAL.

Completed the next step authorized by the owner. Saved successful outcomes now
show independent image, video and silent-audio cards on the home page and project
workspace. They use the step 1.12 artifact API. Video/audio have native controls
and do not autoplay. Fixed sample limits remain explicit.

Each preview has loading, HTTP/decode error and manual retry states. A failed
card does not hide the other media or progress. Download makes a fresh artifact
read with `download=true`, checks status/type, and starts a browser download with
a safe job-based filename. Failed downloads stay in the page with retry; duplicate
clicks are guarded. Polling does not reload already mounted media. Abort signals
and object-URL cleanup handle retries, navigation and unmount.

Changed implementation and verification files:

- `apps/web/src/SampleArtifacts.tsx` and `SampleArtifacts.css` — media cards,
  read/download lifecycle, errors, and responsive layout.
- `apps/web/src/JobsPanel.tsx` — saved result integration and summary.
- `apps/web/src/App.css` — constrain the existing 1536px artwork to its container;
  mobile regression exposed this pre-existing overflow alongside the new cards.
- `scripts/check_job_progress.mjs` — preserve binary responses/query strings;
  test real downloads/playback and failure/retry/cleanup; bound CDP waits and
  recognize discarded interception IDs only after observed navigation or matching
  browser request-cancellation events. A stale home-heading assertion now checks
  the existing home form instead of old wording.

Updated root/web READMEs, artifact/result/dispatch usage docs, the master plan,
current ledger and historical starter banner. The web README's old demo/tick
instructions have been replaced with the current background sample flow.

Validation:

- Strict TypeScript, production build and Oxlint PASS, no lint warnings.
- Final headless Chrome regression PASS with a real isolated FastAPI process
  and disposable SQLite database. No uncaught browser exceptions.
- Real image/audio/video decoding, audio playback advancement and video reaching
  playback/end; no autoplay; stable object URLs and no repeated media fetches over
  result polls. The existing video is one frame over one second: Chrome may reject
  `play()` after reaching its end. The test catches only that exact AbortError
  while also requiring `ended`, `currentTime >= duration` and no media error.
- All three browser downloads compared byte-for-byte with original fixtures,
  including filenames. Download error/retry and duplicate-click protection pass.
- Delayed preview loading, missing-media 410 and invalid-image decoding/retry,
  independent cards, navigation while loading and URL cleanup pass.
- Refresh and actual API restart retain previews/results without duplicate jobs
  or demo ticks. Existing cancellation, project isolation, Characters, Voices
  and Settings regression scenarios also pass.
- 390px mobile overflow check and desktop/mobile screenshots checked.
- Documentation links/status and whitespace checks pass.

Commands (build/lint from `apps/web`, browser script from repository root):

```bash
npm run build
npm run lint
timeout 180s node scripts/check_job_progress.mjs
```

The browser run uses approved local execution. Missing-media and invalid-byte
browser cases are controlled responses; Python step 1.12 tests cover real missing,
changed and disallowed files. Forwarding does not verify production CORS. Screenshot
captures and downloads remain in the disposable directory printed by the script.
No dependency/backend/schema changes were needed. The backend suite was not
rerun for this frontend step; its latest result remains **206 passed** from the
[artifact API checkpoint](artifact-api-checkpoint.md). Remote CI was not run.

No runtime user database or original fixture was modified; no models, paid GPU,
public deployment or Git commit. Limits: shared fixed media, silent audio, a
one-frame sample video, full blobs rather than streaming, and no automatic crash
recovery. Already loaded previews are snapshots; downloads reread the file.
“Download started” does not guarantee that a browser saved it to disk.

Next unfinished step: **1.14 — structured pipeline logging**. Phase 1 still needs
the remaining formatter/startup/contract work and its full 1.17 acceptance gate.
