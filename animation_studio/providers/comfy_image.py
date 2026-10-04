"""Image boundary for an injected Comfy workflow executor; no built-in network I/O.

Live HTTP submission, polling, authentication and bounded downloads belong to a
future executor. An executor must return bounded PNG bytes, honor cancellation,
and raise ImageProviderError for operational failures. No automatic retry occurs.
"""

import hashlib
import io
import tempfile
from pathlib import Path
from threading import Event
from typing import Protocol

from PIL import Image

from animation_studio.providers.comfy_workflow import build_image_workflow
from animation_studio.providers.image import ImageProviderError, ImageRequest, ImageResult

MAX_IMAGE_BYTES = 16 * 1024 * 1024


class ComfyWorkflowExecutor(Protocol):
    # Trusted application configuration, never inferred from server output.
    is_mock: bool

    def execute(self, graph: dict[str, dict], *, cancel: Event | None = None) -> bytes: ...


class ComfyImageProvider:
    """Validate one 512x512 PNG and retain it in a unique caller-read-only file.

    The executor is explicitly injected; construction cannot enable live dispatch.
    Model metadata is the workflow's declared mapping, not a remote weight attestation.
    Successful files remain for the caller; retention and API delivery are separate.
    """

    def __init__(self, executor: ComfyWorkflowExecutor, output_directory: Path):
        if type(executor.is_mock) is not bool:
            raise ValueError('Executor must declare boolean mock provenance')
        self.executor = executor
        self.is_mock = executor.is_mock
        self.output_directory = output_directory.absolute()

    @staticmethod
    def _check_cancel(cancel: Event | None):
        if cancel is not None and cancel.is_set():
            raise ImageProviderError('cancelled', 'Image generation was cancelled')

    def generate(self, request: ImageRequest, *, cancel: Event | None = None) -> ImageResult:
        request = ImageRequest.model_validate(request)
        self._check_cancel(cancel)
        try:
            graph = build_image_workflow(request)
        except ValueError as error:
            raise ImageProviderError('unsupported', 'Unsupported image model or version') from error
        try:
            content = self.executor.execute(graph, cancel=cancel)
        except TimeoutError as error:
            raise ImageProviderError('timeout', 'Workflow execution timed out') from error
        except OSError as error:
            raise ImageProviderError('execution_failed', 'Workflow execution failed') from error
        self._check_cancel(cancel)
        if type(content) is not bytes or not 0 < len(content) <= MAX_IMAGE_BYTES:
            raise ImageProviderError('invalid_image', 'Expected bounded PNG bytes')
        try:
            with Image.open(io.BytesIO(content)) as image:
                if image.format != 'PNG' or image.size != (512, 512) or image.is_animated:
                    raise ImageProviderError('invalid_image', 'Expected one 512x512 PNG')
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image.load()
        except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as error:
            raise ImageProviderError('invalid_image', 'Workflow image is invalid') from error
        self._check_cancel(cancel)
        path = None
        try:
            self.output_directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=self.output_directory, prefix='comfy-', suffix='.png', delete=False
            ) as stream:
                path = Path(stream.name)
                stream.write(content)
            self._check_cancel(cancel)
            return ImageResult(
                provider_name='comfy-image',
                provider_version='1',
                model_name=request.model_name,
                model_version=request.model_version,
                seed=request.seed,
                is_mock=self.is_mock,
                path=path,
                width=512,
                height=512,
                sha256=hashlib.sha256(content).hexdigest(),
            )
        except (OSError, ImageProviderError) as error:
            if path is not None:
                path.unlink(missing_ok=True)
            if isinstance(error, ImageProviderError):
                raise
            raise ImageProviderError('io_error', 'Workflow image cannot be saved') from error
