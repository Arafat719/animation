# Phase 2 final gate — 2026-09-16

**2.10 / local Phase 2 gate: PASS.**

Scope: deterministic local composer with fixed synthetic fixtures, not real AI
animation. Phase 3 has not started in this gate review.

## Requirements and acceptance

| Requirement | Evidence |
| --- | --- |
| Safe FFmpeg/ffprobe helpers | Argument arrays, real probe/decode and error tests |
| Documented fixtures | Local shape/tone/video generator, provenance and hashes (2.2) |
| Image-to-video | Frame, visual and Chromium playback acceptance (2.3) |
| Matching codec/FPS/resolution/audio | H.264/yuv420p, square pixels, constant FPS and AAC 48 kHz stereo; no/short/long audio tests (2.4) |
| Concatenation | Special/relative paths, concurrency, stream retention, timeline/order and cleanup (2.5) |
| Dialogue/background and fades | Real PCM signal/padding/trimming/fades, video preservation, Chromium audio decoding (2.6) |
| SRT and optional burn-in | Millisecond timing, Unicode export, before/during/after pixels and audio preservation (2.7) |
| Thumbnail and manifest | First-frame pixel equality, hashes/settings/version metadata, repeated outputs (2.8) |
| Missing/corrupt/disk errors | Safe Bengali error boundary, actual ZIP API, UI retry and controlled browser failure checks (2.9) |
| Playable H.264/AAC output | Actual stream/decode tests and recent browser playback evidence; successful composer ZIP |
| Timeline duration ±0.5 s | Combined two-second export satisfies tolerance |
| Synchronized audio | New red/blue boundary at 1 s with delayed tone onset within 50 ms; silence before/after cue |
| Reproduce exact export from manifest | New replay command reconstructs from recorded inputs/settings, validates input and output hashes; MP4/PNG/SRT/manifest byte-identical |

## Gate follow-up implementation

`scripts/replay_render.py` consumes trusted local manifests, checks source hashes,
replays recorded settings/cues and verifies tool versions and output hashes. It
rejects changed inputs before creating a destination. If tools/output differ,
it raises an error and leaves the new output for inspection. No shell commands
from manifest content are executed. See [replay usage](render-bundle.md).

The new end-to-end test uses two colored clips, a delayed synthetic audio cue and
SRT. It checks pixel colors on either side of the boundary, decoded PCM onset,
silence windows, duration and actual manifest-driven replay, including source
hash mismatch refusal.

## Evidence reuse and limits

The immediately preceding [2.9 checkpoint](composer-errors-checkpoint.md) contains
frontend lint/typecheck/build and full browser regression with composer error,
retry and ZIP success. UI/API/composer code is unchanged by this final audit;
those checks were reused rather than rerun. Earlier dated media checks retain
their precise scope; no human speech/music quality approval is implied.

- Local Linux/Python 3.12; remote CI/Python 3.11 not freshly verified.
- Same-toolchain output identity; different encoder/font versions can differ.
- Fixed sample export is synchronous/per-process, not a durable resumable job.
- Disk headroom is heuristic plus runtime detection, not a storage reservation.
- Bangla SRT export works; Bangla font appearance and general HDR/anamorphic media
  quality remain unverified. Dialogue starts at zero; background is not looped.
- Fades are background audio fades; video transitions are not provided.
- No real models, personal voice assets, network download or paid GPU used.
- Existing dirty worktree preserved; earlier Git-object problem not repaired.
- Full V1 30–60 second AI generation, strict planner and shot recovery remain future
  phases. The next bounded task after phase authorization is 3.1 strict planning
  contracts; existing persisted Shot baseline is not that planning contract.

## Final checks

**386 backend tests PASS**, three existing dependency warnings, 70.80 seconds.
Command: `DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -o faulthandler_timeout=30`.
New manifest/sync acceptance passed separately in 5.24 seconds and in the full
suite. Backend formatter, 17-schema drift and pip check PASS. Local escalation
used for the previously established TestClient sandbox limitation.
