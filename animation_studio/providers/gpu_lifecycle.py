"""Mock-only session deadline and cleanup, including REST transport fixtures."""

import math
from dataclasses import dataclass
from typing import Literal

from animation_studio.providers.gpu import ErrorCode, GPUProviderError
from animation_studio.providers.runpod_lifecycle import RunPodLifecycle


@dataclass(frozen=True)
class ResourceState:
    pod_id: str
    compute: Literal['running', 'stopped', 'absent', 'unknown']
    storage: Literal['none', 'retained', 'unknown']


@dataclass(frozen=True)
class CleanupResult:
    state: ResourceState
    errors: tuple[str, ...]
    provider_codes: tuple[ErrorCode, ...] = ()

    @property
    def complete(self) -> bool:
        return self.state.compute == 'absent' and self.state.storage == 'none'


class MockLifecycle:
    """Simulates one already-created disposable Pod; failures are explicit controls."""

    def __init__(self, pod_id: str, *, storage: Literal['none', 'retained', 'unknown'] = 'none'):
        if not pod_id or storage not in ('none', 'retained', 'unknown'):
            raise ValueError('Invalid resource')
        self.state = ResourceState(pod_id, 'running', storage)
        self.failures: set[str] = set()
        self.calls: list[str] = []

    def _call(self, operation: str, pod_id: str):
        if pod_id != self.state.pod_id:
            raise ValueError('Resource ID mismatch')
        self.calls.append(operation)
        if operation in self.failures:
            raise RuntimeError('Simulated lifecycle failure')

    def inspect(self, pod_id: str) -> ResourceState:
        self._call('inspect', pod_id)
        return self.state

    def stop(self, pod_id: str):
        self._call('stop', pod_id)
        if self.state.compute != 'absent':
            self.state = ResourceState(pod_id, 'stopped', self.state.storage)

    def terminate(self, pod_id: str):
        self._call('terminate', pod_id)
        self.state = ResourceState(pod_id, 'absent', self.state.storage)


class MockRESTLifecycle:
    """Conservative bridge: desired state never establishes stopped compute.

    Storage remains unknown even when the scoped Pod lookup returns 404.
    Only the mock-transport REST adapter is accepted; no storage deletion.
    """

    def __init__(self, adapter: RunPodLifecycle):
        if type(adapter) is not RunPodLifecycle:
            raise TypeError('Only the mock REST adapter is supported')
        self._adapter = adapter
        self.state = ResourceState(adapter.pod_id, 'unknown', 'unknown')

    def _check(self, pod_id: str):
        if pod_id != self._adapter.pod_id:
            raise ValueError('Resource ID mismatch')

    def inspect(self, pod_id: str) -> ResourceState:
        self._check(pod_id)
        observation = self._adapter.inspect()
        self.state = ResourceState(
            pod_id, 'unknown' if observation.present else 'absent', 'unknown'
        )
        return self.state

    def stop(self, pod_id: str):
        self._check(pod_id)
        self._adapter.stop()

    def terminate(self, pod_id: str):
        self._check(pod_id)
        self._adapter.terminate()


class MockSessionController:
    """Caller ticks a monotonic clock; cleanup on deadline, completion or failure.

    No background watchdog or hard billing cutoff. Only local/mock REST backends accepted.
    No create/retry or retained-storage deletion. Cleanup can be reconciled again.
    """

    def __init__(
        self,
        backend: MockLifecycle | MockRESTLifecycle,
        *,
        started_at: float,
        duration_seconds: float,
    ):
        if type(backend) not in (MockLifecycle, MockRESTLifecycle):
            raise TypeError('Only the local mock backend is supported')
        for value in (started_at, duration_seconds):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError('Expected a finite clock value')
        if started_at < 0 or duration_seconds <= 0:
            raise ValueError('Invalid session window')
        self.deadline = started_at + duration_seconds
        if not math.isfinite(self.deadline):
            raise ValueError('Invalid deadline')
        self._last = started_at
        self._backend = backend
        self._pod_id = backend.state.pod_id
        self.closed = False
        self._auth_failure: CleanupResult | None = None

    def tick(
        self, now: float, *, finished: bool = False, failed: bool = False
    ) -> CleanupResult | None:
        if (
            isinstance(now, bool)
            or not isinstance(now, (int, float))
            or not math.isfinite(now)
            or now < self._last
        ):
            raise ValueError('Clock must be finite and monotonic')
        self._last = now
        if self.closed or finished or failed or now >= self.deadline:
            self.closed = True  # no further work admitted even if cleanup fails
            return self.cleanup()
        return None

    def cleanup(self) -> CleanupResult:
        self.closed = True
        if self._auth_failure is not None:
            return self._auth_failure
        errors = []
        codes = []

        def failed(operation, error):
            errors.append(f'{operation}_failed')
            codes.append(error.code if isinstance(error, GPUProviderError) else 'unavailable')

        def finish(state):
            result = CleanupResult(state, tuple(errors), tuple(codes))
            if 'unauthorized' in codes:
                self._auth_failure = result
            return result

        def inspect():
            try:
                return self._backend.inspect(self._pod_id)
            except (RuntimeError, GPUProviderError) as error:
                failed('inspect', error)
                return ResourceState(self._pod_id, 'unknown', 'unknown')

        state = inspect()
        if 'unauthorized' in codes:
            return finish(state)
        if state.compute != 'absent':
            if state.compute != 'stopped':
                try:
                    self._backend.stop(self._pod_id)
                except (RuntimeError, GPUProviderError) as error:
                    failed('stop', error)
                if 'unauthorized' in codes:
                    return finish(state)
            # Termination fallback follows transient stop failure, not denied auth.
            try:
                self._backend.terminate(self._pod_id)
            except (RuntimeError, GPUProviderError) as error:
                failed('terminate', error)
            if 'unauthorized' in codes:
                return finish(state)
            state = inspect()
        return finish(state)
