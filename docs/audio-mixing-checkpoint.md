# Phase 2 / 2.6 audio mixing checkpoint

Date: 2026-09-16. **2.6 PASS** for local synthetic dialogue/background mixing.
Next bounded task: **2.7 SRT subtitles and optional burn-in**.

New media/audio.py mixer combines dialogue and optional background, resamples to
AAC stereo 48 kHz, pads/trims to video duration, applies background fades and peak
limiting, and preserves video frames through stream copy. Output replacement is
atomic with temporary-file cleanup. [Behavior/limits](audio-mixing.md).

- **362 backend tests PASS**, three existing warnings, 77.51 seconds; eight new
  audio signal/timing/failure cases. Full Phase 1/2 regression included.
- Command: `DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -o faulthandler_timeout=30`.
- Backend incremental formatter PASS.
- Actual Chromium unmuted playback: ended=true, time=2 seconds, audio decoded
  bytes=16568, error=null. Browser process cleaned up. This verifies playback,
  not human listening quality. Test content is synthetic tone, not speech.
- Session-local output `/tmp/animation-audio-mix-acceptance/clip.mp4`, browser
  harness `/tmp/check_audio_mix.mjs`. Older temporary evidence had expired;
  fresh output/harness was generated before the successful browser check.

No dependency/UI/API/database change, real AI, personal voice or paid compute.
Automated tests and browser used approved local escalation for sandbox limits.
Full UI regression was not repeated because UI is unchanged. Background is not
looped, dialogue starts at zero, and video transitions are not implemented here.
