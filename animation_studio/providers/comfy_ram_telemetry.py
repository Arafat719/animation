"""Bounded Linux RAM reads for one owned direct child; no GPU or tree claims."""

import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

MAX_PROC_BYTES = 65536


@dataclass(frozen=True)
class LocalRamReading:
    status: Literal['ok', 'unavailable', 'invalid', 'identity_mismatch', 'exited']
    pid: int
    sampled_at: float
    start_ticks: int | None = None
    rss_bytes: int | None = None
    available_ram_bytes: int | None = None
    source: Literal['local_procfs'] = 'local_procfs'
    coverage: Literal['direct_child'] = 'direct_child'
    vram_bytes: None = None


def _read(path: Path) -> bytes:
    with path.open('rb') as stream:
        data = stream.read(MAX_PROC_BYTES + 1)
    if len(data) > MAX_PROC_BYTES:
        raise ValueError('Oversized proc record')
    return data


def _stat(data: bytes) -> tuple[int, int, int, bytes]:
    # comm may contain spaces, newlines and parentheses; fields follow the last ')'.
    head, separator, tail = data.rpartition(b') ')
    if not separator:
        raise ValueError('Invalid stat')
    pid, separator, _ = head.partition(b' (')
    fields = tail.split()
    if (
        not separator
        or len(fields) < 20
        or fields[0] not in (b'R', b'S', b'D', b'Z', b'T', b't', b'X', b'x', b'K', b'W', b'P', b'I')
    ):
        raise ValueError('Invalid stat')
    values = (pid, fields[1], fields[19])
    if any(not re.fullmatch(rb'[0-9]{1,20}', value) for value in values):
        raise ValueError('Invalid identity')
    return int(pid), int(fields[1]), int(fields[19]), fields[0]


def _kib(data: bytes, key: bytes) -> int:
    lines = [line for line in data.splitlines() if line.split(b':', 1)[0].strip() == key]
    if len(lines) != 1:
        raise ValueError('Missing or duplicate memory field')
    match = re.fullmatch(re.escape(key) + rb':[ \t]+([0-9]{1,20})[ \t]+kB[ \t]*', lines[0])
    if match is None:
        raise ValueError('Invalid memory field')
    return int(match[1]) * 1024


class OwnedChildRamReader:
    """Retain a Popen handle and pin its start ticks on the first valid reading.

    Reads /proc only. Does not signal, wait, spawn or fabricate unavailable values.
    Popen.poll observes/reaps exit. OS read latency is not a hard wall-clock bound.
    """

    def __init__(self, child: subprocess.Popen):
        if not sys.platform.startswith('linux'):
            raise ValueError('Linux procfs required')
        if type(child) is not subprocess.Popen or type(child.pid) is not int or child.pid <= 0:
            raise ValueError('Expected owned Popen child')
        self._child = child
        self._pid = child.pid
        self._parent = os.getpid()
        self._start_ticks = None

    def read(self) -> LocalRamReading:
        sampled_at = time.monotonic()

        def failure(status):
            return LocalRamReading(status, self._pid, sampled_at)

        if os.getpid() != self._parent or self._child.pid != self._pid:
            return failure('identity_mismatch')
        if self._child.poll() is not None:
            return failure('exited')
        base = Path('/proc') / str(self._pid)
        try:
            before = _stat(_read(base / 'stat'))
            rss = _kib(_read(base / 'status'), b'VmRSS')
            available = _kib(_read(Path('/proc/meminfo')), b'MemAvailable')
            after = _stat(_read(base / 'stat'))
        except OSError:
            return failure('unavailable')
        except ValueError:
            return failure('invalid')
        if (
            self._child.poll() is not None
            or before[3] in (b'Z', b'X', b'x')
            or after[3] in (b'Z', b'X', b'x')
        ):
            return failure('exited')
        if (
            before[:3] != after[:3]
            or before[:2] != (self._pid, self._parent)
            or (self._start_ticks is not None and before[2] != self._start_ticks)
        ):
            return failure('identity_mismatch')
        self._start_ticks = before[2]
        return LocalRamReading('ok', self._pid, sampled_at, before[2], rss, available)
