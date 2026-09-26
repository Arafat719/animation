<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

### Phase 2 — AI ছাড়া video জোড়া দেওয়া

বর্তমান scope: 2.1 helper এবং 2.2–2.5 fixture/playback/normalization/concat acceptance সম্পন্ন। পরবর্তী 2.6 dialogue audio mixing; background audio/fades-ও 2.6-এর scope। 2.7–2.10 ও insufficient-disk UI handling বাকি। [বর্তমান ledger](../../docs/current-build-status.md) ও dated checkpoints অনুসরণ করবে।

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 2.1 | FFmpeg/ffprobe wrapper ও version check বানাবে | unit test pass; shell string interpolation নেই |
| 2.2 | ছোট legal fixture image/audio/video যোগ করবে | fixture source documented এবং files probe হয় |
| 2.3 | একটি image থেকে test video বানাবে | playable MP4 output |
| 2.4 | দুইটি fixture clip একই format-এ normalize করবে | resolution/FPS/codec match |
| 2.5 | দুইটি clip concatenate করবে | duration expected value-এর ±0.5 second |
| 2.6 | একটি dialogue audio track mix করবে | sound plays এবং duration ঠিক থাকে |
| 2.7 | SRT subtitle তৈরি ও optional burn করবে | subtitle timing test pass |
| 2.8 | thumbnail ও `render_manifest.json` বানাবে | output দ্বিতীয়বার reproduce করা যায় |
| 2.9 | corrupt/missing input error handle করবে | crash নয়; পরিষ্কার বাংলা UI error |
| 2.10 | Phase 2 regression test চালাবে | Phase 1-এর test-ও pass থাকে |

## Phase 2 — Deterministic media composer

### Codex tasks

1. Build a safe FFmpeg wrapper using argument arrays, never shell-concatenated user input.
2. Validate inputs with ffprobe.
3. Normalize test clips to the same resolution, FPS, codec and audio format.
4. Concatenate fixture clips, mix dialogue and background audio, add fades and burn optional subtitles.
5. Generate SRT subtitles from timed dialogue.
6. Create the render manifest and thumbnail.
7. Add failure messages for missing/corrupt media and insufficient disk.

### Acceptance gate

- Fixtures export a playable H.264/AAC MP4.
- Duration is within 0.5 seconds of the requested timeline.
- Audio remains synchronized.
- The exact export can be reproduced from its manifest.

---
