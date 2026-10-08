"""Owned offline durable composition. No live admission or synthetic live journals."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event

import httpx

from animation_studio.providers.comfy_admission import ComfyAdmissionObservation, evaluate_admission
from animation_studio.providers.comfy_config import ComfyEndpointConfig
from animation_studio.providers.comfy_http import ComfyHTTPExecutor
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_resource_guard import (
    ComfyResourceSample,
    _time,
    evaluate_resources,
)
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy
from animation_studio.providers.comfy_transport import create_mock_comfy_transport
from animation_studio.providers.comfy_v2_executor import DurableComfyExecutorV2
from animation_studio.providers.image import ImageProviderError


@dataclass(frozen=True)
class OfflineComfyAdmission:
    """Explicit fixture snapshot; caller owns clock-session identity and policy.

    Supply a fresh clock-session ID after process restart, never relabel old
    observations. Missing snapshots support recovery only. No automatic refresh.
    """

    policy: ComfySupervisionPolicy
    worker_id: str
    clock_session_id: str
    max_age_seconds: float
    observations: tuple[ComfyAdmissionObservation, ...]
    run_started_at: float | None = None
    resource_sample: ComfyResourceSample | None = None


class OfflineDurableComfySession:
    """Single owner of transport and durable mock execution; caller owns root.

    Use the same private root/context on restart. Recovery performs GET only and
    never resets generation or cleanup attempts. close() is local cleanup, not
    worker shutdown. This does not provide independent resource/time supervision.
    """

    def __init__(
        self,
        config: ComfyEndpointConfig,
        root: Path,
        context: ComfyExecutionContext,
        *,
        transport: httpx.MockTransport,
        timeout_seconds: float = 60,
        poll_interval: float = 0.25,
        max_polls: int = 240,
        admission: OfflineComfyAdmission | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        if type(config) is not ComfyEndpointConfig or type(context) is not ComfyExecutionContext:
            raise ValueError('Expected explicit offline configuration and context')
        config = ComfyEndpointConfig(origin=config.origin, token=config.token)
        context = ComfyExecutionContext.model_validate(context.model_dump())
        if context.mode != 'mock' or context.origin != config.origin:
            raise ValueError('Offline session requires matching mock context')
        if not callable(clock):
            raise TypeError('Expected admission clock')
        self._admission = admission
        self._clock = clock
        self._last_admission_time = None
        self._closed = False
        self._transport = create_mock_comfy_transport(config, transport=transport)
        try:
            self._http = ComfyHTTPExecutor(
                transport_client=self._transport,
                timeout_seconds=timeout_seconds,
                poll_interval=poll_interval,
                max_polls=max_polls,
            )
            self._durable = DurableComfyExecutorV2(self._http, root, context)
        except BaseException as primary:
            try:
                self._transport.close()
            except Exception:  # noqa: BLE001 — preserve failure and resource ownership.
                primary.cleanup_handle = self._transport
            raise

    @property
    def is_mock(self):
        return True

    def _check(self):
        if self._closed:
            raise ImageProviderError('unsupported', 'Offline session is closed')
        self._transport.require_mock()

    def execute(self, graph: dict[str, dict], *, cancel: Event | None = None) -> bytes:
        self._check()
        return self._durable.execute(graph, cancel=cancel, admission_check=self._check_admission)

    def _check_admission(self):
        self._check()
        snapshot = self._admission
        if type(snapshot) is not OfflineComfyAdmission:
            raise ImageProviderError('unsupported', 'Offline admission snapshot required')
        try:
            now = _time(self._clock())
        except Exception:  # noqa: BLE001 — injected clock failures must not expose details.
            raise ImageProviderError(
                'execution_failed', 'Offline admission clock invalid'
            ) from None
        if self._last_admission_time is not None and now < self._last_admission_time:
            raise ImageProviderError('execution_failed', 'Offline admission clock reversed')
        self._last_admission_time = now
        decision = evaluate_admission(
            context=self._durable._context,
            policy=snapshot.policy,
            worker_id=snapshot.worker_id,
            clock_session_id=snapshot.clock_session_id,
            expected_source='fixture',
            now=now,
            max_age_seconds=snapshot.max_age_seconds,
            observations=snapshot.observations,
        )
        if decision.action != 'allow' or decision.source != 'fixture':
            error = ImageProviderError('execution_failed', 'Offline admission rejected')
            error.admission_reasons = decision.reasons
            raise error
        try:
            sample = snapshot.resource_sample
            if sample is not None:
                if type(sample) is not ComfyResourceSample:
                    raise ValueError('Expected fixture resource sample')
                # Preserve forbidden injected fields instead of dropping them in serialization.
                fields = dict(sample.__dict__)
                if type(fields.get('context')) is ComfyExecutionContext:
                    fields['context'] = dict(fields['context'].__dict__)
                sample = ComfyResourceSample.model_validate(fields)
            resource = evaluate_resources(
                policy=snapshot.policy,
                context=self._durable._context,
                worker_id=snapshot.worker_id,
                stage='admission',
                start=snapshot.run_started_at,
                now=now,
                sample=sample,
            )
        except (ValueError, TypeError, OverflowError):
            error = ImageProviderError('execution_failed', 'Offline resource admission invalid')
            error.resource_reasons = ('resource_input_invalid',)
            raise error from None
        if resource.action != 'allow':
            error = ImageProviderError('execution_failed', 'Offline resource admission rejected')
            error.resource_reasons = resource.reasons
            raise error

    def recover(self, graph: dict[str, dict], *, cancel: Event | None = None) -> bytes:
        self._check()
        return self._durable.recover(graph, cancel=cancel)

    def close(self):
        self._closed = True
        self._transport.close()

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.close()
        except Exception:
            if exc is None:
                raise
            exc.cleanup_handle = self._transport
        return False
