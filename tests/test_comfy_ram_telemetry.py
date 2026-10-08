import builtins
import io
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from animation_studio.providers import comfy_ram_telemetry as telemetry


@pytest.fixture
def child():
    process = subprocess.Popen(
        [sys.executable, '-I', '-S', '-c', 'import time; time.sleep(30)'],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        yield process
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)


def stat(pid, parent, ticks=123, state='S'):
    fields = [state, str(parent)] + ['0'] * 17 + [str(ticks)]
    return f'{pid} (a tricky ) name\n) {" ".join(fields)}\n'.encode()


@pytest.fixture
def fixture_reader(child, monkeypatch):
    reader = telemetry.OwnedChildRamReader(child)
    records = {
        'stat': stat(child.pid, os.getpid()),
        'status': b'Name: fixture\nVmRSS:\t12 kB\n',
        'meminfo': b'MemAvailable: 345 kB\n',
    }
    monkeypatch.setattr(telemetry, '_read', lambda path: records[path.name])
    return reader, records


def assert_unknown(reading, status):
    assert reading.status == status
    assert reading.rss_bytes is reading.available_ram_bytes is reading.start_ticks is None
    assert reading.vram_bytes is None


def test_units_provenance_and_no_network_gpu(fixture_reader, monkeypatch):
    reader, _ = fixture_reader
    original = builtins.__import__

    def no_gpu(name, *a, **kw):
        assert name.split('.')[0] not in ('torch', 'torchvision', 'comfy_kitchen')
        return original(name, *a, **kw)

    def forbidden(*a, **kw):
        pytest.fail('No network or process launch')

    with monkeypatch.context() as patch:
        patch.setattr(builtins, '__import__', no_gpu)
        patch.setattr(socket, 'socket', forbidden)
        patch.setattr(socket, 'getaddrinfo', forbidden)
        patch.setattr(subprocess, 'Popen', forbidden)
        before = time.monotonic()
        result = reader.read()
        assert before <= result.sampled_at <= time.monotonic()
    assert result.status == 'ok'
    assert (result.rss_bytes, result.available_ram_bytes) == (12 * 1024, 345 * 1024)
    assert result.start_ticks == 123
    assert result.coverage == 'direct_child' and result.source == 'local_procfs'
    assert result.vram_bytes is None


@pytest.mark.parametrize(
    'content',
    [
        b'',
        b'VmRSS: -1 kB',
        b'VmRSS: 1 MB',
        b'VmRSS: 1.5 kB',
        b'VmRSS: 1 kB\nVmRSS: 2 kB',
        b'VmRSS: 1 kB\n VmRSS: 2 kB',
        b'VmRSS: x kB',
    ],
)
def test_invalid_rss(fixture_reader, content):
    reader, records = fixture_reader
    records['status'] = content
    assert_unknown(reader.read(), 'invalid')


@pytest.mark.parametrize(
    'content',
    [
        b'',
        b'MemAvailable: 1 kB\nMemAvailable: 2 kB',
        b'MemAvailable: -1 kB',
        b'MemAvailable: 4 bytes',
    ],
)
def test_invalid_host_memory(fixture_reader, content):
    reader, records = fixture_reader
    records['meminfo'] = content
    assert_unknown(reader.read(), 'invalid')


@pytest.mark.parametrize('error', [FileNotFoundError, PermissionError, OSError])
def test_read_errors(child, monkeypatch, error):
    reader = telemetry.OwnedChildRamReader(child)

    def failed(path):
        raise error('fixture')

    monkeypatch.setattr(telemetry, '_read', failed)
    assert_unknown(reader.read(), 'unavailable')


def test_pid_reuse_across_samples(fixture_reader, child):
    reader, records = fixture_reader
    assert reader.read().status == 'ok'
    records['stat'] = stat(child.pid, os.getpid(), ticks=124)
    assert_unknown(reader.read(), 'identity_mismatch')


