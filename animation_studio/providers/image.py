"""Image-only worker boundary and read-only PNG fixture implementation."""

import hashlib
import io
from pathlib import Path
from threading import Event
from typing import Annotated, Literal, Protocol

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1, max_length=4000)]
ImageErrorCode = Literal[
    'unsupported',
    'cancelled',
    'fixture_missing',
    'invalid_image',
    'io_error',
    'execution_failed',
    'timeout',
]


class ImageProviderError(Exception):
    def __init__(self, code: ImageErrorCode, message: str):
        self.code = code
        super().__init__(message)


class ImageContract(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra='forbid',
        frozen=True,
        str_strip_whitespace=True,
        revalidate_instances='always',
    )


class ImageRequest(ImageContract):
    prompt: Text
    model_name: Text
    model_version: Text
    seed: int = Field(default=0, ge=0, le=2**32 - 1)


class ImageResult(ImageContract):
    provider_name: Text
    provider_version: Text
    model_name: Text
    model_version: Text
    seed: int = Field(ge=0, le=2**32 - 1)
    is_mock: bool
    path: Path
    mime_type: Literal['image/png'] = 'image/png'
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')


class ImageProvider(Protocol):
    """Synchronous worker call returning verified, caller-read-only PNG media.

    Invalid requests raise ValidationError; operational failures raise
    ImageProviderError. Results retain the selected model/version and seed.
    Cancellation is cooperative, not a hard I/O deadline. Persistence, job
    scheduling, reference conditioning and API artifact delivery are separate.
    """

    def generate(self, request: ImageRequest, *, cancel: Event | None = None) -> ImageResult: ...


class MockImageProvider:
    """Always returns the same fixture, regardless of prompt/seed; no inference.

    Only fixture-image version 1 is supported. No writes or network calls occur.
    The returned path is shared and must not be deleted or overwritten by callers.
    """

    def __init__(self, fixture_path: Path | None = None):
        self.fixture_path = (
            fixture_path
            if fixture_path is not None
            else Path(__file__).resolve().parents[2] / 'tests/fixtures/sample_image.png'
        ).absolute()

    @staticmethod
    def _check_cancel(cancel: Event | None):
        if cancel is not None and cancel.is_set():
            raise ImageProviderError('cancelled', 'Image generation was cancelled')

    def generate(self, request: ImageRequest, *, cancel: Event | None = None) -> ImageResult:
        request = ImageRequest.model_validate(request)
        self._check_cancel(cancel)
        if (request.model_name, request.model_version) != ('fixture-image', '1'):
            raise ImageProviderError('unsupported', 'Unsupported image model or version')
        try:
            with self.fixture_path.open('rb') as stream:
                content = stream.read(16 * 1024 * 1024 + 1)
        except FileNotFoundError as error:
            raise ImageProviderError('fixture_missing', 'Image fixture is missing') from error
        except OSError as error:
            raise ImageProviderError('io_error', 'Image fixture cannot be read') from error
        self._check_cancel(cancel)
        if len(content) > 16 * 1024 * 1024:
            raise ImageProviderError('invalid_image', 'Image fixture exceeds the byte limit')
        try:
            with Image.open(io.BytesIO(content)) as image:
                if image.format != 'PNG' or image.width * image.height > 4096 * 4096:
                    raise ImageProviderError('invalid_image', 'Expected a bounded PNG fixture')
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                width, height = image.size
        except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as error:
            raise ImageProviderError('invalid_image', 'Image fixture is invalid') from error
        self._check_cancel(cancel)
        return ImageResult(
            provider_name='mock-image',
            provider_version='1',
            model_name=request.model_name,
            model_version=request.model_version,
            seed=request.seed,
            is_mock=True,
            path=self.fixture_path,
            width=width,
            height=height,
            sha256=hashlib.sha256(content).hexdigest(),
        )
