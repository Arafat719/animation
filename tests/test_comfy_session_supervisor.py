import json
import os
import signal
import socket
import subprocess
import sys
import time
from threading import Event, Thread
from uuid import uuid4

import pytest
from test_comfy_http import graph as graph_fixture

from animation_studio.providers import comfy_session_supervisor as module
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_journal import _fingerprint
from animation_studio.providers.comfy_session_child import fixture_session
from animation_studio.providers.comfy_session_supervisor import (
    FixtureLaunch,
    supervise_offline_session,
)
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy
from animation_studio.providers.image import ImageProviderError

graph = graph_fixture


@pytest.fixture(autouse=True)
def guards(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('No parent network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    previous = signal.signal(
        signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Test watchdog'))
    )
    signal.alarm(15)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous)


@pytest.fixture
def options(tmp_path, graph):
    tmp_path.chmod(0o700)
    context = ComfyExecutionContext(
        mode='mock',
        job_id=str(uuid4()),
        graph_sha256=_fingerprint(graph),
        origin='https://fixture.invalid:443/',
        deployment_id=str(uuid4()),
        runtime_manifest_sha256='a' * 64,
        model_manifest_sha256='b' * 64,
    )
    policy = ComfySupervisionPolicy(
        ram_limit_bytes=512 * 1024 * 1024,
        host_reserve_bytes=1,
        device_index=0,
        vram_limit_bytes=512 * 1024 * 1024,
        sample_interval_seconds=0.01,
        stale_after_seconds=5.0,
        overall_timeout_seconds=4.5,
        cleanup_reserve_seconds=0.75,
        reap_allowance_seconds=0.75,
    )
    return {'root': tmp_path, 'context': context, 'graph': graph, 'policy': policy}


def calls(root):
    return [
        json.loads(line)
        for path in root.glob('*.requests.jsonl')
        for line in path.read_bytes().splitlines()
    ]


def assert_reaped(result):
    assert result.returncode is not None
    with pytest.raises(ChildProcessError):
        os.waitpid(result.child_pid, os.WNOHANG)


def test_normal_fixture_and_unrelated_child(options):
    sentinel = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    try:
        result = supervise_offline_session(**options)
        assert result.outcome == 'fixture_verified' and result.is_mock, result
        assert result.telemetry_source == 'synthetic'
        assert result.compute_status == result.job_status == result.storage_status == 'unknown'
        assert result.terminal.outcome == 'fixture_verified'
        assert result.cleanup is None and not result.kill_requested
        assert sentinel.poll() is None
        assert_reaped(result)
        assert sum(path == '/prompt' for _, path in calls(options['root'])) == 1
        assert len(list((options['root'] / 'fixture-images').glob('*.png'))) == 1
    finally:
        sentinel.kill()
        sentinel.wait(timeout=2)


@pytest.mark.parametrize(
    'scenario,state',
    [
        ('startup_hang', None),
        ('inventory_hang', None),
        ('history_hang', 'accepted'),
        ('intent_hang', 'intent'),
        ('cancel_hang', 'accepted'),
    ],
)
def test_hung_child_bounded_exit_and_explicit_recovery(options, scenario, state):
    start = time.monotonic()
    result = supervise_offline_session(**options, scenario=scenario)
    elapsed = time.monotonic() - start
    assert 3.5 <= elapsed < 6.0  # 3.75s cleanup deadline plus scheduling tolerance.
    assert result.outcome == 'aborted' and result.stop_requested and result.kill_requested
    assert result.returncode == -signal.SIGKILL
    assert_reaped(result)
    root, context = options['root'], options['context']
    journal = root / f'{context.job_id}.json'
    if state is None:
        assert not journal.exists()
        return
    assert json.loads(journal.read_bytes())['state'] == state
    saved = {p.name: p.read_bytes() for p in root.glob('*.json')}
    before = calls(root)
    if scenario == 'cancel_hang':
        sidecar = json.loads((root / f'{context.job_id}.supervision.json').read_bytes())
        assert sidecar['cleanup_phase'] == 'intent' and sidecar['attempt_count'] == 1
        assert sum(path.endswith('/cancel') for _, path in before) == 1
    else:
        assert not any(path.endswith('/cancel') for _, path in before)
    launch = FixtureLaunch(
        **{**options, 'root': str(root)},
        start=time.monotonic(),
        session_id=str(uuid4()),
        scenario='normal',
    )
    with fixture_session(launch, Event()) as session:
        with pytest.raises(ImageProviderError, match='Journal exists'):
            session.execute(options['graph'])
        if state == 'intent':
            with pytest.raises(ImageProviderError, match='outcome unknown'):
                session.recover(options['graph'])
        else:
            assert session.recover(options['graph']).startswith(b'\x89PNG')
    assert {p.name: p.read_bytes() for p in root.glob('*.json')} == saved
    after = calls(root)
    assert sum(path == '/prompt' for _, path in after) == sum(
        path == '/prompt' for _, path in before
    )
    assert sum(path.endswith('/cancel') for _, path in after) == sum(
        path.endswith('/cancel') for _, path in before
    )


