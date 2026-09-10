# Local fixture provider

`animation_studio.providers.fake.FakeProvider` is a synchronous, independent
fixture provider. It does not import the API, connect to SQLite or update jobs.
Run it in a worker when it is eventually connected to an asynchronous server.

```python
from threading import Event
from animation_studio.providers.fake import FakeProvider, FakeRequest

provider = FakeProvider()
health = provider.health_check()
cancel = Event()
result = provider.generate(
    FakeRequest(prompt='A quiet rooftop', seed=42, timeout_seconds=10),
    cancel=cancel,
    on_progress=lambda event: print(event.model_dump()),
)
print(result.model_dump_json(indent=2))
```

The validated request accepts a trimmed prompt (1–4000 characters), integer
seed (0–2^32−1), and a positive timeout up to 60 seconds. Unknown fields are
rejected. A request dictionary is also accepted; invalid requests raise
`ProviderError` with `code='invalid_input'`. Invalid Pydantic model construction
raises `ValidationError` directly. Config is validated via `FakeConfig`.

The default fixture directory is repository-relative `tests/fixtures`, independent
of the working directory. An explicit `FakeConfig(fixture_dir=...)` can supply
another directory. The fixed filenames are `sample_image.png`, `silent_audio.wav`
and `sample_video.mp4`. Prompt text never becomes a file path or shell argument.

Each artifact has an absolute path, kind, SHA-256 and, for audio/video, duration.
The result includes provider/model names, both versions and the request seed.
Prompt and seed do not change fixture content; these are deliberate mock outputs.
For unchanged fixtures/config, the same input gives the same result metadata.
Returned paths refer to shared fixtures and must be treated as read-only.
No copies, generated output directories or timestamps are created.

Before each artifact, the provider waits 0.1 seconds by default; tests can use
`FakeConfig(delay_seconds=0)`. Total runtime also includes decoding. Progress is
`started:0`, `image:30`, `audio:60`, `video:90`, `completed:100`. Validation failure,
timeout or cancellation before completion prevents a completed event/result.
Callbacks run synchronously, must return promptly, and their exceptions propagate.

The single monotonic deadline covers waits and validation. A `threading.Event`
can cancel waits immediately. Video subprocesses are checked at most every 50 ms;
on cancellation/timeout they are killed and reaped. Image/WAV reads and decoding
are synchronous and checked before/after; this provider is for small trusted
fixtures, not untrusted uploads or arbitrarily large media. OS scheduling, process
startup and cleanup can add latency beyond the requested timeout.

Image data is decoded with Pillow. Audio must be complete, nonempty mono PCM16
silence. Video requires a positive duration/video stream from ffprobe and a full
FFmpeg decode. Both commands use argument arrays. System FFmpeg/ffprobe and the
existing pinned Python dependencies are required; no model or network call occurs.

Normalized error codes: `invalid_input`, `fixture_missing`, `fixture_invalid`,
`dependency_missing`, `io_error`, `cancelled`, `timeout`. `health_check()` validates
all three fixtures using the same path and returns a typed health report. It does
not cache readiness; a subsequent generate call validates again.

Run the provider tests from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_fake_provider.py
```

Job execution, artifact persistence/serving and browser previews need separate
approved integration steps. Existing browser-driven demo progress is unchanged.
