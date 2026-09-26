"""Shared boundary checks; substitute provider fixture for future adapters."""

import pytest
from pydantic import ValidationError

from animation_studio.providers.gpu import (
    GPUJob,
    GPUJobRequest,
    GPUProvider,
    GPUProviderError,
    MockGPUProvider,
)


@pytest.fixture
def provider() -> GPUProvider:
    return MockGPUProvider()


@pytest.fixture
def request_model():
    return GPUJobRequest(
        operation='mock.noop',
        prompt='শান্ত নদী',
        model_name='mock-worker',
        model_version='1',
        seed=42,
    )


def test_contract_submit_status_cancel(provider, request_model):
    assert provider.health_check().healthy
    assert request_model.operation in provider.capabilities().operations
    first = provider.submit(request_model)
    second = provider.submit(request_model)
    assert first.job_id != second.job_id
    assert first.status == 'queued' and first.progress == 0
    assert first.request == request_model
    assert GPUJob.model_validate_json(first.model_dump_json()) == first
    assert provider.status(first.job_id) == first
    cancelled = provider.cancel(first.job_id)
    assert cancelled.status == 'cancelled'
    assert provider.cancel(first.job_id) == cancelled
    assert provider.status(second.job_id) == second


@pytest.mark.parametrize('method', ['status', 'cancel'])
def test_contract_unknown_job(provider, method):
    with pytest.raises(GPUProviderError) as error:
        getattr(provider, method)('absent')
    assert error.value.code == 'not_found'


@pytest.mark.parametrize('timeout', [0, -1, float('nan'), float('inf'), True, '10'])
@pytest.mark.parametrize('method', ['health_check', 'capabilities', 'submit', 'status', 'cancel'])
def test_contract_invalid_deadline(provider, request_model, timeout, method):
    args = (
        (request_model,)
        if method == 'submit'
        else (('absent',) if method in ('status', 'cancel') else ())
    )
    with pytest.raises(GPUProviderError) as error:
        getattr(provider, method)(*args, timeout_seconds=timeout)
    assert error.value.code == 'invalid_input'


@pytest.mark.parametrize(
    'field,value',
    [('operation', 'real.image'), ('model_name', 'real-model'), ('model_version', '2')],
)
def test_mock_rejects_unsupported(request_model, field, value):
    provider = MockGPUProvider()
    request = GPUJobRequest(**{**request_model.model_dump(), field: value})
    with pytest.raises(GPUProviderError) as error:
        provider.submit(request)
    assert error.value.code == 'unsupported'
    assert provider.submit(request_model).job_id == 'mock-gpu-1'


@pytest.mark.parametrize('outcome', ['succeeded', 'failed', 'cancelled'])
def test_mock_lifecycle_and_terminal_stability(request_model, outcome):
    provider = MockGPUProvider()
    queued = provider.submit(request_model)
    running = provider.advance(queued.job_id)
    assert running.status == 'running' and running.progress == 50
    assert queued.status == 'queued'  # immutable earlier snapshot
    assert provider.status(queued.job_id) == running
    terminal = (
        provider.cancel(queued.job_id)
        if outcome == 'cancelled'
        else provider.advance(queued.job_id, fail=outcome == 'failed')
    )
    assert terminal.status == outcome
    assert terminal.request == request_model
    assert terminal.error_code == ('mock_failure' if outcome == 'failed' else None)
    assert provider.cancel(queued.job_id) == terminal
    assert provider.advance(queued.job_id) == terminal


@pytest.mark.parametrize('update', [{'seed': True}, {'seed': -1}, {'prompt': ' '}, {'extra': 1}])
def test_request_validation(request_model, update):
    with pytest.raises(ValidationError):
        GPUJobRequest(**{**request_model.model_dump(), **update})


@pytest.mark.parametrize(
    'status,progress,error',
    [
        ('succeeded', 50, None),
        ('running', 100, None),
        ('queued', 50, None),
        ('failed', 50, None),
        ('cancelled', 0, 'oops'),
        ('running', -1, None),
    ],
)
def test_invalid_snapshots(request_model, status, progress, error):
    with pytest.raises(ValidationError):
        GPUJob(
            job_id='job', request=request_model, status=status, progress=progress, error_code=error
        )


def test_mock_isolation_and_immutable_snapshot(request_model):
    first, second = MockGPUProvider(), MockGPUProvider()
    job = first.submit(request_model)
    with pytest.raises(GPUProviderError):
        second.status(job.job_id)
    with pytest.raises(ValidationError):
        job.request.seed = 10
    with pytest.raises(GPUProviderError) as error:
        first.submit({})
    assert error.value.code == 'invalid_input'
