# Phase 2 / 2.7 subtitles checkpoint

Date: 2026-09-16. **2.7 PASS.** Next bounded task: **2.8 thumbnail and reproducible
render manifest**. Full Phase 2 is still incomplete.

Added plain-text timed SRT generation/export and optional libass burn-in with
unique temporary workspace, atomic destination replacement and audio stream copy.
See [contract and limits](subtitles.md).

- **375 backend tests PASS**, three existing warnings, 56.07 seconds; 13 new cases.
- Millisecond timing, ordering/overlap rejection, Unicode/multiline export and
  output preservation on validation/encoder failure PASS.
- Actual FFmpeg subtitle pixels absent before/after cue and visible during cue;
  video resolution/FPS/duration and encoded AAC bytes preserved.
- Apostrophe/colon/Unicode directory paths work. Temporary files cleaned up.
- A decoded 640×360 frame visually reviewed: centered readable “Hello world”
  near the lower edge. Session-local `/tmp/subtitle-acceptance/frame.png` and
  `subtitled.mp4` retained for review. Bangla font appearance not verified.
- Backend incremental formatter and all 17 schema drift checks PASS.

Full command: `DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -o faulthandler_timeout=30`.
Approved escalation used for established TestClient sandbox limits. No UI/API,
dependency, runtime database, AI or paid resource changes. UI/browser suite not
repeated because no UI changed. Subtitle helpers are not automatic transcription,
dialogue timing or a complete integrated export pipeline.
