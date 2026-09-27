"""Explicit local mock submission with conservative durable attempt admission."""

from animation_studio.providers.gpu import GPUJob, MockGPUProvider
from animation_studio.providers.gpu_attempts import (
    LocalAttemptLedger,
    MockSubmissionReceipt,
    Reservation,
)
from animation_studio.providers.gpu_budget import BudgetConfig, RenderWorkload


class AttemptAlreadyReserved(Exception):
    """Submission may have happened; this path never resubmits or invents a result."""

    def __init__(self, reservation: Reservation):
        self.reservation = reservation
        super().__init__('Attempt already reserved; inspect its receipt without resubmitting')


def submit_mock_budgeted_shot(
    provider: MockGPUProvider,
    ledger: LocalAttemptLedger,
    workload: RenderWorkload,
    config: BudgetConfig,
    *,
    render_id: str,
    shot_id: str,
    attempt_key: str,
    timeout_seconds: float = 10,
) -> GPUJob:
    """Reserve durably, then submit once to the exact in-memory mock provider.

    A crash between reservation and submit consumes the slot without submitting.
    Any submit failure also consumes it. Replay raises AttemptAlreadyReserved,
    even after success or restart. A minimal receipt records historical acceptance;
    lookup never contacts the provider or reconciles current execution status.
    This is not production wiring, remote exactly-once execution or paid approval.
    """
    if type(provider) is not MockGPUProvider or type(ledger) is not LocalAttemptLedger:
        raise TypeError('Only the local mock provider and local attempt ledger are supported')
    MockGPUProvider._deadline(timeout_seconds)
    workload = RenderWorkload.model_validate(workload.model_dump())
    reservation, fresh = ledger._reserve_once(
        workload, config, render_id=render_id, shot_id=shot_id, attempt_key=attempt_key
    )
    if not fresh:
        raise AttemptAlreadyReserved(reservation)
    shot = next(shot for shot in workload.shots if shot.shot_id == shot_id)
    job = provider.submit(shot.request, timeout_seconds=timeout_seconds)
    ledger._record_mock_receipt(reservation, MockSubmissionReceipt(job_id=job.job_id))
    return job