def test_caller_cancel_after_receipt_is_child_owned_once(options):
    cancel, done = Event(), Event()
    journal = options['root'] / f'{options["context"].job_id}.json'

    def watch():
        while not done.wait(0.01):
            if journal.exists() and json.loads(journal.read_bytes())['state'] == 'accepted':
                cancel.set()
                return

    watcher = Thread(target=watch)
    watcher.start()
    try:
        result = supervise_offline_session(**options, scenario='cooperate', cancel=cancel)
    finally:
        done.set()
        watcher.join(timeout=1)
    assert not watcher.is_alive()
    assert result.reason == 'cancelled' and not result.kill_requested
    assert_reaped(result)
    assert sum(path.endswith('/cancel') for _, path in calls(options['root'])) == 1


@pytest.mark.parametrize(
    'mode', ['malformed', 'oversize', 'identity', 'duplicate', 'eof', 'partial']
)
def test_terminal_protocol_rejects_bad_frames(options, monkeypatch, mode):
    script = """
import json, sys
x=json.loads(sys.stdin.buffer.readline())
m={'session_id':x['session_id'],'job_id':x['context']['job_id'],'outcome':'fixture_verified','code':None}
mode=sys.argv[1]
if mode=='identity': m['session_id']='wrong'
b=json.dumps(m).encode()+b'\\n'
b={'malformed':b'bad\\n','oversize':b'x'*65537,'duplicate':b+b,'eof':b'','partial':b[:-1]}.get(mode,b)
sys.stdout.buffer.write(b); sys.stdout.buffer.flush()
"""
    children = []

    def spawn():
        child = subprocess.Popen(
            [sys.executable, '-c', script, mode],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        children.append(child)
        return child

    monkeypatch.setattr(module, '_spawn', spawn)
    try:
        result = supervise_offline_session(**options)
        assert result.outcome == 'aborted' and result.reason == 'invalid_terminal'
        assert_reaped(result)
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=2)


@pytest.mark.parametrize('failure', [RuntimeError('private-parent'), KeyboardInterrupt()])
def test_parent_exception_retains_primary_and_cleaned_child(options, monkeypatch, failure):
    original = module._spawn
    children = []

    def spawn():
        child = original()
        children.append(child)
        poll = child.poll
        count = 0

        def once():
            nonlocal count
            count += 1
            if count == 1:
                raise failure
            return poll()

        child.poll = once
        return child

    monkeypatch.setattr(module, '_spawn', spawn)
    try:
        with pytest.raises(type(failure)) as caught:
            supervise_offline_session(**options)
        assert caught.value is failure
        cleanup = failure.session_child_cleanup
        assert cleanup.child is children[0] and cleanup.child.poll() is not None
        assert 'private-parent' not in repr(cleanup)
        assert children[0].stdin.closed and children[0].stdout.closed
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=2)


