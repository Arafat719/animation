# Phase 1 follow-up — independent fixture provider

Date: 2026-09-08

Implemented `animation_studio.providers.fake.FakeProvider` with validated
request/result/config/health/progress schemas. It returns shared, read-only
fixture image, silent audio and video paths after predictable per-artifact
delays. Results include SHA-256, audio/video duration, provider/model names,
versions and seed. Prompt/seed do not change this mock's media content.

The provider has health checks, normalized error codes, a monotonic deadline,
threading.Event cancellation and progress events. FFmpeg/ffprobe subprocesses
use argument arrays and are killed/reaped on timeout/cancel. Images are decoded,
audio samples checked for completeness/silence, and video probed and fully decoded.
Caller progress callback exceptions propagate. Usage and timing limits are in
`docs/fake-provider.md`.

Added `tests/fixtures/silent_audio.wav`: locally generated one-second 16 kHz mono
PCM16 zero samples, 32,044 bytes. SHA-256:
`643f8a8dc8bd9c19225afffad2becfec5426180b3749cb208abdf1a6c8354efc`.
Source and reproduction instructions are in `tests/fixtures/README.md`. Existing
sample audio is not silent and remains unchanged. Existing image/video are reused;
this step makes no new provenance/licensing claim about those older files.

Verification:

- Baseline backend suite: 64 passed in 6.55s.
- Initial focused provider tests: 26 passed in 1.37s.
- Final suite including 29 new provider cases: 93 passed in 8.77s; two existing
  TestClient deprecation warnings.
- Covered deterministic output, metadata, media validation, actual silence,
  cwd-independent paths, request/output/config validation, every missing/corrupt
  fixture, non-silent audio rejection, delay, timeout, cancellation before/during
  generation, reuse after cancellation, missing dependencies, I/O errors,
  callback failure propagation and cleanup of hung media subprocesses.
- Full suite ran outside the sandbox using temporary data, disabled real pipeline,
  no Python bytecode writes and no pytest cache. The focused provider suite ran
  inside the sandbox. Earlier session evidence established API tests stall there.
- git diff --check passed. SHA-256 comparison against
  `/tmp/animation-before-fake-phhqy7vi.json` confirmed all 69 pre-existing files
  were unchanged, including prior uncommitted work and original fixtures.

New files only: animation_studio/providers/__init__.py, fake.py,
tests/test_fake_provider.py, tests/fixtures/silent_audio.wav,
tests/fixtures/README.md, docs/fake-provider.md and this checkpoint.

Limitations: independent synchronous provider only; it is not connected to jobs,
artifact serving or the browser. Shared fixture paths must not be modified by
callers. Image/WAV reads are synchronous, with cancellation checks before/after;
use only small trusted fixtures. Progress callbacks must return promptly.
Frontend/build/browser checks were not rerun because no frontend/API integration
changed. Python 3.11 and remote CI were not run. Detailed Phase 1 remains partial.

No existing file edits, installs, user database migrations, model downloads,
network inference, GPU usage or Git commits occurred. Next proposed action:
define one bounded job-integration step and obtain owner approval before coding.
