import json
import resource
import subprocess
import sys

import pytest

from scripts.image_load_probe import GIB, apply_address_policy, run_probe, validate_address_policy


@pytest.mark.parametrize('policy', ['cpu', 'cuda'])
def test_address_policy_virtual_reservation_in_disposable_process(policy):
    code = """
import mmap, resource, sys
from scripts.image_load_probe import apply_address_policy, GIB
policy = sys.argv[1]
apply_address_policy(policy, 24 * GIB)
expected = (24 * GIB, 24 * GIB) if policy == 'cpu' else (-1, -1)
assert resource.getrlimit(resource.RLIMIT_AS) == expected
try:
    reservation = mmap.mmap(-1, 32 * GIB, flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS, prot=0)
except (OSError, MemoryError):
    assert policy == 'cpu'
else:
    assert policy == 'cuda'
    reservation.close()
"""
    subprocess.run([sys.executable, '-c', code, policy], check=True, timeout=10)


@pytest.mark.parametrize('inherited', [(24 * GIB, 24 * GIB), (24 * GIB, -1)])
def test_cuda_does_not_override_inherited_cap(monkeypatch, inherited):
    calls = []
    monkeypatch.setattr(resource, 'getrlimit', lambda kind: inherited)
    monkeypatch.setattr(resource, 'setrlimit', lambda *args: calls.append(args))
    with pytest.raises(RuntimeError, match='inherited RLIMIT_AS'):
        apply_address_policy('cuda', 24 * GIB)
    assert calls == []


@pytest.mark.parametrize('mode', ['load', 'decode-only', 'synthetic-ok', 'operator:conv:float16'])
def test_cpu_only_modes_cannot_drop_as_guard(mode):
    with pytest.raises(ValueError, match='inference modes'):
        validate_address_policy(mode, 'cuda')


def test_invalid_policy_rejected_before_output(tmp_path):
    with pytest.raises(ValueError, match='Unknown address'):
        run_probe(tmp_path / 'unused', mode='infer', address_policy='automatic')
    assert not (tmp_path / 'unused').exists()


@pytest.mark.parametrize('available', [True, False])
def test_cuda_child_policy_before_runtime_and_other_guards_intact(tmp_path, available):
    code = """
import json, resource, signal, sys, types
from pathlib import Path
from scripts.image_load_probe import child_probe, GIB
from scripts.image_device import select_device
available = sys.argv[2] == 'True'
root = Path(sys.argv[1])
sys.modules['torch'] = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda:available))
def decode(snapshot, output, record):
    assert available
    assert resource.getrlimit(resource.RLIMIT_AS) == (-1,-1)
    assert resource.getrlimit(resource.RLIMIT_CPU) == (5,6)
    assert resource.getrlimit(resource.RLIMIT_CORE) == (0,0)
    assert signal.getitimer(signal.ITIMER_REAL)[0] > 0
    try:
        sys.audit('socket.connect', None, None)
    except RuntimeError:
        pass
    else:
        raise AssertionError('offline guard absent')
    record('image_saved')
sys.modules['scripts.image_split_probe'] = types.SimpleNamespace(decode_real=decode)
status = child_probe('decode-real', root/'stage.json', 5, 24*GIB, 'cuda')
evidence=json.loads((root/'stage.json').read_text())
assert status == (0 if available else 1)
assert evidence['stage'] == ('image_saved' if available else 'error')
if not available:
    assert 'requires an available CUDA' in evidence['error_message']
# Once this process uses CUDA policy it must never silently run unguarded CPU inference.
available=False
try:
    select_device()
except RuntimeError:
    pass
else:
    raise AssertionError('unexpected CPU fallback')
"""
    subprocess.run(
        [sys.executable, '-c', code, str(tmp_path), str(available)], check=True, timeout=10
    )
    events = [json.loads(line) for line in (tmp_path / 'events.jsonl').read_text().splitlines()]
    assert events[1]['address_policy'] == 'cuda'


@pytest.mark.parametrize('failure', ['rss_limit', 'host_memory'])
def test_parent_memory_guards_remain_active_for_cuda(tmp_path, monkeypatch, failure):
    from scripts import image_load_probe as probe

    class Child:
        pid = 999999999
        returncode = None

        def poll(self):
            return self.returncode

        def kill(self):
            self.returncode = -9

        def wait(self):
            return self.returncode

    child = Child()

    def spawn(command, **kwargs):
        index = command.index('--address-policy')
        assert command[index + 1] == 'cuda'
        return child

    values = iter([12 * GIB, 1 if failure == 'host_memory' else 12 * GIB])
    monkeypatch.setattr(probe, 'available_memory', lambda: next(values))
    monkeypatch.setattr(
        probe, 'resident_memory', lambda pid: 9 * GIB if failure == 'rss_limit' else GIB
    )
    monkeypatch.setattr(probe.subprocess, 'Popen', spawn)
    result = run_probe(tmp_path / 'run', mode='infer', address_policy='cuda')
    assert result['reason'] == failure
    assert result['returncode'] == -9
    assert result['address_policy'] == 'cuda'
