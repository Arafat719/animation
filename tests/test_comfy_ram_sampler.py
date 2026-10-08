import threading
import time
from dataclasses import FrozenInstanceError

import pytest

from animation_studio.providers.comfy_ram_sampler import RamSampler
from animation_studio.providers.comfy_ram_telemetry import LocalRamReading, OwnedChildRamReader


def reader_with(read):
    reader = object.__new__(OwnedChildRamReader)
    reader.read = read
    return reader


def wait_for(predicate):
    deadline = time.monotonic() + 2
    while not predicate():
        assert time.monotonic() < deadline, 'Sampler condition timed out'
        threading.Event().wait(0.001)


def test_serial_latest_slot_and_preserved_time():
    entered, release = threading.Event(), threading.Event()
    calls = 0

    def read():
        nonlocal calls
        calls += 1
        if calls == 3:
            entered.set()
            assert release.wait(2)
        return LocalRamReading('ok', 123, float(calls), 456, calls, 100)

    sampler = RamSampler(reader_with(read), interval_seconds=0.001)
    try:
        assert sampler.snapshot().status == 'not_started'
        sampler.start()
        assert entered.wait(2)
        snapshot = sampler.snapshot()
        assert snapshot.sequence == 2 and snapshot.latest.rss_bytes == 2
        assert snapshot.latest.sampled_at == 2
        assert calls == 3
        for _ in range(20):
            assert sampler.snapshot() == snapshot
        with pytest.raises(FrozenInstanceError):
            snapshot.sequence = 4
        stopped = sampler.close(deadline=time.monotonic() + 0.02)
        assert stopped.status == 'unknown' and stopped.sequence == 2
        with pytest.raises(RuntimeError):
            sampler.start()
    finally:
        release.set()
        assert sampler.close(deadline=time.monotonic() + 2).status == 'stopped'
    assert sampler.snapshot().sequence == 2 and calls == 3


def test_delayed_read_timestamp_not_refreshed():
    entered, release = threading.Event(), threading.Event()
    reading = LocalRamReading('ok', 123, 10.0, 456, 1, 100)

    def read():
        entered.set()
        assert release.wait(2)
        return reading

    sampler = RamSampler(reader_with(read), interval_seconds=10)
    try:
        sampler.start()
        assert entered.wait(2)
        assert sampler.snapshot().latest is None
        release.set()
        wait_for(lambda: sampler.snapshot().sequence == 1)
        assert sampler.snapshot().latest is reading
        assert sampler.snapshot().latest.sampled_at == 10
    finally:
        release.set()
        assert sampler.close(deadline=time.monotonic() + 2).status == 'stopped'


@pytest.mark.parametrize('deadline_delta', [-1, 0, 0.02])
def test_hung_read_close_bounded_no_late_publication(deadline_delta):
    entered, release = threading.Event(), threading.Event()

    def read():
        entered.set()
        assert release.wait(2)
        return LocalRamReading('ok', 123, 10, 456, 1, 100)

    sampler = RamSampler(reader_with(read), interval_seconds=0.01)
    try:
        sampler.start()
        assert entered.wait(2)
        start = time.monotonic()
        result = sampler.close(deadline=start + deadline_delta)
        assert time.monotonic() - start < 0.3
        assert result.status == 'unknown' and result.latest is None
        assert sampler._thread.daemon
    finally:
        release.set()
        result = sampler.close(deadline=time.monotonic() + 2)
        assert result.status == 'stopped' and result.sequence == 0
        assert not sampler._thread.is_alive()


@pytest.mark.parametrize('status', ['unavailable', 'invalid', 'identity_mismatch', 'exited'])
def test_failure_reading_published_once_no_retry(status):
    calls = 0

    def read():
        nonlocal calls
        calls += 1
        return LocalRamReading(status, 123, 10)

    sampler = RamSampler(reader_with(read), interval_seconds=0.001)
    try:
        sampler.start()
        wait_for(lambda: sampler.snapshot().status == 'stopped')
        result = sampler.snapshot()
        assert result.sequence == 1 and result.latest.status == status and calls == 1
        with pytest.raises(RuntimeError):
            sampler.start()
    finally:
        sampler.close(deadline=time.monotonic() + 2)


