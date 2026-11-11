"""Per-attempt cooperative clock and immutable deadline ceilings; no supervision."""

import math

from animation_studio.providers.image import ImageProviderError


class ComfyRunBudget:
    def __init__(self, clock):
        self._clock = clock
        self._last = None
        self._binding = None
        self._effective_run = None
        self.run_deadline = None
        self.cleanup_deadline = None

    def now(self):
        try:
            value = self._clock()
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError
            if self._last is not None and value < self._last:
                raise ValueError
        except Exception:  # noqa: BLE001 — never expose injected clock details.
            raise ImageProviderError('execution_failed', 'Workflow clock invalid') from None
        self._last = value
        return value

    def bind(self, decision, identity):
        binding = (identity, decision.run_deadline, decision.cleanup_deadline)
        if self._binding is not None and binding != self._binding:
            raise ImageProviderError('execution_failed', 'Workflow budget changed')
        self._binding = binding
        self.run_deadline = decision.run_deadline
        self.cleanup_deadline = decision.cleanup_deadline

    def deadline(self, seconds, *, cleanup=False):
        ceiling = self.cleanup_deadline if cleanup else self.run_deadline
        if ceiling is None:
            raise ImageProviderError('execution_failed', 'Workflow budget missing')
        candidate = min(self.now() + seconds, ceiling)
        if cleanup:
            return candidate
        if self._effective_run is None:
            self._effective_run = candidate
        return min(candidate, self._effective_run)
