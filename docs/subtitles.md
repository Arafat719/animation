# Composer subtitles — 2.7

`SubtitleCue(start, end, text)` uses seconds. `render_srt(cues)` produces UTF-8
compatible text and `write_srt(cues, path)` writes an atomic SRT export. Export
alone leaves video untouched and does not require FFmpeg.

Times must be finite, nonnegative and below 100 hours. Round to nearest
millisecond using Python round (ties to even); cues must remain positive length,
ordered and non-overlapping after rounding. Gaps and adjacent cues are allowed.
Line endings normalize to LF and outer whitespace is stripped. Blank cues/lines,
control characters, HTML/ASS markup delimiters and backslash escapes are rejected
by this plain-text contract. Unicode and multiline plain text are supported.
An empty list exports an empty file.

`burn_subtitles(video, cues, output)` is the optional video operation. It requires
at least one cue and FFmpeg with libass/subtitles support. It encodes the first
video as H.264/yuv420p and copies the first audio stream if present to MP4.
Caller supplies cues appropriate for the video's duration; cues outside playback
will not be visible and are not used to extend the video.

The generated SRT has a fixed relative filename inside a unique temporary working
directory. Caller paths are never interpolated into the filter expression, so
apostrophes, spaces, Unicode and colons in directories work. Encoding failure
preserves existing output and cleans temporary files; source/output aliases are
rejected. Arbitrary input audio still needs MP4-compatible codecs; normalize first.

Font selection/shaping uses installed libass/fontconfig fonts. UTF-8 SRT export
is verified for Bangla, but Bangla visual/font quality is not claimed by the English
burn-in timing test. Speech transcription, automatic timing, styles and UI controls
are not part of this helper.
