"""Deterministic, read-only fixture provider for the private prototype."""

import hashlib
import io
import json
import math
import shutil
import subprocess
import time
import wave
from pathlib import Path
from threading import Event
from typing import Callable, Literal

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, ValidationError


ErrorCode = Literal[
    'invalid_input', 'fixture_missing', 'fixture_invalid', 'dependency_missing',
    'io_error', 'cancelled', 'timeout', 'provider_error',
]


class ProviderError(Exception):
    def __init__(self, code: ErrorCode, message: str):
        self.code = code
        super().__init__(message)


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, str_strip_whitespace=True)


class FakeRequest(Contract):
    prompt: str = Field(min_length=1, max_length=4000)
    seed: int = Field(default=0, ge=0, le=2**32 - 1, strict=True)
    timeout_seconds: float = Field(default=10, gt=0, le=60, allow_inf_nan=False)


class Artifact(Contract):
    kind: Literal['image', 'audio', 'video']
    path: Path
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    duration_seconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class FakeResult(Contract):
    provider_name: Literal['fake'] = 'fake'
    provider_version: Literal['1'] = '1'
    model_name: Literal['fixture-media'] = 'fixture-media'
    model_version: Literal['1'] = '1'
    seed: int = Field(ge=0, le=2**32 - 1, strict=True)
    image: Artifact
    audio: Artifact
    video: Artifact


class ProgressEvent(Contract):
    step: Literal['started', 'image', 'audio', 'video', 'completed']
    progress: int = Field(ge=0, le=100, strict=True)


class HealthResult(Contract):
    healthy: bool
    error_code: ErrorCode | None = None
    message: str | None = None


class FakeConfig(Contract):
    fixture_dir: Path = Path(__file__).resolve().parents[2] / 'tests' / 'fixtures'
    delay_seconds: float = Field(default=0.1, ge=0, le=5, allow_inf_nan=False)


class FakeProvider:
    """Returns shared fixture paths; callers must treat them as read-only.

    Synchronous API intended for a worker, not an async server's event loop.
    Progress callbacks run inline; callback exceptions propagate to the caller.
    """

    def __init__(self, config: FakeConfig | None = None):
        self.config = config or FakeConfig()

    @staticmethod
    def _check(deadline: float, cancel: Event):
        if cancel.is_set():
            raise ProviderError('cancelled', 'Fixture generation was cancelled')
        if time.monotonic() >= deadline:
            raise ProviderError('timeout', 'Fixture provider deadline exceeded')

    def _run(self, arguments: list[str], deadline: float, cancel: Event) -> bytes:
        self._check(deadline, cancel)
        binary = shutil.which(arguments[0])
        if binary is None:
            raise ProviderError('dependency_missing', f'{arguments[0]} is unavailable')
        process = subprocess.Popen(
            [binary, *arguments[1:]], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            while True:
                self._check(deadline, cancel)
                try:
                    output, _ = process.communicate(timeout=max(0, min(0.05, deadline - time.monotonic())))
                    break
                except subprocess.TimeoutExpired:
                    continue
            self._check(deadline, cancel)
            if process.returncode:
                raise ProviderError('fixture_invalid', 'Video fixture could not be decoded')
            return output
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()

    def _artifact(self, kind: Literal['image', 'audio', 'video'], filename: str,
                  deadline: float, cancel: Event) -> Artifact:
        self._check(deadline, cancel)
        path = (self.config.fixture_dir / filename).absolute()
        try:
            content = path.read_bytes()
            if not content:
                raise ProviderError('fixture_invalid', f'{kind} fixture is empty')
            duration = None
            if kind == 'image':
                try:
                    with Image.open(io.BytesIO(content)) as image:
                        image.load()
                except OSError as error:
                    raise ProviderError('fixture_invalid', 'Image fixture could not be decoded') from error
            elif kind == 'audio':
                with wave.open(io.BytesIO(content), 'rb') as audio:
                    if (audio.getsampwidth() != 2 or audio.getnchannels() != 1
                            or audio.getcomptype() != 'NONE' or audio.getnframes() <= 0):
                        raise ProviderError('fixture_invalid', 'Expected non-empty mono PCM16 silence')
                    frames = audio.readframes(audio.getnframes())
                    if len(frames) != audio.getnframes() * 2 or any(frames):
                        raise ProviderError('fixture_invalid', 'Audio fixture must contain complete silent samples')
                    duration = audio.getnframes() / audio.getframerate()
            else:
                output = self._run([
                    'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                    '-show_entries', 'stream=codec_type:format=duration', '-of', 'json', str(path),
                ], deadline, cancel)
                info = json.loads(output)
                duration = float(info['format']['duration'])
                if (not info['streams'] or info['streams'][0]['codec_type'] != 'video'
                        or not math.isfinite(duration) or duration <= 0):
                    raise ProviderError('fixture_invalid', 'Expected a video stream with positive duration')
                self._run([
                    'ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i', str(path),
                    '-map', '0:v:0', '-f', 'null', '-',
                ], deadline, cancel)
            self._check(deadline, cancel)
            return Artifact(kind=kind, path=path, sha256=hashlib.sha256(content).hexdigest(),
                            duration_seconds=duration)
        except FileNotFoundError as error:
            raise ProviderError('fixture_missing', f'{kind} fixture is missing') from error
        except (ValueError, KeyError, IndexError, TypeError, EOFError, wave.Error) as error:
            raise ProviderError('fixture_invalid', f'{kind} fixture is invalid') from error
        except OSError as error:
            raise ProviderError('io_error', f'Unable to read {kind} fixture') from error

    def health_check(self, *, timeout_seconds: float = 10, cancel: Event | None = None) -> HealthResult:
        try:
            self.generate(FakeRequest(prompt='Fixture health check', timeout_seconds=timeout_seconds),
                          cancel=cancel)
        except ValidationError as error:
            raise ProviderError('invalid_input', 'Invalid health-check timeout') from error
        except ProviderError as error:
            return HealthResult(healthy=False, error_code=error.code, message=str(error))
        return HealthResult(healthy=True)

    def generate(self, request: FakeRequest | dict[str, object], *, cancel: Event | None = None,
                 on_progress: Callable[[ProgressEvent], None] | None = None) -> FakeResult:
        try:
            request = FakeRequest.model_validate(request)
        except ValidationError as error:
            raise ProviderError('invalid_input', 'Invalid fake generation request') from error
        cancel = cancel if cancel is not None else Event()
        deadline = time.monotonic() + request.timeout_seconds

        def emit(step, progress):
            self._check(deadline, cancel)
            if on_progress is not None:
                on_progress(ProgressEvent(step=step, progress=progress))
            self._check(deadline, cancel)

        emit('started', 0)
        artifacts = {}
        for kind, filename, progress in (
            ('image', 'sample_image.png', 30),
            ('audio', 'silent_audio.wav', 60),
            ('video', 'sample_video.mp4', 90),
        ):
            cancel.wait(min(self.config.delay_seconds, max(0, deadline - time.monotonic())))
            self._check(deadline, cancel)
            artifacts[kind] = self._artifact(kind, filename, deadline, cancel)
            emit(kind, progress)
        result = FakeResult(seed=request.seed, **artifacts)
        emit('completed', 100)
        return result
