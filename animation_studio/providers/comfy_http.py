"""ComfyUI HTTP executor, deliberately restricted to injected mock transport.

No retries or live dispatch. Cancellation/timeout after a validated receipt sends
one prompt-scoped cancel request; this does not prove server execution stopped. I/O timeouts and checks
between chunks bound cooperative progress, not a hard wall-clock deadline.
"""

import json
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from uuid import UUID

import httpx

from animation_studio.providers.comfy_image import MAX_IMAGE_BYTES
from animation_studio.providers.comfy_preflight import validate_node_inventory
from animation_studio.providers.comfy_workflow import validate_image_workflow
from animation_studio.providers.image import ImageErrorCode, ImageProviderError

MAX_JSON_BYTES = 1024 * 1024


@dataclass(frozen=True)
class ComfyReceipt:
    """In-memory accepted submission identity; not durable recovery evidence."""

    prompt_id: str


@dataclass(frozen=True)
class ComfyCancellation:
    # True: dispatched; False: server no-op; None: cleanup outcome unknown.
    dispatched: bool | None
    error_code: ImageErrorCode | None = None


class ComfyExecutionError(ImageProviderError):
    """Preserve primary failure plus independently observable cleanup outcome."""

    def __init__(self, primary, *, receipt=None, cancellation=None):
        super().__init__(primary.code, str(primary))
        if hasattr(primary, 'cleanup_handle'):
            self.cleanup_handle = primary.cleanup_handle
        self.receipt: ComfyReceipt | None = receipt
        self.cancellation: ComfyCancellation | None = cancellation


