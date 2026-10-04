"""Mock-only v2 durable submission and identity-matched GET-only recovery."""

import os
from pathlib import Path
from threading import Event

from animation_studio.providers.comfy_http import ComfyHTTPExecutor, ComfyReceipt
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_journal import _fingerprint
from animation_studio.providers.comfy_storage import ComfyJournalStore
from animation_studio.providers.image import ImageProviderError


class DurableComfyExecutorV2:
    is_mock = True

    def __init__(self, executor: ComfyHTTPExecutor, root: Path, context: ComfyExecutionContext):
        if type(executor) is not ComfyHTTPExecutor:
            raise TypeError('Expected mock Comfy HTTP executor')
        if type(context) is not ComfyExecutionContext:
            raise ValueError('Expected execution context')
        self._context = ComfyExecutionContext.model_validate(context.model_dump())
        if self._context.origin != executor.origin:
            raise ValueError('Context must match mock transport origin')
        self.store = ComfyJournalStore(root, self._context)
        self.executor = executor

    def _validate(self, graph, cancel):
        if _fingerprint(graph) != self._context.graph_sha256:
            raise ImageProviderError('execution_failed', 'Execution graph identity mismatch')
        if cancel is not None and cancel.is_set():
            raise ImageProviderError('cancelled', 'Cancelled before durable operation')

    def execute(self, graph: dict[str, dict], *, cancel: Event | None = None) -> bytes:
        self._validate(graph, cancel)
        try:
            with self.store.locked():
                if os.path.lexists(self.store.path):
                    raise ImageProviderError('execution_failed', 'Journal exists; use recovery')
                self.executor.preflight(graph, cancel=cancel)
                self._validate(graph, cancel)
                self.store.create_intent()

                def persist(receipt):
                    try:
                        self.store.accept(receipt.prompt_id)
                    except (OSError, ValueError, RuntimeError):
                        raise ImageProviderError('io_error', 'Receipt persistence failed') from None

                return self.executor.execute(graph, cancel=cancel, on_receipt=persist)
        except (OSError, ValueError, RuntimeError):
            raise ImageProviderError(
                'io_error', 'Journal unavailable; submission not retried'
            ) from None

    def recover(self, graph: dict[str, dict], *, cancel: Event | None = None) -> bytes:
        self._validate(graph, cancel)
        try:
            with self.store.locked():
                record = self.store.read()
                if record.state != 'accepted':
                    raise ImageProviderError('execution_failed', 'Submission outcome unknown')
                return self.executor.recover(graph, ComfyReceipt(record.prompt_id), cancel=cancel)
        except (OSError, ValueError, RuntimeError):
            raise ImageProviderError(
                'io_error', 'Recovery journal unavailable or incompatible'
            ) from None
