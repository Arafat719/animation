"""One-shot serialized RAM sampler. A stuck read never blocks parent polling."""

import threading
import time
from dataclasses import dataclass
from typing import Literal

from animation_studio.providers.comfy_ram_telemetry import LocalRamReading, OwnedChildRamReader
from animation_studio.providers.comfy_resource_guard import _time


@dataclass(frozen=True)
class RamSamplerSnapshot:
    status: Literal['not_started', 'running', 'unknown', 'stopped', 'failed']
    latest: LocalRamReading | None
    sequence: int
    error_code: Literal['reader_error', 'invalid_reading', 'start_failed'] | None


class RamSampler:
    """One reader, one daemon thread, one latest-value slot, no automatic restart.

    snapshot() does not wait on I/O. close() takes an absolute monotonic deadline;
    unknown means the read thread is still alive, not successful cleanup. The
    caller must retain this session and report needs_manual_cleanup while unknown;
    no forced thread kill. Read admission under the lock marks an in-flight read;
    stop prevents further admissions, not an already admitted call from completing.
    The reader's read-start timestamp is preserved for the CPU guard to validate.
    """

    def __init__(self, reader: OwnedChildRamReader, *, interval_seconds: float):
        if type(reader) is not OwnedChildRamReader:
            raise ValueError('Expected owned child RAM reader')
        interval = _time(interval_seconds)
        if interval <= 0:
            raise ValueError('Expected positive sample interval')
        self._reader = reader
        self._interval = interval
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._used = False
        self._latest = None
        self._sequence = 0
        self._error = None

    def start(self) -> None:
        with self._lock:
            if self._used:
                raise RuntimeError('Sampler session cannot restart')
            self._used = True
            self._thread = threading.Thread(target=self._run, daemon=True, name='comfy-ram-sampler')
            try:
                self._thread.start()
            except RuntimeError:
                self._thread = None
                self._error = 'start_failed'
                self._stop.set()
                raise

    def _run(self):
        while True:
            # Read admission and stop are serialized; no lock is held across I/O.
            with self._lock:
                if self._stop.is_set():
                    return
            try:
                reading = self._reader.read()
            except Exception:  # noqa: BLE001 — thread boundary reports a bounded failure code.
                # Do not expose arbitrary exception text or retain a stale success.
                with self._lock:
                    if self._stop.is_set():
                        return
                    self._latest = None
                    self._error = 'reader_error'
                return
            with self._lock:
                if self._stop.is_set():
                    return
                if type(reading) is not LocalRamReading:
                    self._latest = None
                    self._error = 'invalid_reading'
                    return
                self._latest = reading
                self._sequence += 1
                if reading.status != 'ok':
                    return
            if self._stop.wait(min(self._interval, threading.TIMEOUT_MAX)):
                return

    def snapshot(self) -> RamSamplerSnapshot:
        with self._lock:
            alive = self._thread is not None and self._thread.is_alive()
            if alive:
                status = 'unknown' if self._stop.is_set() else 'running'
            elif self._error is not None:
                status = 'failed'
            else:
                status = 'stopped' if self._used else 'not_started'
            return RamSamplerSnapshot(status, self._latest, self._sequence, self._error)

    def stop(self) -> None:
        with self._lock:
            self._used = True
            self._stop.set()

    def close(self, *, deadline: float) -> RamSamplerSnapshot:
        deadline = _time(deadline)
        self.stop()
        with self._lock:
            thread = self._thread
        if thread is not None:
            remaining = max(0.0, deadline - time.monotonic())
            thread.join(timeout=min(remaining, threading.TIMEOUT_MAX))
        return self.snapshot()
