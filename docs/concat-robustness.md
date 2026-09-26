# Composer concatenation — 2.5

`concatenate_videos(inputs, output)` stream-copies compatible clips in the supplied
order. Normalize clips to matching video/audio formats first; this helper does
not transcode mismatched inputs or certify arbitrary stream compatibility.

Relative inputs now resolve against the caller's working directory before writing
the ffconcat list. Apostrophes use ffconcat token escaping; spaces, Unicode and
literal backslashes inside quoted paths are preserved. Input line breaks/NUL are
rejected rather than being interpreted as list directives. Missing files and
input/output aliases (including hardlinks) are rejected before encoding.

Each invocation owns a unique temporary directory under the destination parent.
Its list and partial output are removed on success or failure. The destination is
replaced only after FFmpeg succeeds. Existing `concat_input.txt` files are untouched.
Different-output concurrent invocations do not share temporary files. Concurrent
writes to the same destination remain last-successful-writer-wins; callers must
serialize those if necessary. Abrupt process/machine termination can leave temp
files; normal exception cleanup is covered.

FFmpeg runs with argument arrays, without shell interpretation. The output needs
a media extension so the muxer can be selected; supported stream/container pairs
remain subject to FFmpeg. Error reporting to the application UI is future step 2.9.

Tests exercise actual FFmpeg with relative quoted/Unicode/backslash paths, two
parallel outputs, normalized H.264/AAC stream retention, full decode and total
duration within 0.5 seconds. Separate red/blue clips verify output order by decoded
frame colors. Corrupt input preserves the existing destination and cleans up;
missing/newline paths, empty lists and hardlink aliases are rejected.
