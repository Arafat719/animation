"""Mock-only v2 durable submission and identity-matched GET-only recovery."""

import hashlib
import os
import time
from collections.abc import Callable
from pathlib import Path
from threading import Event

from animation_studio.providers.comfy_http import ComfyCancellation, ComfyHTTPExecutor, ComfyReceipt
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_journal import _fingerprint
from animation_studio.providers.comfy_storage import ComfyJournalStore
from animation_studio.providers.comfy_supervision import ComfySupervisionObservation
from animation_studio.providers.comfy_supervision_storage import ComfySupervisionStore
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
        self.supervision = ComfySupervisionStore(self.store)

    def _validate(self, graph, cancel):
        if _fingerprint(graph) != self._context.graph_sha256:
            raise ImageProviderError('execution_failed', 'Execution graph identity mismatch')
        if cancel is not None and cancel.is_set():
            raise ImageProviderError('cancelled', 'Cancelled before durable operation')

    def execute(
        self,
        graph: dict[str, dict],
        *,
        cancel: Event | None = None,
        admission_check: Callable[[], None] | None = None,
    ) -> bytes:
        self._validate(graph, cancel)
        try:
            with self.store.locked():
                if os.path.lexists(self.store.path):
                    raise ImageProviderError('execution_failed', 'Journal exists; use recovery')
                if admission_check is not None:
                    admission_check()
                self.executor.preflight(graph, cancel=cancel)
                if admission_check is not None:
                    admission_check()
                self._validate(graph, cancel)
                self.store.create_intent()

                def persist(receipt):
                    try:
                        self.store.accept(receipt.prompt_id)
                    except (OSError, ValueError, RuntimeError):
                        raise ImageProviderError('io_error', 'Receipt persistence failed') from None

                return self.executor.execute(
                    graph, cancel=cancel, on_receipt=persist, on_cancel=self._cancel_durably
                )
        except (OSError, ValueError, RuntimeError):
            raise ImageProviderError(
                'io_error', 'Journal unavailable; submission not retried'
            ) from None

    def _cancel_durably(self, receipt, primary):
        # Called under the generation lock. No fallback dispatch if persistence fails.
        try:
            now = int(time.time())
            initial = ComfySupervisionObservation(
                schema_version=1,
                context=self._context,
                prompt_id=receipt.prompt_id,
                primary_outcome=primary.code,
                cleanup_phase='not_requested',
                attempt_count=0,
                created_at=now,
                updated_at=now,
                source='none',
            )
            self.supervision.create(initial)
            intent = initial.model_copy(update={'cleanup_phase': 'intent', 'attempt_count': 1})
            self.supervision.transition(intent)
            result = self.executor._cancel_receipt(receipt)
            updates = {'cleanup_phase': 'unknown'}
            if result.dispatched is not None:
                # Digest of the normalized mock acknowledgement, not remote stop proof.
                evidence = b'cancelled=true' if result.dispatched else b'cancelled=false'
                updates = {
                    'cleanup_phase': 'observed',
                    'source': 'mock',
                    'cancel_dispatched': result.dispatched,
                    'evidence_sha256': hashlib.sha256(evidence).hexdigest(),
                }
            self.supervision.transition(intent.model_copy(update=updates))
            return result
        except (OSError, ValueError, RuntimeError):
            return ComfyCancellation(dispatched=None, error_code='io_error')

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