@pytest.mark.parametrize('bad_result', [True, False])
def test_reader_error_clears_previous_sample(bad_result):
    calls = 0

    def read():
        nonlocal calls
        calls += 1
        if calls == 1:
            return LocalRamReading('ok', 123, 10, 456, 1, 100)
        if bad_result:
            return None
        raise OSError('private detail must not escape')

    sampler = RamSampler(reader_with(read), interval_seconds=0.001)
    try:
        sampler.start()
        wait_for(lambda: sampler.snapshot().status == 'failed')
        result = sampler.snapshot()
        assert result.latest is None and result.sequence == 1 and calls == 2
        assert result.error_code == ('invalid_reading' if bad_result else 'reader_error')
        assert 'private detail' not in repr(result)
    finally:
        sampler.close(deadline=time.monotonic() + 2)


def test_stop_before_start_and_no_restart():
    sampler = RamSampler(reader_with(lambda: pytest.fail('Unexpected read')), interval_seconds=1)
    assert sampler.close(deadline=time.monotonic()).status == 'stopped'
    with pytest.raises(RuntimeError):
        sampler.start()


def test_stop_during_read_discards_late_exception():
    entered, release = threading.Event(), threading.Event()
    calls = 0

    def read():
        nonlocal calls
        calls += 1
        if calls == 1:
            return LocalRamReading('ok', 123, 10, 456, 1, 100)
        entered.set()
        assert release.wait(2)
        raise OSError('late private failure')

    sampler = RamSampler(reader_with(read), interval_seconds=0.001)
    try:
        sampler.start()
        assert entered.wait(2)
        before = sampler.snapshot()
        assert sampler.close(deadline=time.monotonic()).status == 'unknown'
    finally:
        release.set()
        result = sampler.close(deadline=time.monotonic() + 2)
    assert result.status == 'stopped' and result.error_code is None
    assert result.latest is before.latest and result.sequence == before.sequence == 1
    assert calls == 2


def test_stop_wakes_interval_wait_without_another_read():
    calls = 0

    def read():
        nonlocal calls
        calls += 1
        return LocalRamReading('ok', 123, 10, 456, 1, 100)

    sampler = RamSampler(reader_with(read), interval_seconds=3600)
    try:
        sampler.start()
        wait_for(lambda: sampler.snapshot().sequence == 1)
    finally:
        result = sampler.close(deadline=time.monotonic() + 1)
    assert result.status == 'stopped' and calls == 1


def test_start_failure_is_terminal(monkeypatch):
    sampler = RamSampler(reader_with(lambda: pytest.fail('Unexpected read')), interval_seconds=1)

    def fail(*a):
        raise RuntimeError('thread unavailable')

    monkeypatch.setattr(threading.Thread, 'start', fail)
    with pytest.raises(RuntimeError):
        sampler.start()
    assert sampler.snapshot().error_code == 'start_failed'
    assert sampler.close(deadline=time.monotonic()).status == 'failed'
    with pytest.raises(RuntimeError):
        sampler.start()


@pytest.mark.parametrize('interval', [True, 0, -1, '1', float('nan'), float('inf')])
def test_invalid_interval(interval):
    with pytest.raises(ValueError):
        RamSampler(reader_with(lambda: None), interval_seconds=interval)


def test_invalid_reader_and_deadline():
    with pytest.raises(ValueError):
        RamSampler(lambda: None, interval_seconds=1)
    sampler = RamSampler(reader_with(lambda: None), interval_seconds=1)
    with pytest.raises(ValueError):
        sampler.close(deadline=float('nan'))
    assert sampler.snapshot().status == 'not_started'
