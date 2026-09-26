# Composer audio mixing — 2.6

`animation_studio.media.audio.mix_audio(video, dialogue, output, *,
background_path=None, background_gain=0.2, fade_seconds=0.2)` creates an MP4
with the existing H.264 video and a new AAC 48 kHz stereo track. Normalize video
first. Video must expose a finite positive stream duration. Existing video audio
is replaced, not added to the dialogue/background mix.

Dialogue starts at zero. Short tracks are padded with silence; long tracks trim
to video duration. Background is optional, not looped, and uses linear gain 0–1.
Its fade-in/out duration is clamped to half the video duration. Dialogue has no
fade. Final peak limiter is set to 0.95 with automatic gain disabled and latency
compensation enabled. This is not loudness mastering, speech synthesis, automatic
ducking, timed multiple dialogue segments or video transitions.

Inputs must exist and contain the required streams. Missing/invalid paths, output
aliases, non-MP4 destination, nonfinite gains/fades and unsupported video are
rejected. Unique temporary output and atomic replacement preserve an existing
output on encoding failure. Normal failures clean temporary files; abrupt process
termination is not guaranteed to clean up. All subprocess arguments are arrays.

Real tests use mathematical tones as dialogue stand-ins. They verify decoded PCM
signal energy, silent padding, short/long tracks, fade-in/out, AAC sample format,
video frame hashes, timing and failure cleanup. Synthetic signal checks do not
constitute subjective speech/music listening review. That requires actual dialogue
assets later; no personal voice data or TTS is introduced here.
