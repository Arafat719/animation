import builtins
import copy
import socket
import subprocess
import time

import pytest

from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_resource_guard import ComfyResourceSample, evaluate_resources
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy


@pytest.fixture
def args():
    context = ComfyExecutionContext(
        mode='mock',
        job_id='12345678-1234-4234-8234-123456789abc',
        deployment_id='12345678-1234-4234-8234-123456789abc',
        origin='https://selected.invalid:443/',
        graph_sha256='a' * 64,
        runtime_manifest_sha256='b' * 64,
        model_manifest_sha256='c' * 64,
    )
    policy = ComfySupervisionPolicy(
        ram_limit_bytes=100,
        host_reserve_bytes=20,
        vram_limit_bytes=80,
        device_index=0,
        sample_interval_seconds=1,
        stale_after_seconds=2,
        overall_timeout_seconds=60,
        cleanup_reserve_seconds=5,
        reap_allowance_seconds=5,
    )
    return {
        'policy': policy,
        'context': context,
        'worker_id': 'owned-1',
        'stage': 'admission',
        'start': 10,
        'now': 12,
        'sample': {
            'context': context.model_dump(),
            'worker_id': 'owned-1',
            'device_index': 0,
            'sampled_at': 12,
            'rss_bytes': 1,
            'available_ram_bytes': 100,
            'used_vram_bytes': 0,
        },
    }


def test_fresh_pure_roundtrip(args, monkeypatch):
    before = copy.deepcopy(args)

    def forbidden(*a, **kw):
        raise AssertionError('I/O forbidden')

    original_import = builtins.__import__

    def guarded_import(name, *a, **kw):
        if name.split('.')[0] in ('torch', 'torchvision', 'comfy_kitchen'):
            raise AssertionError('GPU import forbidden')
        return original_import(name, *a, **kw)

    with monkeypatch.context() as patch:
        for obj, name in (
            (builtins, 'open'),
            (socket, 'socket'),
            (socket, 'getaddrinfo'),
            (subprocess, 'Popen'),
            (time, 'sleep'),
            (time, 'time'),
            (time, 'monotonic'),
        ):
            patch.setattr(obj, name, forbidden)
        patch.setattr(builtins, '__import__', guarded_import)
        result = evaluate_resources(**args)
        assert result == evaluate_resources(**args)
    assert args == before
    assert result.action == 'allow' and result.reasons == ()
    assert (result.run_deadline, result.cleanup_deadline, result.final_deadline) == (60, 65, 70)
    assert result.remaining_seconds == 48
    args['sample'] = ComfyResourceSample(**args['sample'])
    assert evaluate_resources(**args) == result


@pytest.mark.parametrize('stage,blocked', [('admission', 'deny'), ('running', 'abort')])
@pytest.mark.parametrize(
    'field,value,reason',
    [
        ('rss_bytes', 99, None),
        ('rss_bytes', 100, 'ram_limit'),
        ('rss_bytes', 101, 'ram_limit'),
        ('available_ram_bytes', 21, None),
        ('available_ram_bytes', 20, 'host_reserve'),
        ('available_ram_bytes', 19, 'host_reserve'),
        ('used_vram_bytes', 79, None),
        ('used_vram_bytes', 80, 'vram_limit'),
        ('used_vram_bytes', 81, 'vram_limit'),
    ],
)
def test_limits(args, stage, blocked, field, value, reason):
    args['stage'] = stage
    args['sample'][field] = value
    result = evaluate_resources(**args)
    assert result.action == (blocked if reason else 'allow')
    assert result.reasons == ((reason,) if reason else ())


@pytest.mark.parametrize(
    'sample_time,now,reason',
    [
        (10, 12, None),
        (10, 12.001, 'telemetry_stale'),
        (9, 12, 'telemetry_invalid'),
        (13, 12, 'telemetry_invalid'),
    ],
)
def test_freshness(args, sample_time, now, reason):
    args['now'] = now
    args['sample']['sampled_at'] = sample_time
    assert evaluate_resources(**args).reasons == ((reason,) if reason else ())


