# Composer fixtures — locally generated

Created 2026-09-15 by `scripts/generate_composer_fixtures.py`. These files contain
only geometric shapes drawn with Pillow and a mathematical 440 Hz sine wave.
No downloaded content, recordings, personal data, model output or external source
assets are used. They are project-authored test material; no third-party asset
license is being inferred from the older sample files.

- shapes.png: 96×64 RGB rectangle/circle illustration.
- tone.wav: one second, mono PCM16 at 24 kHz, 440 Hz at amplitude 4096/32768.
- shapes.mp4: one second, 96×64, 12 FPS, H.264/yuv420p, no audio.
- provenance.json: source statement, generator path, encoder version, SHA-256s.

Reproduce from the repository root into a new directory:

```bash
.venv/bin/python -m scripts.generate_composer_fixtures /tmp/composer-reproduction
```

Existing destinations are refused. Failed generation can leave a partial new
directory; inspect/remove that directory before retrying. Images/audio are checked
byte-for-byte in the current environment. MP4 bytes may vary by FFmpeg/libx264
version; tests verify streams/duration/full decode and each generation's hashes,
not cross-version MP4 binary identity. The tone is a synthetic test signal, not
speech. These fixtures do not replace the Phase 1 provider's existing files.
