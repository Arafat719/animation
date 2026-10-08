import os
import signal
import subprocess
import time

import pytest

from animation_studio.providers.comfy_dummy_supervisor import _signal_owned, supervise_dummy
from animation_studio.providers.comfy_identity import ComfyExecutionContext
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


def assert_reaped(result):
    assert result.worker_status == 'exited'
    with pytest.raises(ChildProcessError):
        os.waitpid(result.child_pid, os.WNOHANG)
    assert result.job_status == result.compute_status == result.storage_status == 'unknown'
    assert result.telemetry_source == 'synthetic'


@pytest.mark.parametrize(
    'mode,code,stop,kill',
    [
        ('normal', 0, False, False),
        ('cooperate', 0, True, False),
        ('ignore_stop', -signal.SIGKILL, True, True),
    ],
)
def test_lifecycle_and_ownership(args, mode, code, stop, kill, monkeypatch):
    real_spawn = subprocess.Popen
    children = []

    def spawn(*a, **kw):
        child = real_spawn(*a, **kw)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, 'Popen', spawn)
    started = time.monotonic()
    result = supervise_dummy(**args, mode=mode)
    elapsed = time.monotonic() - started
    assert elapsed < args['policy'].overall_timeout_seconds + 0.75
    assert len(children) == 1 and result.child_pid == children[0].pid
    assert result.ready
    assert result.returncode == code
    assert (result.stop_requested, result.kill_requested) == (stop, kill)
    assert result.outcome == ('exited' if mode == 'normal' else 'aborted')
    assert result.reasons == (() if mode == 'normal' else ('run_deadline',))
    assert_reaped(result)


@pytest.mark.parametrize('mode', ['cooperate', 'ignore_stop'])
def test_disappearing_telemetry(args, mode):
    result = supervise_dummy(**args, mode=mode, telemetry='missing_when_ready')
    assert result.ready and result.outcome == 'aborted'
    assert result.reasons == ('telemetry_missing',)
    assert result.stop_requested
    assert result.kill_requested == (mode == 'ignore_stop')
    assert_reaped(result)


def test_denied_never_spawns(args, monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError('Must not launch')

    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    result = supervise_dummy(**args, mode='normal', telemetry='missing_at_admission')
    assert result.outcome == 'denied' and result.child_pid is None
    assert result.reasons == ('telemetry_missing',)


@pytest.mark.parametrize(
    'change',
    [
        {'mode': 'arbitrary-command'},
        {'telemetry': 'invalid'},
        {'policy': None},
    ],
)
def test_invalid_no_launch(args, change, monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError('Must not launch')

    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    with pytest.raises(ValueError):
        supervise_dummy(**(args | {'mode': 'normal'} | change))


def test_live_no_launch(args, monkeypatch):
    args['context'] = args['context'].model_copy(update={'mode': 'live'})
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: pytest.fail('Must not launch'))
    with pytest.raises(ValueError):
        supervise_dummy(**args, mode='normal')


def test_exit_between_poll_and_signal():
    class ExitingChild:
        def poll(self):
            return None

        def send_signal(self, sig):
            assert sig == signal.SIGTERM
            raise ProcessLookupError

    assert not _signal_owned(ExitingChild(), signal.SIGTERM)


def test_already_exited_no_signal():
    class ExitedChild:
        def poll(self):
            return 0

        def send_signal(self, sig):
            pytest.fail('Exited child must not receive signal')

    assert not _signal_owned(ExitedChild(), signal.SIGKILL)


def test_unrelated_child_untouched(args):
    import sys

    other = subprocess.Popen([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(10)'])
    try:
        result = supervise_dummy(**args, mode='ignore_stop')
        assert other.poll() is None
        assert other.pid != result.child_pid
        assert_reaped(result)
    finally:
        other.kill()
        other.wait(timeout=2)


def test_failed_reap_reports_unknown_with_bounded_wait(args, monkeypatch):
    read_fd, write_fd = os.pipe()
    os.write(write_fd, b'R')
    os.close(write_fd)
    signals = []
    waits = []

    class UnreapableChild:
        pid = 123
        stdout = os.fdopen(read_fd, 'rb')

        def poll(self):
            return None

        def send_signal(self, sig):
            signals.append(sig)

        def wait(self, timeout):
            waits.append(timeout)
            raise subprocess.TimeoutExpired('dummy', timeout)

    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **kw: UnreapableChild())
    args['policy'] = args['policy'].model_copy(
        update={
            'overall_timeout_seconds': 0.06,
            'cleanup_reserve_seconds': 0.02,
            'reap_allowance_seconds': 0.02,
        }
    )
    started = time.monotonic()
    result = supervise_dummy(**args, mode='ignore_stop')
    assert time.monotonic() - started < 0.5
    assert result.outcome == 'needs_manual_cleanup'
    assert result.worker_status == 'unknown' and result.returncode is None
    assert result.job_status == result.compute_status == 'unknown'
    assert signals == [signal.SIGTERM, signal.SIGKILL]
    assert len(waits) == 1 and waits[0] == 0
    assert UnreapableChild.stdout.closed


def test_parent_setup_error_reaps_child(args, monkeypatch):
    real_spawn = subprocess.Popen
    children = []

    def spawn(*a, **kw):
        child = real_spawn(*a, **kw)
        children.append(child)
        return child

    def fail_setup(*a):
        raise OSError('injected setup failure')

    monkeypatch.setattr(subprocess, 'Popen', spawn)
    monkeypatch.setattr(os, 'set_blocking', fail_setup)
    with pytest.raises(OSError, match='injected setup failure'):
        supervise_dummy(**args, mode='ignore_stop')
    assert len(children) == 1 and children[0].returncode is not None
    with pytest.raises(ChildProcessError):
        os.waitpid(children[0].pid, os.WNOHANG)