@pytest.mark.parametrize('stage,action', [('admission', 'deny'), ('running', 'abort')])
def test_missing(args, stage, action):
    args.update(stage=stage, sample=None)
    result = evaluate_resources(**args)
    assert (result.action, result.reasons) == (action, ('telemetry_missing',))


@pytest.mark.parametrize(
    'field,value',
    [
        ('worker_id', 'other'),
        ('device_index', 1),
        ('context', {}),
        ('extra', 1),
        *[
            (field, value)
            for field in ('rss_bytes', 'available_ram_bytes', 'used_vram_bytes')
            for value in (True, -1, 1.5, '1')
        ],
        *[('sampled_at', value) for value in (True, -1, '12', float('nan'), float('inf'))],
    ],
)
def test_invalid_sample(args, field, value):
    args['sample'][field] = value
    assert evaluate_resources(**args).reasons == ('telemetry_invalid',)


@pytest.mark.parametrize(
    'field',
    [
        'job_id',
        'deployment_id',
        'graph_sha256',
        'runtime_manifest_sha256',
        'model_manifest_sha256',
        'origin',
        'mode',
    ],
)
def test_identity(args, field):
    replacements = {
        'job_id': '22345678-1234-4234-8234-123456789abc',
        'deployment_id': '22345678-1234-4234-8234-123456789abc',
        'origin': 'https://other.invalid:443/',
        'mode': 'live',
    }
    args['sample']['context'][field] = replacements.get(field, 'd' * 64)
    assert evaluate_resources(**args).reasons == ('telemetry_invalid',)


@pytest.mark.parametrize(
    'now,expired', [(59.9, False), (60, True), (65, True), (70, True), (71, True)]
)
def test_deadline_no_reset(args, now, expired):
    args['now'] = args['sample']['sampled_at'] = now
    result = evaluate_resources(**args)
    assert result.run_deadline == 60
    assert result.reasons == (('run_deadline',) if expired else ())
    assert result.remaining_seconds == max(0, 60 - now)


@pytest.mark.parametrize(
    'field,value',
    [
        ('start', True),
        ('now', '12'),
        ('now', float('nan')),
        ('now', float('inf')),
        ('now', 9),
        ('start', -1),
        ('stage', 'other'),
        ('worker_id', ''),
        ('now', 10**400),
        ('start', 1e308),
    ],
)
def test_invalid_arguments(args, field, value):
    args[field] = value
    with pytest.raises(ValueError):
        evaluate_resources(**args)


def test_overflow_and_unvalidated_models(args):
    args['policy'] = args['policy'].model_copy(update={'overall_timeout_seconds': 1e308})
    args.update(start=1e308, now=1e308)
    with pytest.raises(ValueError):
        evaluate_resources(**args)


def test_multiple_breaches(args):
    args.update(now=60, stage='running')
    args['sample'].update(rss_bytes=100, available_ram_bytes=0, used_vram_bytes=80)
    result = evaluate_resources(**args)
    assert result.action == 'abort'
    assert result.reasons == (
        'telemetry_stale',
        'ram_limit',
        'host_reserve',
        'vram_limit',
        'run_deadline',
    )


def test_revalidate_copied_models(args):
    args['sample'] = ComfyResourceSample(**args['sample']).model_copy(update={'rss_bytes': True})
    assert evaluate_resources(**args).reasons == ('telemetry_invalid',)
    args['policy'] = args['policy'].model_copy(update={'ram_limit_bytes': True})
    with pytest.raises(ValueError):
        evaluate_resources(**args)


def test_live_context_rejected(args):
    args['context'] = args['context'].model_copy(update={'mode': 'live'})
    with pytest.raises(ValueError):
        evaluate_resources(**args)
