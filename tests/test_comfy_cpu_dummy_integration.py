import os
import signal
import threading
import time

import pytest

from animation_studio.providers import comfy_cpu_dummy_integration as integration
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_ram_telemetry import OwnedChildRamReader
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy


@pytest.fixture
def args():
    return {
        'policy': ComfySupervisionPolicy(
            ram_limit_bytes=100,
            host_reserve_bytes=20,
            vram_limit_bytes=80,
            device_index=0,
            sample_interval_seconds=0.01,
            stale_after_seconds=0.1,
            overall_timeout_seconds=1.2,
            cleanup_reserve_seconds=0.3,
            reap_allowance_seconds=0.3,
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
    }


def run(args, mode='cooperate', **changes):
    args = args | {
        'policy': args['policy'].model_copy(
            update={
                'ram_limit_bytes': 128 * 1024 * 1024,
                'host_reserve_bytes': 1,
                'stale_after_seconds': 0.15,
                **changes,
            }
        )
    }
    started = time.monotonic()
    result = integration.supervise_cpu_dummy(**args, mode=mode)
    assert time.monotonic() - started < 2
    assert result.worker_status == 'exited'
    with pytest.raises(ChildProcessError):
        os.waitpid(result.child_pid, os.WNOHANG)
    assert result.scope == 'local_cpu_dummy'
    assert result.telemetry_source == 'local_procfs'
    assert result.vram_status == result.job_status == result.compute_status == 'unknown'
    assert result.storage_status == 'unknown'
    return result


@pytest.mark.parametrize('mode', ['cooperate', 'ignore_stop'])
def test_real_ram_deadline_and_reap(args, mode):
    result = run(args, mode)
    assert result.admitted and result.observed_rss_bytes > 0
    assert result.reasons == ('run_deadline',)
    assert result.stop_requested
    assert result.kill_requested == (mode == 'ignore_stop')
    assert result.returncode == (0 if mode == 'cooperate' else -signal.SIGKILL)
    assert result.sampler_status == 'stopped'


def test_low_threshold_aborts_without_admission(args):
    result = run(args, ram_limit_bytes=1)
    assert not result.admitted
    assert result.reasons == ('ram_limit',)
    assert result.outcome == 'aborted'


@pytest.mark.parametrize(
    'mode,admitted', [('exit_after_ready', True), ('exit_before_ready', False)]
)
def test_normal_exit_race(args, mode, admitted):
    result = run(args, mode)
    assert result.returncode == 0 and result.outcome == 'exited'
    assert result.reasons == ()
    assert result.admitted == admitted
    assert not result.stop_requested


@pytest.mark.parametrize('initial', [True, False])
def test_hung_read_parent_deadline_and_retained_session(args, monkeypatch, initial):
    release = threading.Event()
    original = OwnedChildRamReader.read
    calls = []

    def read(self):
        calls.append(1)
        if initial or len(calls) > 1:
            release.wait(5)
        return original(self)

    monkeypatch.setattr(OwnedChildRamReader, 'read', read)
    result = None
    try:
        result = run(args, 'ignore_stop')
        assert result.outcome == 'needs_manual_cleanup'
        assert result.sampler_status == 'unknown'
        assert result.reasons == (('telemetry_missing',) if initial else ('telemetry_stale',))
        assert result.admitted == (not initial)
        assert result.kill_requested
        assert result.cleanup_sampler is not None
    finally:
        release.set()
        if result is not None:
            assert result.cleanup_sampler.close(deadline=time.monotonic() + 1).status == 'stopped'


@pytest.mark.parametrize('initial', [True, False])
def test_reader_exception_aborts(args, monkeypatch, initial):
    original = OwnedChildRamReader.read
    calls = []

    def read(self):
        calls.append(1)
        if initial or len(calls) > 1:
            raise OSError('private failure text')
        return original(self)

    monkeypatch.setattr(OwnedChildRamReader, 'read', read)
    result = run(args)
    assert result.reasons == ('telemetry_missing',)
    assert result.admitted == (not initial)
    assert result.sampler_status == 'failed'
    assert 'private' not in repr(result)


@pytest.mark.parametrize('change', [{'mode': 'shell'}, {'policy': None}, {'context': None}])
def test_invalid_does_not_spawn(args, monkeypatch, change):
    monkeypatch.setattr(integration, '_spawn', lambda *_: pytest.fail('must not spawn'))
    with pytest.raises(ValueError):
        integration.supervise_cpu_dummy(**(args | {'mode': 'cooperate'} | change))


def test_live_does_not_spawn(args, monkeypatch):
    args['context'] = args['context'].model_copy(update={'mode': 'live'})
    monkeypatch.setattr(integration, '_spawn', lambda *_: pytest.fail('must not spawn'))
    with pytest.raises(ValueError):
        integration.supervise_cpu_dummy(**args, mode='cooperate')


def test_setup_failure_reaps(args, monkeypatch):
    original = integration._spawn
    children = []

    def spawn(mode):
        child = original(mode)
        children.append(child)
        return child

    def fail(*_):
        raise OSError('setup failure')

    monkeypatch.setattr(integration, '_spawn', spawn)
    monkeypatch.setattr(integration.os, 'set_blocking', fail)
    with pytest.raises(OSError, match='setup failure'):
        integration.supervise_cpu_dummy(**args, mode='cooperate')
    assert children[0].poll() is not None
    assert children[0].stdout.closed


@pytest.mark.parametrize('status', ['unavailable', 'identity_mismatch', 'invalid', 'exited'])
def test_first_failure_record_aborts_immediately(args, monkeypatch, status):
    from animation_studio.providers.comfy_ram_telemetry import LocalRamReading

    def read(self):
        return LocalRamReading(status, self._pid, time.monotonic())

    monkeypatch.setattr(OwnedChildRamReader, 'read', read)
    result = run(args)
    expected = {
        'unavailable': 'telemetry_unavailable',
        'identity_mismatch': 'telemetry_identity_mismatch',
        'invalid': 'telemetry_invalid',
        'exited': 'worker_exit_unconfirmed',
    }
    assert result.reasons == (expected[status],)
    assert not result.admitted
    assert result.stop_requested


def test_first_abort_survives_late_healthy_sample(args, monkeypatch):
    from dataclasses import replace

    original = OwnedChildRamReader.read
    calls = []

    def read(self):
        reading = original(self)
        calls.append(1)
        if len(calls) == 1 and reading.status == 'ok':
            return replace(reading, rss_bytes=256 * 1024 * 1024)
        return reading

    monkeypatch.setattr(OwnedChildRamReader, 'read', read)
    result = run(args, 'ignore_stop')
    assert result.reasons == ('ram_limit',)
    assert not result.admitted
    assert len(calls) > 1


def test_unrelated_child_untouched(args):
    import subprocess
    import sys

    other = subprocess.Popen([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(5)'])
    try:
        result = run(args)
        assert other.pid != result.child_pid
        assert other.poll() is None
    finally:
        other.kill()
        other.wait(timeout=1)


@pytest.mark.parametrize('error_type', [OSError, KeyboardInterrupt])
def test_parent_error_retains_hung_sampler(args, monkeypatch, error_type):
    from animation_studio.providers.comfy_ram_sampler import RamSampler

    release = threading.Event()
    entered = threading.Event()
    samplers = []
    original_read = OwnedChildRamReader.read
    original_start = RamSampler.start
    failure = error_type('private parent failure')

    def read(self):
        entered.set()
        release.wait(5)
        return original_read(self)

    def start(self):
        samplers.append(self)
        original_start(self)
        assert entered.wait(1)
        raise failure

    monkeypatch.setattr(OwnedChildRamReader, 'read', read)
    monkeypatch.setattr(RamSampler, 'start', start)
    began = time.monotonic()
    try:
        with pytest.raises(error_type) as caught:
            integration.supervise_cpu_dummy(**args, mode='ignore_stop')
        assert caught.value is failure
        session = caught.value.cpu_dummy_cleanup
        assert session.outcome == 'needs_manual_cleanup'
        assert session.worker_status == 'exited'
        assert session.sampler_status == 'unknown'
        assert session.sampler is samplers[0]
        assert session.child.stdout.closed
        assert session.deadline <= began + args['policy'].overall_timeout_seconds + 0.1
        assert time.monotonic() - began < 2
        assert 'private' not in repr(session)
        with pytest.raises(ChildProcessError):
            os.waitpid(session.child.pid, os.WNOHANG)
    finally:
        release.set()
        for sampler in samplers:
            assert sampler.close(deadline=time.monotonic() + 1).status == 'stopped'


@pytest.mark.parametrize('action', ['stop', 'close'])
def test_cleanup_failure_continues_independent_actions(args, monkeypatch, action):
    from animation_studio.providers.comfy_ram_sampler import RamSampler

    original = getattr(RamSampler, action)
    samplers = []
    failure = OSError('private cleanup failure')

    def fail(self, **kwargs):
        samplers.append(self)
        raise failure

    monkeypatch.setattr(RamSampler, action, fail)
    try:
        with pytest.raises(OSError) as caught:
            integration.supervise_cpu_dummy(**args, mode='cooperate')
        assert caught.value is failure
        session = caught.value.cpu_dummy_cleanup
        assert session.child.poll() is not None
        assert session.child.stdout.closed
        assert 'sampler_' + action + '_failed' in session.error_codes
        assert session.outcome == 'needs_manual_cleanup'
        assert session.errors[0] is failure
        assert 'private' not in repr(session)
    finally:
        monkeypatch.setattr(RamSampler, action, original)
        for sampler in samplers:
            sampler.close(deadline=time.monotonic() + 1)


def test_parent_error_and_failed_kill_retain_unknown_worker(args, monkeypatch):
    import subprocess

    children = []
    waits = []
    original_spawn = integration._spawn
    original_wait = subprocess.Popen.wait
    primary = OSError('private setup error')
    secondary = PermissionError('private signal error')

    def spawn(mode):
        child = original_spawn(mode)
        children.append(child)
        return child

    def fail_setup(*_):
        raise primary

    def fail_signal(*_):
        raise secondary

    def wait(self, timeout):
        waits.append(timeout)
        raise subprocess.TimeoutExpired('dummy', timeout)

    monkeypatch.setattr(integration, '_spawn', spawn)
    monkeypatch.setattr(integration.os, 'set_blocking', fail_setup)
    monkeypatch.setattr(integration, '_signal_owned', fail_signal)
    monkeypatch.setattr(subprocess.Popen, 'wait', wait)
    try:
        with pytest.raises(OSError) as caught:
            integration.supervise_cpu_dummy(**args, mode='cooperate')
        assert caught.value is primary
        session = caught.value.cpu_dummy_cleanup
        assert session.child is children[0]
        assert session.worker_status == 'unknown'
        assert session.outcome == 'needs_manual_cleanup'
        assert session.error_codes == ('worker_kill_failed',)
        assert session.errors == (secondary,)
        assert len(waits) == 1
        assert 0 <= waits[0] <= args['policy'].overall_timeout_seconds
        assert session.child.stdout.closed
        assert 'private' not in repr(session)
    finally:
        monkeypatch.setattr(subprocess.Popen, 'wait', original_wait)
        for child in children:
            child.kill()
            child.wait(timeout=1)