@pytest.mark.parametrize('kind', ['scenario', 'context', 'root', 'cancel', 'oversize'])
def test_invalid_launch_never_spawns(options, monkeypatch, kind):
    def forbidden():
        pytest.fail('Invalid request must not spawn')

    monkeypatch.setattr(module, '_spawn', forbidden)
    if kind == 'scenario':
        options['scenario'] = 'arbitrary-command'
    elif kind == 'context':
        options['context'] = options['context'].model_copy(update={'mode': 'live'})
    elif kind == 'root':
        options['root'].chmod(0o755)
    elif kind == 'cancel':
        options['cancel'] = Event()
        options['cancel'].set()
    else:
        monkeypatch.setattr(module, 'MAX_IPC_BYTES', 1)
    with pytest.raises((ValueError, ImageProviderError)):
        supervise_offline_session(**options)
    assert not list(options['root'].iterdir())


@pytest.mark.parametrize('failure', ['kill', 'reap', 'close', 'unknown'])
def test_cleanup_failures_preserve_handles_and_other_actions(options, monkeypatch, failure):
    original = module._spawn
    children = []
    restore = []
    primary = RuntimeError('primary-private')

    def spawn():
        child = original()
        children.append(child)
        poll, send, wait, close = child.poll, child.send_signal, child.wait, child.stdin.close
        restore.append((poll, send, wait, close))
        count = 0

        def interrupted():
            nonlocal count
            count += 1
            if count == 1:
                raise primary
            if failure == 'unknown':
                return None
            return poll()

        child.poll = interrupted

        def broken(*args, **kwargs):
            raise OSError('private-cleanup')

        if failure == 'kill':
            child.send_signal = broken
        elif failure == 'reap':
            child.wait = broken
        elif failure == 'close':
            child.stdin.close = broken
        else:
            child.send_signal = lambda *args: None

            def timed_out(*args, **kwargs):
                raise subprocess.TimeoutExpired('fixture', 0)

            child.wait = timed_out
        return child

    monkeypatch.setattr(module, '_spawn', spawn)
    try:
        with pytest.raises(RuntimeError) as caught:
            supervise_offline_session(**options)
        assert caught.value is primary
        cleanup = primary.session_child_cleanup
        assert cleanup.child is children[0]
        assert 'private' not in repr(cleanup)
        assert children[0].stdout.closed
        if failure != 'close':
            assert children[0].stdin.closed
        if failure != 'unknown':
            assert any(failure in label for label in cleanup.error_codes)
    finally:
        for child, (poll, send, wait, close) in zip(children, restore, strict=True):
            child.poll, child.send_signal, child.wait, child.stdin.close = poll, send, wait, close
            if poll() is None:
                send(signal.SIGKILL)
            wait(timeout=2)
            close()


def test_startup_delay_does_not_reset_parent_or_child_clock(options, monkeypatch):
    spawn, write = module._spawn, os.write
    captured = []
    birth = []

    def delayed():
        time.sleep(0.2)
        birth.append(time.monotonic())
        return spawn()

    def observe(fd, data):
        if data.startswith(b'{'):
            captured.append(json.loads(data.split(b'\n')[0]))
        return write(fd, data)

    monkeypatch.setattr(module, '_spawn', delayed)
    monkeypatch.setattr(module.os, 'write', observe)
    result = supervise_offline_session(**options)
    assert result.outcome == 'fixture_verified', result
    assert captured[0]['start'] < birth[0] - 0.19
    assert captured[0]['session_id'] == result.session_id
    assert_reaped(result)


def test_unconfirmed_exit_returns_retained_cleanup_without_success(options, monkeypatch):
    original = module._spawn
    children, restore = [], []

    def spawn():
        child = original()
        children.append(child)
        restore.append((child.poll, child.send_signal, child.wait))
        child.poll = lambda: None
        child.send_signal = lambda *args: None

        def unknown(*args, **kwargs):
            raise subprocess.TimeoutExpired('fixture', 0)

        child.wait = unknown
        return child

    monkeypatch.setattr(module, '_spawn', spawn)
    try:
        result = supervise_offline_session(**options)
        assert result.outcome == 'needs_manual_cleanup' and result.returncode is None
        assert result.cleanup.child is children[0]
        assert result.terminal.outcome == 'fixture_verified'
        assert children[0].stdin.closed and children[0].stdout.closed
    finally:
        for child, methods in zip(children, restore, strict=True):
            child.poll, child.send_signal, child.wait = methods
            if child.poll() is None:
                child.kill()
            child.wait(timeout=2)


