import builtins
import copy
import socket
import subprocess
import time
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from animation_studio.providers.comfy_cpu_guard import evaluate_cpu_resources
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_ram_telemetry import LocalRamReading
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy


@pytest.fixture
def args():
    return {
        'policy': ComfySupervisionPolicy(
            ram_limit_bytes=100,
            host_reserve_bytes=20,
            vram_limit_bytes=1,
            device_index=0,
            sample_interval_seconds=1,
            stale_after_seconds=2,
            overall_timeout_seconds=60,
            cleanup_reserve_seconds=5,
            reap_allowance_seconds=5,
        ),
        'context': ComfyExecutionContext(
            mode='mock',
            job_id='12345678-1234-4234-8234-123456789abc',
            deployment_id='12345678-1234-4234-8234-123456789abc',
            origin='https://selected.invalid:443/',
            graph_sha256='a' * 64,
            runtime_manifest_sha256='b' * 64,
            model_manifest_sha256='c' * 64,
        ),
        'expected_pid': 123,
        'expected_start_ticks': 456,
        'start': 10,
        'now': 12,
        'reading': LocalRamReading('ok', 123, 12, 456, 10, 100),
    }


def test_allow_purity_and_immutability(args, monkeypatch):
    before = copy.deepcopy(args)

    def forbidden(*a, **kw):
        pytest.fail('Unexpected I/O')

    original = builtins.__import__

    def imports(name, *a, **kw):
        assert name.split('.')[0] not in ('torch', 'torchvision', 'comfy_kitchen')
        return original(name, *a, **kw)

    with monkeypatch.context() as patch:
        for obj, field in (
            (builtins, 'open'),
            (Path, 'open'),
            (socket, 'socket'),
            (socket, 'getaddrinfo'),
            (subprocess, 'Popen'),
            (time, 'monotonic'),
            (time, 'time'),
            (time, 'sleep'),
        ):
            patch.setattr(obj, field, forbidden)
        patch.setattr(builtins, '__import__', imports)
        result = evaluate_cpu_resources(**args)
        assert evaluate_cpu_resources(**args) == result
    assert args == before and result.action == 'allow' and result.reasons == ()
    assert result.scope == 'local_cpu_dummy' and result.vram_status == 'unknown'
    assert (result.run_deadline, result.cleanup_deadline, result.final_deadline) == (60, 65, 70)
    assert result.remaining_seconds == 48
    with pytest.raises(FrozenInstanceError):
        result.action = 'abort'


@pytest.mark.parametrize(
    'field,value,reason',
    [
        ('rss_bytes', 99, None),
        ('rss_bytes', 100, 'ram_limit'),
        ('rss_bytes', 101, 'ram_limit'),
        ('available_ram_bytes', 21, None),
        ('available_ram_bytes', 20, 'host_reserve'),
        ('available_ram_bytes', 19, 'host_reserve'),
        ('sampled_at', 10, None),
    ],
)
def test_boundaries(args, field, value, reason):
    args['reading'] = replace(args['reading'], **{field: value})
    result = evaluate_cpu_resources(**args)
    assert result.reasons == ((reason,) if reason else ())
    assert result.action == ('abort' if reason else 'allow')


@pytest.mark.parametrize(
    'status,reason',
    [
        ('unavailable', 'telemetry_unavailable'),
        ('invalid', 'telemetry_invalid'),
        ('identity_mismatch', 'telemetry_identity_mismatch'),
        ('exited', 'worker_exit_unconfirmed'),
    ],
)
def test_failure_status(args, status, reason):
    args['reading'] = LocalRamReading(status, 123, 12)
    assert evaluate_cpu_resources(**args).reasons == (reason,)
    args['now'] = 60
    assert evaluate_cpu_resources(**args).reasons == (reason, 'run_deadline')
    args['reading'] = replace(args['reading'], rss_bytes=0)
    assert evaluate_cpu_resources(**args).reasons == ('telemetry_invalid', 'run_deadline')


@pytest.mark.parametrize(
    'field,value',
    [
        ('status', 'other'),
        ('status', []),
        ('pid', 124),
        ('pid', True),
        ('start_ticks', 457),
        ('start_ticks', True),
        ('start_ticks', None),
        ('source', 'synthetic'),
        ('coverage', 'tree'),
        ('vram_bytes', 0),
        *[
            (field, value)
            for field in ('rss_bytes', 'available_ram_bytes')
            for value in (True, None, -1, 1.5, '10')
        ],
        *[
            ('sampled_at', value)
            for value in (True, -1, 9, 13, '12', float('nan'), float('inf'), 10**400)
        ],
    ],
)
def test_forged_readings(args, field, value):
    args['reading'] = replace(args['reading'], **{field: value})
    result = evaluate_cpu_resources(**args)
    assert result.action == 'abort' and result.reasons == ('telemetry_invalid',)


@pytest.mark.parametrize('reading,reason', [(None, 'telemetry_missing'), ({}, 'telemetry_invalid')])
def test_missing_or_wrong_type(args, reading, reason):
    args['reading'] = reading
    assert evaluate_cpu_resources(**args).reasons == (reason,)


@pytest.mark.parametrize('now', [60, 65, 70, 71])
def test_deadline_never_resets(args, now):
    args.update(now=now, reading=replace(args['reading'], sampled_at=now))
    result = evaluate_cpu_resources(**args)
    assert result.run_deadline == 60 and result.remaining_seconds == 0
    assert result.reasons == ('run_deadline',)


def test_simultaneous_breaches(args):
    args['now'] = 60
    args['reading'] = replace(args['reading'], rss_bytes=100, available_ram_bytes=20)
    assert evaluate_cpu_resources(**args).reasons == (
        'telemetry_stale',
        'ram_limit',
        'host_reserve',
        'run_deadline',
    )


@pytest.mark.parametrize(
    'field,value',
    [
        ('expected_pid', True),
        ('expected_pid', 0),
        ('expected_pid', '123'),
        ('expected_start_ticks', True),
        ('expected_start_ticks', -1),
        ('now', 9),
        ('now', float('inf')),
        ('now', float('nan')),
        ('now', '12'),
        ('start', True),
        ('start', -1),
        ('start', 10**400),
        ('context', None),
        ('policy', None),
    ],
)
def test_invalid_arguments(args, field, value):
    args[field] = value
    with pytest.raises(ValueError):
        evaluate_cpu_resources(**args)


def test_live_and_copied_policy_rejected(args):
    args['context'] = args['context'].model_copy(update={'mode': 'live'})
    with pytest.raises(ValueError):
        evaluate_cpu_resources(**args)
    args['context'] = args['context'].model_copy(update={'mode': 'mock'})
    args['policy'] = args['policy'].model_copy(update={'ram_limit_bytes': True})
    with pytest.raises(ValueError):
        evaluate_cpu_resources(**args)


@pytest.mark.parametrize('overall', [60, 1e308])
def test_precision_collapse_or_overflow(args, overall):
    args.update(start=1e308, now=1e308)
    args['policy'] = args['policy'].model_copy(update={'overall_timeout_seconds': overall})
    with pytest.raises(ValueError):
        evaluate_cpu_resources(**args)


def test_stale_and_valid_zero(args):
    args['reading'] = replace(args['reading'], rss_bytes=0, sampled_at=10)
    assert evaluate_cpu_resources(**args).action == 'allow'
    args['now'] = 12.001
    assert evaluate_cpu_resources(**args).reasons == ('telemetry_stale',)
