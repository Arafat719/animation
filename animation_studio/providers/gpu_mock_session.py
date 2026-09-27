"""Cooperative, process-local mock admission deadline; no live runtime guarantee."""

import math
from collections.abc import Callable
from decimal import Decimal, localcontext

from animation_studio.providers.gpu import GPUJob, MockGPUProvider
from animation_studio.providers.gpu_attempts import LocalAttemptLedger
from animation_studio.providers.gpu_budget import (
    BudgetConfig,
    BudgetExceeded,
    RenderWorkload,
    estimate_render,
)
from animation_studio.providers.gpu_lifecycle import (
    CleanupResult,
    MockLifecycle,
    MockSessionController,
)
from animation_studio.providers.gpu_mock_dispatch import (
    AttemptAlreadyReserved,
    submit_mock_budgeted_shot,
)


class MockSessionClosed(Exception):
    """No more submissions are admitted through this session."""


class MockRenderSession:
    """Single-caller wrapper; caller supplies monotonic ticks and explicit finish.

    Deadline is not restart-persistent. Blocking calls are not interrupted. Resource
    cleanup does not cancel the separate mock provider's in-memory jobs.
    """

    def __init__(
        self,
        provider: MockGPUProvider,
        backend: MockLifecycle,
        ledger: LocalAttemptLedger,
        workload: RenderWorkload,
        config: BudgetConfig,
        *,
        render_id: str,
        clock: Callable[[], float],
    ):
        if (
            type(provider) is not MockGPUProvider
            or type(backend) is not MockLifecycle
            or type(ledger) is not LocalAttemptLedger
        ):
            raise TypeError('Only exact local mock components are supported')
        if not isinstance(render_id, str) or not render_id.strip() or len(render_id) > 4000:
            raise ValueError('Invalid render identity')
        self._work = RenderWorkload.model_validate(workload.model_dump())
        self._config = BudgetConfig.model_validate(config.model_dump())
        estimate = estimate_render(self._work, self._config)
        if not estimate.allowed:
            raise BudgetExceeded(estimate)
        start = clock()
        if (
            isinstance(start, bool)
            or not isinstance(start, (int, float))
            or not math.isfinite(start)
            or start < 0
        ):
            raise ValueError('Invalid start clock')
        with localcontext() as context:
            context.prec = 400
            exact_start = Decimal(start)
            exact_end = exact_start + self._config.max_gpu_minutes_per_job * 60
            end = float(exact_end)
            if Decimal(end) > exact_end:
                end = math.nextafter(end, -math.inf)
        if not math.isfinite(end) or end <= start:
            raise ValueError('Unrepresentable session window')
        self._controller = MockSessionController(
            backend, started_at=start, duration_seconds=end - start
        )
        # Use the conservatively rounded absolute deadline, not another float sum.
        self._controller.deadline = end
        self._provider, self._ledger = provider, ledger
        self._render_id, self._clock = render_id, clock
        self.cleanup_result: CleanupResult | None = None

    @property
    def closed(self) -> bool:
        return self._controller.closed

    @property
    def deadline(self) -> float:
        return self._controller.deadline

    def tick(self) -> CleanupResult | None:
        result = self._controller.tick(self._clock())
        if result is not None:
            self.cleanup_result = result
        return result

    def finish(self) -> CleanupResult:
        self.cleanup_result = self._controller.tick(self._clock(), finished=True)
        return self.cleanup_result

    def fail(self) -> CleanupResult:
        self.cleanup_result = self._controller.tick(self._clock(), failed=True)
        return self.cleanup_result

    def submit(self, *, shot_id: str, attempt_key: str, timeout_seconds: float = 10) -> GPUJob:
        self.tick()
        if self.closed:
            raise MockSessionClosed('Session admission closed')
        # Invalid caller input is rejected before dispatch, without closing the session.
        MockGPUProvider._deadline(timeout_seconds)
        if not isinstance(attempt_key, str) or not attempt_key.strip() or len(attempt_key) > 4000:
            raise ValueError('Invalid attempt key')
        if not any(shot.shot_id == shot_id for shot in self._work.shots):
            raise ValueError('Unknown shot')
        from animation_studio.providers.gpu_attempts import AttemptLimitExceeded, LedgerConflict

        try:
            job = submit_mock_budgeted_shot(
                self._provider,
                self._ledger,
                self._work,
                self._config,
                render_id=self._render_id,
                shot_id=shot_id,
                attempt_key=attempt_key,
                timeout_seconds=timeout_seconds,
            )
        except (AttemptAlreadyReserved, AttemptLimitExceeded, LedgerConflict):
            raise
        except Exception as dispatch_error:
            # Cleanup without a new clock read preserves the original dispatch failure.
            try:
                self.cleanup_result = self._cleanup()
            except Exception as cleanup_error:
                # Keep the caller's dispatch error contract and expose cleanup failure.
                raise dispatch_error from cleanup_error
            raise
        self.tick()
        return job

    def _cleanup(self) -> CleanupResult:
        return self._controller.cleanup()