@pytest.mark.parametrize('data', [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'])
def test_strict_protocol_json(data):
    with pytest.raises(ValueError):
        module.decode_message(data)


@pytest.mark.parametrize('failure', ['ram', 'reserve', 'pid', 'ticks', 'stale', 'invalid'])
def test_ram_bootstrap_rejection_has_no_startup_or_journal(options, monkeypatch, failure):
    from dataclasses import replace

    from animation_studio.providers.comfy_ram_telemetry import LocalRamReading

    def reading(reader):
        data = LocalRamReading('ok', reader._pid, time.monotonic(), 10, 100, 1000)
        changes = {
            'ram': {'rss_bytes': options['policy'].ram_limit_bytes},
            'reserve': {'available_ram_bytes': options['policy'].host_reserve_bytes},
            'pid': {'pid': reader._pid + 1},
            'ticks': {'start_ticks': -1},
            'stale': {'sampled_at': 0.0},
            'invalid': {'rss_bytes': True},
        }
        return replace(data, **changes[failure])

    monkeypatch.setattr(module.OwnedChildRamReader, 'read', reading)
    result = supervise_offline_session(**options)
    assert result.outcome == 'aborted' and result.ram_reasons and not result.ram_admitted
    assert not list(options['root'].iterdir())
    assert result.sampler_status == 'stopped'
    assert_reaped(result)


def test_real_ram_evidence_is_separate_from_mock_inference(options):
    result = supervise_offline_session(**options)
    assert result.outcome == 'fixture_verified' and result.ram_admitted
    assert result.ram_source == 'local_procfs' and result.ram_coverage == 'direct_child'
    assert result.rss_bytes is not None and result.available_ram_bytes is not None
    assert result.sample_sequence > 0 and result.sampler_status == 'stopped'
    assert result.telemetry_source == 'synthetic' and result.is_mock
    assert result.vram_status == 'unknown'


@pytest.mark.parametrize('stage', ['bootstrap', 'accepted'])
def test_blocked_sampler_retained_without_blocking_child_cleanup(options, monkeypatch, stage):
    release = Event()
    entered = Event()
    original = module.OwnedChildRamReader.read
    journal = options['root'] / f'{options["context"].job_id}.json'
    options['policy'] = options['policy'].model_copy(update={'stale_after_seconds': 0.3})

    def read(reader):
        if stage == 'bootstrap' or (
            journal.exists() and json.loads(journal.read_bytes())['state'] == 'accepted'
        ):
            entered.set()
            release.wait(10)
        return original(reader)

    monkeypatch.setattr(module.OwnedChildRamReader, 'read', read)
    result = None
    try:
        result = supervise_offline_session(**options, scenario='cooperate')
        assert entered.is_set() and result.outcome == 'needs_manual_cleanup'
        assert result.cleanup.sampler is not None and result.sampler_status == 'unknown'
        assert_reaped(result)
        if stage == 'bootstrap':
            assert not journal.exists() and not calls(options['root'])
        else:
            assert json.loads(journal.read_bytes())['state'] == 'accepted'
            assert sum(path.endswith('/cancel') for _, path in calls(options['root'])) <= 1
    finally:
        release.set()
        if result is not None and result.cleanup is not None:
            assert result.cleanup.sampler.close(deadline=time.monotonic() + 2).status == 'stopped'


@pytest.mark.parametrize('failure', ['ram', 'reader_error', 'ticks'])
def test_running_ram_failure_stops_once_preserves_accepted_journal(options, monkeypatch, failure):
    from dataclasses import replace

    original = module.OwnedChildRamReader.read
    journal = options['root'] / f'{options["context"].job_id}.json'

    def read(reader):
        value = original(reader)
        if (
            value.status == 'ok'
            and journal.exists()
            and json.loads(journal.read_bytes())['state'] == 'accepted'
        ):
            if failure == 'reader_error':
                raise RuntimeError('private-reader')
            return replace(
                value,
                **(
                    {'rss_bytes': options['policy'].ram_limit_bytes}
                    if failure == 'ram'
                    else {'start_ticks': value.start_ticks + 1}
                ),
            )
        return value

    monkeypatch.setattr(module.OwnedChildRamReader, 'read', read)
    result = supervise_offline_session(**options, scenario='cooperate')
    assert result.outcome == 'aborted' and result.ram_reasons
    assert 'private' not in repr(result)
    assert json.loads(journal.read_bytes())['state'] == 'accepted'
    assert sum(path.endswith('/cancel') for _, path in calls(options['root'])) == 1
    assert_reaped(result)


def test_partial_startup_cancel_never_finishes_payload(options, monkeypatch):
    original = os.write
    cancel = Event()
    written = []

    def partial(fd, data):
        written.append(data[:1])
        result = original(fd, data[:1])
        cancel.set()
        return result

    monkeypatch.setattr(module.os, 'write', partial)
    result = supervise_offline_session(**options, cancel=cancel)
    assert result.reason == 'cancelled' and written == [b'{']
    assert not list(options['root'].iterdir())
    assert_reaped(result)


@pytest.mark.parametrize('failure', ['reader', 'unavailable', 'invalid', 'identity_mismatch'])
def test_bootstrap_reader_failure_never_dispatches(options, monkeypatch, failure):
    from animation_studio.providers.comfy_ram_telemetry import LocalRamReading

    def read(reader):
        if failure == 'reader':
            raise OSError('private-reader')
        return LocalRamReading(failure, reader._pid, time.monotonic())

    monkeypatch.setattr(module.OwnedChildRamReader, 'read', read)
    result = supervise_offline_session(**options)
    assert result.outcome == 'aborted' and not result.ram_admitted
    assert not list(options['root'].iterdir())
    assert 'private-reader' not in repr(result)
    assert_reaped(result)


def test_cancel_before_first_sample_discards_payload(options, monkeypatch):
    cancel, release = Event(), Event()
    original = module.OwnedChildRamReader.read

    def read(reader):
        cancel.set()
        release.wait(10)
        return original(reader)

    monkeypatch.setattr(module.OwnedChildRamReader, 'read', read)
    result = None
    try:
        result = supervise_offline_session(**options, cancel=cancel)
        assert result.reason == 'cancelled' and not result.ram_admitted
        assert result.outcome == 'needs_manual_cleanup'
        assert not list(options['root'].iterdir())
        assert_reaped(result)
    finally:
        release.set()
        if result is not None:
            assert result.cleanup.sampler.close(deadline=time.monotonic() + 2).status == 'stopped'


@pytest.mark.parametrize('failure', ['snapshot', 'close'])
def test_sampler_exception_preserves_ownership_and_pipe_cleanup(options, monkeypatch, failure):
    original = module.RamSampler.close
    primary = RuntimeError('private-sampler')

    def broken(*args, **kwargs):
        raise primary

    monkeypatch.setattr(module.RamSampler, failure, broken)
    try:
        with pytest.raises(RuntimeError) as caught:
            supervise_offline_session(**options)
        assert caught.value is primary
        cleanup = caught.value.session_child_cleanup
        assert cleanup.sampler is not None
        assert cleanup.child.poll() is not None
        assert cleanup.child.stdin.closed and cleanup.child.stdout.closed
        assert 'private-sampler' not in repr(cleanup)
    finally:
        monkeypatch.undo()
        if hasattr(primary, 'session_child_cleanup'):
            assert (
                original(
                    primary.session_child_cleanup.sampler, deadline=time.monotonic() + 2
                ).status
                == 'stopped'
            )
