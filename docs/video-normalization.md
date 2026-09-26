# Composer normalization — 2.4

`normalize_video(input_path, output_path, width=64, height=64, fps=12)` now emits
MP4 with H.264/yuv420p video and AAC stereo 48 kHz audio at 128 kb/s target bitrate.
Dimensions and FPS must be positive integers; dimensions must be even. The first
video and first audio streams are selected; extra streams are omitted.

Existing audio is retained and resampled. Missing audio gets a silent track;
short audio is padded and long audio ends with video (`apad` / `-shortest`). AAC
encoder/frame rounding may introduce a small timing difference. This is format
normalization, not dialogue/background mixing or loudness mastering.

Video scales to fit and pads to the target rectangle at the chosen constant FPS,
with square output pixels. The current acceptance pack uses square-pixel inputs;
anamorphic/rotation/HDR source fidelity has not been established by these tests.
Output uses faststart for MP4 playback. The prior helper discarded all audio.

Only `.mp4` output is supported. Missing/non-video inputs, same-file aliases and
invalid settings are rejected. Encoding uses a unique temporary file beside the
destination, replaces the destination after success, and removes the temporary
file on failure. Existing output and source are preserved if encoding fails.
FFmpeg arguments are passed as arrays; no shell command interpolation.

## Verification

Real two-second 96×48/10 FPS FFV1 inputs normalize to 80×64/12 FPS H.264 with
matching AAC 48 kHz stereo tracks. Cases cover no audio, 0.5-second tone and
3-second tone. Tests inspect stream metadata, full decoding, video/audio timing,
nonzero decoded tone samples and silence after padding. Existing two-source
normalization tests and all earlier media tests also pass.

Validation/failure tests cover odd/zero dimensions, boolean/fractional FPS,
same-file output, audio-only input and an injected encoder failure after probing.
No runtime database, UI, provider fixture, model or dependency change is needed.
Next: 2.5 concat relative/quoted paths, unique list handling and cleanup.
