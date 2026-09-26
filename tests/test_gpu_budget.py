from decimal import Decimal, localcontext

import pytest
from pydantic import ValidationError

from animation_studio.providers.gpu import GPUJobRequest, GPUProviderError, MockGPUProvider
from animation_studio.providers.gpu_budget import (
    BudgetConfig,
    BudgetExceeded,
    PlannedGPUShot,
    RenderWorkload,
    estimate_render,
    submit_budgeted_shot,
)


@pytest.fixture
def workload():
    request = GPUJobRequest(
        operation='mock.noop', prompt='নদী', model_name='mock-worker', model_version='1'
    )
    return RenderWorkload(
        gpu_hourly_price='1.2',
        startup_gpu_minutes='2',
        shots=(
            PlannedGPUShot(
                shot_id='first', request=request, gpu_minutes_per_attempt='3', attempts=2
            ),
            PlannedGPUShot(
                shot_id='second', request=request, gpu_minutes_per_attempt='4', attempts=3
            ),
        ),
    )


@pytest.fixture
def config():
    return BudgetConfig(
        max_gpu_hourly_price='1.2',
        max_gpu_minutes_per_job='20',
        max_attempts_per_shot=3,
        max_estimated_cost_per_render='0.4',
    )


class SpyProvider(MockGPUProvider):
    def __init__(self):
        super().__init__()
        self.calls = []

    def submit(self, request, *, timeout_seconds=10):
        self.calls.append((request, timeout_seconds))
        return super().submit(request, timeout_seconds=timeout_seconds)


def test_all_attempts_overhead_and_exact_limits(workload, config):
    estimate = estimate_render(workload, config)
    assert estimate.allowed
    assert estimate.reserved_gpu_minutes == Decimal(20)
    assert estimate.estimated_compute_cost == Decimal('0.400000')
    assert estimate_render(workload, config) == estimate
    assert RenderWorkload.model_validate_json(workload.model_dump_json()) == workload
    assert BudgetConfig.model_validate_json(config.model_dump_json()) == config


@pytest.mark.parametrize(
    'field,value,violation',
    [
        ('max_gpu_hourly_price', '1.199999', 'hourly_price'),
        ('max_gpu_minutes_per_job', '19.999999', 'gpu_minutes'),
        ('max_attempts_per_shot', 2, 'shot_attempts'),
        ('max_estimated_cost_per_render', '0.399999', 'render_cost'),
    ],
)
def test_each_limit_blocks_before_provider(workload, config, field, value, violation):
    limits = BudgetConfig(**{**config.model_dump(), field: value})
    provider = SpyProvider()
    with pytest.raises(BudgetExceeded) as error:
        submit_budgeted_shot(provider, workload, limits, shot_id='first')
    assert error.value.estimate.violations == (violation,)
    assert error.value.code == 'budget_exceeded'
    assert provider.calls == []


def test_whole_render_gate_not_just_selected_shot(workload, config):
    limits = config.model_copy(update={'max_gpu_minutes_per_job': Decimal(10)})
    provider = SpyProvider()
    with pytest.raises(BudgetExceeded):
        submit_budgeted_shot(provider, workload, limits, shot_id='first')
    assert provider.calls == []


def test_admitted_shot_submits_once(workload, config):
    provider = SpyProvider()
    job = submit_budgeted_shot(provider, workload, config, shot_id='second', timeout_seconds=7)
    assert provider.calls == [(workload.shots[1].request, 7)]
    assert job.status == 'queued'


def test_dry_run_does_not_submit(workload, config):
    provider = SpyProvider()
    assert estimate_render(workload, config).allowed
    assert provider.calls == []


def test_upward_rounding_and_decimal_context(workload, config):
    work = workload.model_copy(update={'gpu_hourly_price': Decimal('0.000001')})
    with localcontext() as context:
        context.prec = 3
        result = estimate_render(work, config)
    assert result.estimated_compute_cost == Decimal('0.000001')
    assert not estimate_render(
        work, config.model_copy(update={'max_estimated_cost_per_render': Decimal(0)})
    ).allowed


def test_all_violations_reported(workload):
    config = BudgetConfig(
        max_gpu_hourly_price=0,
        max_gpu_minutes_per_job=0,
        max_attempts_per_shot=1,
        max_estimated_cost_per_render=0,
    )
    assert estimate_render(workload, config).violations == (
        'hourly_price',
        'gpu_minutes',
        'shot_attempts',
        'render_cost',
    )


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', '0.0000001', True])
def test_invalid_cost_input(config, value):
    with pytest.raises(ValidationError):
        BudgetConfig(**{**config.model_dump(), 'max_gpu_hourly_price': value})


@pytest.mark.parametrize('value', [True, 0, -1, 1.5, '2'])
def test_invalid_attempts(workload, value):
    with pytest.raises(ValidationError):
        PlannedGPUShot(**{**workload.shots[0].model_dump(), 'attempts': value})


@pytest.mark.parametrize('value', [0, '-1', 'NaN', 'Infinity'])
def test_invalid_minutes(workload, value):
    with pytest.raises(ValidationError):
        PlannedGPUShot(**{**workload.shots[0].model_dump(), 'gpu_minutes_per_attempt': value})


def test_empty_and_duplicate_shots(workload):
    for shots in [(), (workload.shots[0], workload.shots[0])]:
        with pytest.raises(ValidationError):
            RenderWorkload(**{**workload.model_dump(), 'shots': shots})


def test_missing_config_and_unknown_fields(config):
    with pytest.raises(ValidationError):
        BudgetConfig()
    with pytest.raises(ValidationError):
        BudgetConfig(**config.model_dump(), arbitrary_allowance=5)


def test_unknown_shot_and_invalid_copied_workload_make_no_calls(workload, config):
    provider = SpyProvider()
    with pytest.raises(ValueError, match='not part'):
        submit_budgeted_shot(provider, workload, config, shot_id='absent')
    invalid = workload.model_copy(update={'gpu_hourly_price': Decimal(-1)})
    with pytest.raises(ValidationError):
        submit_budgeted_shot(provider, invalid, config, shot_id='first')
    assert provider.calls == []


def test_provider_failure_propagates_without_retry(workload, config):
    class FailedProvider(SpyProvider):
        def submit(self, request, *, timeout_seconds=10):
            self.calls.append(request)
            raise GPUProviderError('timeout', 'Ambiguous response')

    provider = FailedProvider()
    with pytest.raises(GPUProviderError):
        submit_budgeted_shot(provider, workload, config, shot_id='first')
    assert len(provider.calls) == 1


def test_http_dispatch_is_blocked_before_transport(workload, config):
    import httpx

    from animation_studio.providers.gpu_http import HTTPGPUProvider

    calls = []
    worker = MockGPUProvider()

    def transport(request):
        calls.append(request)
        submitted = GPUJobRequest.model_validate_json(request.content)
        return httpx.Response(202, json=worker.submit(submitted).model_dump(mode='json'))

    with HTTPGPUProvider(
        'http://127.0.0.1', token='test-only', transport=httpx.MockTransport(transport)
    ) as provider:
        blocked = config.model_copy(update={'max_estimated_cost_per_render': Decimal(0)})
        with pytest.raises(BudgetExceeded):
            submit_budgeted_shot(provider, workload, blocked, shot_id='first')
        assert calls == []
        result = submit_budgeted_shot(provider, workload, config, shot_id='first')
        assert result.request == workload.shots[0].request
        assert len(calls) == 1
        assert calls[0].headers['Idempotency-Key']