class ComfyHTTPExecutor:
    is_mock = True

    def __init__(
        self,
        *,
        transport: httpx.MockTransport | None = None,
        authenticated_client=None,
        transport_client=None,
        timeout_seconds: float = 60,
        poll_interval: float = 0.25,
        max_polls: int = 240,
    ):
        # Local import avoids config/identity/journal module initialization cycle.
        if transport_client is not None:
            from animation_studio.providers.comfy_transport import ComfyTransport

            if (
                type(transport_client) is not ComfyTransport
                or transport is not None
                or authenticated_client is not None
            ):
                raise TypeError('Expected one offline transport client')
            transport_client.require_mock()
        elif authenticated_client is not None:
            from animation_studio.providers.comfy_auth import MockComfyAuthenticatedClient

            if (
                type(authenticated_client) is not MockComfyAuthenticatedClient
                or transport is not None
            ):
                raise TypeError('Expected one mock authenticated client')
        elif type(transport) is not httpx.MockTransport:
            raise TypeError('Comfy executor requires an injected MockTransport')
        for value in (timeout_seconds, poll_interval):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('Timeout and polling interval must be finite and positive')
        if type(max_polls) is not int or not 1 <= max_polls <= 1000:
            raise ValueError('Invalid poll limit')
        self.timeout_seconds = timeout_seconds
        self.poll_interval = poll_interval
        self.max_polls = max_polls
        self._transport_client = transport_client
        self._origin = (
            transport_client.origin
            if transport_client is not None
            else authenticated_client.origin
            if authenticated_client
            else 'https://comfy.invalid:443/'
        )
        self._client = (
            transport_client
            if transport_client is not None
            else authenticated_client
            if authenticated_client is not None
            else httpx.Client(
                base_url='https://comfy.invalid/',
                transport=transport,
                follow_redirects=False,
                trust_env=False,
                headers={'Accept-Encoding': 'identity'},
            )
        )

    @property
    def origin(self):
        return self._origin

    def close(self):
        self._client.close()

    @staticmethod
    def _check(cancel, deadline):
        if cancel is not None and cancel.is_set():
            raise ImageProviderError('cancelled', 'Local wait cancelled; server outcome unknown')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ImageProviderError(
                'timeout', 'Workflow deadline exceeded; server outcome unknown'
            )
        return remaining

    def _read(self, method, path, *, cancel, deadline, limit, mime, **kwargs):
        # Identity imports the journal/executor; defer policy import until dispatch.
        from animation_studio.providers.comfy_request_policy import validate_comfy_request

        remaining = self._check(cancel, deadline)
        validate_comfy_request(
            origin=self.origin,
            method=method,
            path=path,
            timeout=min(10, remaining),
            payload=kwargs.get('json'),
            params=kwargs.get('params'),
        )
        if self._transport_client is not None:
            self._transport_client.require_mock()
            response = self._transport_client.request(
                method,
                path,
                deadline=deadline,
                timeout=min(10, remaining),
                cancel=cancel,
                limit=limit,
                mime=mime,
                payload=kwargs.get('json'),
                params=kwargs.get('params'),
            )
            self._check(cancel, deadline)
            return response.content
        try:
            with self._client.stream(
                method, path, timeout=min(10, remaining), **kwargs
            ) as response:
                self._check(cancel, deadline)
                if response.status_code != 200:
                    raise ImageProviderError('execution_failed', 'Comfy HTTP request rejected')
                if response.headers.get('content-type', '').split(';')[0].strip() != mime:
                    raise ImageProviderError('execution_failed', 'Unexpected response content type')
                if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                    raise ImageProviderError('execution_failed', 'Compressed responses unsupported')
                declared = response.headers.get('content-length')
                if declared is not None and (not declared.isdecimal() or int(declared) > limit):
                    raise ImageProviderError('execution_failed', 'Response byte limit exceeded')
                content = bytearray()
                for chunk in response.iter_bytes(chunk_size=65536):
                    self._check(cancel, deadline)
                    if len(content) + len(chunk) > limit:
                        raise ImageProviderError('execution_failed', 'Response byte limit exceeded')
                    content.extend(chunk)
                self._check(cancel, deadline)
                return bytes(content)
        except httpx.TimeoutException:
            raise ImageProviderError('timeout', 'HTTP timeout; server outcome unknown') from None
        except httpx.TransportError:
            raise ImageProviderError(
                'execution_failed', 'HTTP failure; server outcome unknown'
            ) from None

    def _json(self, method, path, *, cancel, deadline, **kwargs):
        content = self._read(
            method,
            path,
            cancel=cancel,
            deadline=deadline,
            limit=MAX_JSON_BYTES,
            mime='application/json',
            **kwargs,
        )

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate JSON key')
                result[key] = value
            return result

        def invalid_constant(value):
            raise ValueError('Nonfinite JSON value')

        try:
            data = json.loads(content, object_pairs_hook=unique, parse_constant=invalid_constant)
            if not isinstance(data, dict):
                raise TypeError
            return data
        except (TypeError, ValueError, UnicodeError, RecursionError):
            raise ImageProviderError('execution_failed', 'Malformed Comfy response') from None

    @staticmethod
    def _image_reference(history, prompt_id, graph):
        try:
            if set(history) != {prompt_id}:
                raise ValueError
            entry = history[prompt_id]
            prompt = entry['prompt']
            if prompt[1] != prompt_id or validate_image_workflow(
                prompt[2]
            ) != validate_image_workflow(graph):
                raise ValueError
            status = entry['status']
            if status['status_str'] != 'success' or status['completed'] is not True:
                raise ValueError
            images = entry['outputs']['7']['images']
            if not isinstance(images, list) or len(images) != 1:
                raise ValueError
            reference = images[0]
            filename, subfolder = reference['filename'], reference['subfolder']
            # This workflow uses a flat SaveImage prefix. Restrict retrieval to it.
            if (
                reference['type'] != 'output'
                or subfolder != ''
                or not isinstance(filename, str)
                or not re.fullmatch(r'animation_sdxl_turbo_[A-Za-z0-9_-]{1,100}\.png', filename)
            ):
                raise ValueError
            return {'filename': filename, 'subfolder': '', 'type': 'output'}
        except (KeyError, IndexError, TypeError, ValueError):
            raise ImageProviderError(
                'execution_failed', 'Failed or invalid workflow history'
            ) from None

    def _cancel_receipt(self, receipt: ComfyReceipt) -> ComfyCancellation:
        # Independent cleanup budget: original event/deadline must not suppress it.
        try:
            response = self._json(
                'POST',
                f'api/jobs/{receipt.prompt_id}/cancel',
                cancel=None,
                deadline=time.monotonic() + 5,
            )
            if set(response) != {'cancelled'} or type(response['cancelled']) is not bool:
                raise ImageProviderError('execution_failed', 'Invalid cancellation acknowledgement')
            return ComfyCancellation(dispatched=response['cancelled'])
        except ImageProviderError as error:
            return ComfyCancellation(dispatched=None, error_code=error.code)

    def preflight(self, graph: dict[str, dict], *, cancel: Event | None = None) -> None:
        """Bounded read-only inventory check of six unique node classes."""
        validate_image_workflow(graph)
        deadline = time.monotonic() + self.timeout_seconds
        inventory = {}
        for kind in dict.fromkeys(node['class_type'] for node in graph.values()):
            response = self._json('GET', f'object_info/{kind}', cancel=cancel, deadline=deadline)
            if set(response) != {kind}:
                raise ImageProviderError('unsupported', 'Required Comfy node missing')
            inventory[kind] = response[kind]
        validate_node_inventory(graph, inventory)
        self._check(cancel, deadline)

    def execute(
        self,
        graph: dict[str, dict],
        *,
        cancel: Event | None = None,
        on_receipt: Callable[[ComfyReceipt], None] | None = None,
        on_cancel: Callable[[ComfyReceipt, ImageProviderError], ComfyCancellation] | None = None,
    ) -> bytes:
        validate_image_workflow(graph)
        deadline = time.monotonic() + self.timeout_seconds
        receipt = None
        try:
            self._check(cancel, deadline)
            # Once submitted, finish the bounded receipt read despite local cancellation
            # so a valid acknowledgement can be retained and targeted for cleanup.
            submitted = self._json(
                'POST', 'prompt', cancel=None, deadline=deadline, json={'prompt': graph}
            )
            try:
                prompt_id = submitted['prompt_id']
                if not isinstance(prompt_id, str) or str(UUID(prompt_id)) != prompt_id:
                    raise ValueError
                if submitted.get('node_errors') != {} or 'error' in submitted:
                    raise ValueError
            except (KeyError, ValueError):
                raise ImageProviderError(
                    'execution_failed', 'Invalid submit receipt; outcome unknown'
                ) from None
            receipt = ComfyReceipt(prompt_id)
            if on_receipt is not None:
                try:
                    on_receipt(receipt)
                except OSError:
                    raise ImageProviderError('io_error', 'Receipt persistence failed') from None
            return self._poll(graph, prompt_id, cancel=cancel, deadline=deadline)
        except ImageProviderError as primary:
            cancellation = None
            if receipt is not None and primary.code in ('cancelled', 'timeout'):
                cancellation = (
                    on_cancel(receipt, primary)
                    if on_cancel is not None
                    else self._cancel_receipt(receipt)
                )
            raise ComfyExecutionError(
                primary, receipt=receipt, cancellation=cancellation
            ) from primary

    def recover(
        self,
        graph: dict[str, dict],
        receipt: ComfyReceipt,
        *,
        cancel: Event | None = None,
    ) -> bytes:
        """Read-only recovery: fresh bounded polling, never submit or cancel a job."""
        validate_image_workflow(graph)
        if type(receipt) is not ComfyReceipt or not isinstance(receipt.prompt_id, str):
            raise ValueError('Invalid recovery receipt')
        if str(UUID(receipt.prompt_id)) != receipt.prompt_id:
            raise ValueError('Invalid recovery receipt')
        try:
            return self._poll(
                graph,
                receipt.prompt_id,
                cancel=cancel,
                deadline=time.monotonic() + self.timeout_seconds,
            )
        except ImageProviderError as primary:
            raise ComfyExecutionError(primary, receipt=receipt) from primary

    def _poll(self, graph, prompt_id, *, cancel, deadline):
        for index in range(self.max_polls):
            history = self._json('GET', f'history/{prompt_id}', cancel=cancel, deadline=deadline)
            if history:
                reference = self._image_reference(history, prompt_id, graph)
                return self._read(
                    'GET',
                    'view',
                    params=reference,
                    cancel=cancel,
                    deadline=deadline,
                    limit=MAX_IMAGE_BYTES,
                    mime='image/png',
                )
            if index + 1 < self.max_polls:
                remaining = self._check(cancel, deadline)
                (cancel if cancel is not None else Event()).wait(min(self.poll_interval, remaining))
        raise ImageProviderError('timeout', 'Polling limit reached; server outcome unknown')
