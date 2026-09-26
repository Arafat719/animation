# Local composer export bundle — 2.8

`animation_studio.media.export.export_bundle` composes clips into a **new** output
directory. Existing destinations are refused. It normalizes clips, concatenates,
optionally replaces audio with dialogue/background, optionally burns subtitles,
and writes a thumbnail and reproducibility manifest.

```python
from animation_studio.media.export import export_bundle
from animation_studio.media.subtitles import SubtitleCue

export_bundle(
    ['tests/fixtures/composer/shapes.mp4'] * 2,
    '/tmp/my-new-export',
    dialogue='tests/fixtures/composer/tone.wav',
    cues=[SubtitleCue(0, 1, 'Hello')],
    width=160, height=96, fps=12,
)
```

Output files:

- `video.mp4`: H.264/AAC composition.
- `thumbnail.png`: decoded first video frame, full output dimensions.
- `subtitles.srt`: when cues are supplied (also kept if burned into video).
- `render_manifest.json`: schema version 1, pipeline version `local-composer-1`,
  FFmpeg/ffprobe version, ordered input paths/roles/hashes, rendering settings,
  cues, stream metadata, output sizes and SHA-256 hashes (excluding itself).

Repeat by passing the recorded ordered clip inputs and settings, plus optional
input roles, to export_bundle with a new destination. The manifest is a record,
not an executable script or automatic replay command. Source hashes are checked
again before publication to detect changes during rendering. The helper does not
snapshot sources or eliminate all concurrent source-write races.

The manifest has no timestamp or destination-specific paths, so repeated runs on
the tested toolchain produce byte-identical manifests and artifacts. Different
FFmpeg/libx264/libass/font versions may change output; cross-machine bit identity
is not promised. Burn-in depends on installed fonts. Input paths/cue text are local
project data: review before sharing the manifest publicly.

All intermediate work lives in a unique temporary directory beside the output.
Only a complete bundle is renamed into place; ordinary failures clean up. Export
destinations must be uniquely assigned by the caller; competing writers to the
same destination are unsupported. Abrupt termination can leave temporary files.

No dialogue preserves concatenated normalized audio. Background requires dialogue.
Burn-in requires cues. Audio and subtitle behavior follows their existing helper
contracts. There is no new UI, TTS, planner or remote generation in this step.

## Verified replay command (2.10)

For a trusted local manifest, run:

```bash
.venv/bin/python -m scripts.replay_render /path/to/render_manifest.json /tmp/new-replay
```

This resolves relative input paths beside the manifest, verifies source hashes,
reconstructs settings/cues, renders into a new destination and compares tool
versions and every recorded output hash/size. Missing/changed sources fail before
rendering. A toolchain/output mismatch fails explicitly and retains the resulting
directory for inspection. No command text is executed from the manifest.
Downloaded sample manifests use basenames: supply the matching source fixtures
beside that manifest before replay. Fonts/encoder differences can cause a mismatch.
This command supersedes the earlier note that there was no replay command.
