# Composer failures and sample export UI — 2.9

`checked_export` wraps the local composer with stable error codes and Bengali
messages. It checks missing inputs, FFmpeg availability and free disk before
rendering. Required headroom is max(64 MiB, eight times total input bytes), a
conservative minimum rather than a guaranteed size prediction for arbitrary
resolution/duration. Runtime ENOSPC/EDQUOT and FFmpeg's disk-full diagnostics are
also translated. No test intentionally fills the machine's disk.

Missing/corrupt/unsupported media, invalid settings, changed inputs, existing
destinations, dependency and storage errors have separate safe responses. Raw
paths, subprocess stderr and tracebacks are not sent to the UI. Existing export
atomic publication/cleanup protects previous output; non-disk FFmpeg failures are
reported as invalid/unsupported media and may also require checking local FFmpeg
capabilities. Low-level export_bundle retains its existing exception contract;
use checked_export at application boundaries.

Project workspace now offers a clearly labeled **fixed sample export**, unrelated
to the project's prompt. POST `/composer/sample-export` accepts no filesystem
parameters, uses only the project-authored composer fixtures and produces a ZIP
containing MP4, PNG, SRT and manifest. Absolute source paths are reduced to basenames
in this downloadable manifest; it is not an automatic local path replay recipe.
The local export bundle's full manifest behavior is unchanged.

One export runs at a time per API process. Busy requests return 409. The endpoint
is synchronous on FastAPI's worker thread and does not create a persisted job.
The UI prevents duplicate clicks, shows Bengali failures, permits retry and offers
a ZIP link on success. Navigation aborts the browser request and revokes blob URLs;
it does not cancel an already-running server export. The 120-second client timeout
likewise does not promise server cancellation. This fixed tiny local sample is
not a general upload/export API or durable background queue.

Tests use real missing/corrupt fixtures, injected low-space/runtime disk failures,
API error envelopes and an actual ZIP. Browser failure responses are controlled
HTTP injections; backend tests independently exercise failure translation. Success
uses the real local API. Temporary server output is deleted after ZIP construction.
