"""Verified image results for explicit durable submission or GET-only recovery."""

from pathlib import Path
from threading import Event

from animation_studio.providers.comfy_image import ComfyImageProvider
from animation_studio.providers.comfy_journal import DurableComfyExecutor
from animation_studio.providers.comfy_v2_executor import DurableComfyExecutorV2
from animation_studio.providers.image import ImageRequest, ImageResult


class _RecoveryExecutor:
    is_mock = True

    def __init__(self, executor: DurableComfyExecutor | DurableComfyExecutorV2):
        self.executor = executor

    def execute(self, graph: dict[str, dict], *, cancel: Event | None = None) -> bytes:
        return self.executor.recover(graph, cancel=cancel)


class DurableComfyImageProvider:
    """One journal per logical job; both paths use identical image validation.

    Recovery explicitly downloads existing output again; it does not submit,
    infer success from a receipt, overwrite prior files or cache ImageResult.
    Caller owns executor/client lifetime and successful output retention.
    """

    def __init__(
        self, executor: DurableComfyExecutor | DurableComfyExecutorV2, output_directory: Path
    ):
        if type(executor) not in (DurableComfyExecutor, DurableComfyExecutorV2):
            raise TypeError('Expected a durable mock Comfy executor')
        self._generation = ComfyImageProvider(executor, output_directory)
        self._recovery = ComfyImageProvider(_RecoveryExecutor(executor), output_directory)

    def generate(self, request: ImageRequest, *, cancel: Event | None = None) -> ImageResult:
        return self._generation.generate(request, cancel=cancel)

    def recover(self, request: ImageRequest, *, cancel: Event | None = None) -> ImageResult:
        return self._recovery.generate(request, cancel=cancel)