@pytest.mark.parametrize('kind', ['pid', 'parent', 'ticks', 'exit'])
def test_read_race(child, monkeypatch, kind):
    reader = telemetry.OwnedChildRamReader(child)
    calls = 0

    def read(path):
        nonlocal calls
        if path.name == 'stat':
            calls += 1
            if calls == 2:
                return stat(
                    child.pid + (kind == 'pid'),
                    os.getpid() + (kind == 'parent'),
                    ticks=124 if kind == 'ticks' else 123,
                    state='Z' if kind == 'exit' else 'S',
                )
            return stat(child.pid, os.getpid())
        return b'VmRSS: 1 kB' if path.name == 'status' else b'MemAvailable: 1 kB'

    monkeypatch.setattr(telemetry, '_read', read)
    assert_unknown(reader.read(), 'exited' if kind == 'exit' else 'identity_mismatch')


def test_bounded_read(monkeypatch):
    requests = []

    class RecordingStream(io.BytesIO):
        def read(self, size=-1):
            requests.append(size)
            return super().read(size)

    monkeypatch.setattr(Path, 'open', lambda *a, **kw: RecordingStream(b'x' * 70000))
    with pytest.raises(ValueError, match='Oversized'):
        telemetry._read(Path('/fixture'))
    assert requests == [telemetry.MAX_PROC_BYTES + 1]


def test_actual_owned_child_and_exit(child):
    reader = telemetry.OwnedChildRamReader(child)
    reading = reader.read()
    assert reading.status == 'ok'
    assert reading.pid == child.pid and reading.start_ticks > 0
    assert reading.rss_bytes >= 0 and reading.available_ram_bytes > 0
    child.terminate()
    child.wait(timeout=2)
    assert_unknown(reader.read(), 'exited')


@pytest.mark.parametrize('bad', [None, 123, '123'])
def test_requires_child_handle(bad):
    with pytest.raises(ValueError):
        telemetry.OwnedChildRamReader(bad)


@pytest.mark.parametrize(
    'data', [b'', b'123 no_comm', b'123 (name) S 1', b'bad (name) ' + b'0 ' * 30]
)
def test_malformed_stat(fixture_reader, data):
    reader, records = fixture_reader
    records['stat'] = data
    assert_unknown(reader.read(), 'invalid')


def test_valid_zero_is_distinct_from_missing(fixture_reader):
    reader, records = fixture_reader
    records['status'] = b'VmRSS: 0 kB'
    records['meminfo'] = b'MemAvailable: 0 kB'
    reading = reader.read()
    assert reading.status == 'ok' and reading.rss_bytes == reading.available_ram_bytes == 0


def test_child_exits_during_read(child, monkeypatch):
    reader = telemetry.OwnedChildRamReader(child)

    def read(path):
        if path.name == 'stat':
            return stat(child.pid, os.getpid())
        if path.name == 'status':
            child.kill()
            child.wait(timeout=2)
            return b'VmRSS: 1 kB'
        return b'MemAvailable: 20 kB'

    monkeypatch.setattr(telemetry, '_read', read)
    assert_unknown(reader.read(), 'exited')


@pytest.mark.parametrize('failed_read', [1, 2, 3, 4])
def test_disappearance_at_each_read(child, monkeypatch, failed_read):
    reader = telemetry.OwnedChildRamReader(child)
    calls = 0

    def read(path):
        nonlocal calls
        calls += 1
        if calls == failed_read:
            raise FileNotFoundError
        if path.name == 'stat':
            return stat(child.pid, os.getpid())
        return b'VmRSS: 1 kB' if path.name == 'status' else b'MemAvailable: 2 kB'

    monkeypatch.setattr(telemetry, '_read', read)
    assert_unknown(reader.read(), 'unavailable')
    assert calls == failed_read


def test_exact_size_allowed(monkeypatch):
    data = b'x' * telemetry.MAX_PROC_BYTES
    monkeypatch.setattr(Path, 'open', lambda *a, **kw: io.BytesIO(data))
    assert telemetry._read(Path('/fixture')) == data


def test_other_parent_rejected(fixture_reader, child):
    reader, records = fixture_reader
    records['stat'] = stat(child.pid, os.getpid() + 1)
    assert_unknown(reader.read(), 'identity_mismatch')
