# Media fixtures

`sample_image.png`, `sample_video.mp4` and `sample_audio.wav` predate the fake
provider step and are preserved byte-for-byte. The fake provider reuses the
image and video. The existing audio contains nonzero PCM samples and is not
used as the provider's silent audio. This step does not establish new provenance
or licensing claims for the older files.

## Silent audio

`silent_audio.wav` was generated locally on 2026-09-08 from all-zero samples.
It contains no recording, speech, model output or third-party source material.
Format: one second, 16 kHz, mono, 16-bit PCM; 32,044 bytes including the WAV header.

Reproduce into a **new** file using Python's standard library:

```python
import wave

with open('/tmp/reproduced-silence.wav', 'xb') as output:
    with wave.open(output, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b'\0' * 32000)
```

The provider checks full sample count and zero-valued samples, not merely the
presence of an audio stream. Its tests also reject the older non-silent audio.
