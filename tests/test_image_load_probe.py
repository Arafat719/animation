import json
from pathlib import Path

import pytest

from scripts.image_load_probe import Limits, error_details, resident_memory, run_probe


@pytest.mark.parametrize('exited', [True, False])
def test_missing_rss_requires_confirmed_exit(tmp_path, monkeypatch, exited):
    """Reproduce R-without-VmRSS; a live child must still fail closed."""
    import subprocess

    class Child:
        pid = 123456
        returncode = None
        killed = False

        def __init__(self):
            self.waits = []

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            self.waits.append(timeout)
            if timeout is not None:
                if not exited:
                    raise subprocess.TimeoutExpired('synthetic', timeout)
                self.returncode = 1
            return self.returncode

        def kill(self):
            self.killed = True
            self.returncode = -9

    child = Child()
    original_read = Path.read_text

    def read(path, *args, **kwargs):
        if str(path) == f'/proc/{child.pid}/status':
            return 'State:\tR (running)\n'
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', read)
    monkeypatch.setattr('scripts.image_load_probe.subprocess.Popen', lambda *a, **k: child)
    monkeypatch.setattr('scripts.image_load_probe.available_memory', lambda: 10 * 1024**3)
    result = run_probe(tmp_path / 'probe', mode='synthetic-error')
    assert result['outcome'] == 'failed'
    assert result['reason'] == ('child_failed' if exited else 'monitor_error:ValueError')
    assert child.waits == [0.05, None]
    assert child.killed is not exited
    assert result['returncode'] == (1 if exited else -9)


@pytest.mark.parametrize(
    'status,expected',
    [('State:\tR (running)\nVmRSS:\t42 kB\n', 42 * 1024), ('State:\tZ (zombie)\n', 0)],
)
def test_rss_reading_preserved(monkeypatch, status, expected):
    monkeypatch.setattr(Path, 'read_text', lambda path: status)
    assert resident_memory(123456) == expected


def assert_reaped(result):
    assert result['returncode'] is not None
    assert not Path(f'/proc/{result["pid"]}').exists()


def test_synthetic_success_and_offline_guard(tmp_path):
    result = run_probe(tmp_path / 'probe', mode='synthetic-ok', limits=Limits(seconds=5))
    assert result['outcome'] == 'synthetic_pass'
    assert result['child_evidence']['network_blocked']
    assert result['child_evidence']['address_limit'] == 24 * 1024**3
    assert json.loads((tmp_path / 'probe/result.json').read_text()) == result
    assert_reaped(result)


@pytest.mark.parametrize(
    'mode,limits,reason',
    [
        ('synthetic-hang', Limits(seconds=0.4), 'timeout'),
        ('synthetic-rss', Limits(seconds=5, rss_bytes=32 * 1024**2), 'rss_limit'),
        ('synthetic-as', Limits(seconds=5, address_bytes=128 * 1024**2), 'child_failed'),
        ('synthetic-error', Limits(seconds=5), 'child_failed'),
    ],
)
def test_failures_reaped(tmp_path, mode, limits, reason):
    result = run_probe(tmp_path / 'probe', mode=mode, limits=limits)
    assert result['outcome'] == 'failed'
    assert result['reason'] == reason
    assert_reaped(result)
    if mode == 'synthetic-as':
        assert result['child_evidence']['error_type'] == 'MemoryError'
    if mode == 'synthetic-error':
        evidence = result['child_evidence']
        assert evidence['failed_stage'] == 'guarded'
        assert evidence['error_message'] == 'Injected child failure'
        assert evidence['traceback_frames'][-1]['function'] == 'child_probe'
        assert json.loads((tmp_path / 'probe/result.json').read_text()) == result


def test_diagnostics_bounded_without_locals():
    def fail(depth):
        if depth:
            fail(depth - 1)
        raise RuntimeError('x' * 10000)

    try:
        fail(30)
    except RuntimeError as error:
        details = error_details(error)
    assert details['error_message'] == 'x' * 2048
    assert len(details['traceback_frames']) == 12
    for frame in details['traceback_frames']:
        assert set(frame) == {'file', 'function', 'line'}
        assert len(frame['file']) <= 256 and len(frame['function']) <= 256


def test_host_reserve_prevents_spawn(tmp_path, monkeypatch):
    monkeypatch.setattr('scripts.image_load_probe.available_memory', lambda: 1)
    result = run_probe(tmp_path / 'probe', mode='synthetic-ok')
    assert result['reason'] == 'host_memory' and result['pid'] is None


def test_host_reserve_during_child(tmp_path, monkeypatch):
    values = iter([10 * 1024**3, 1])
    monkeypatch.setattr('scripts.image_load_probe.available_memory', lambda: next(values))
    result = run_probe(tmp_path / 'probe', mode='synthetic-hang')
    assert result['reason'] == 'host_memory'
    assert_reaped(result)


def test_monitor_error_reaps(tmp_path, monkeypatch):
    def unavailable(pid):
        raise OSError('Injected read failure')

    monkeypatch.setattr('scripts.image_load_probe.resident_memory', unavailable)
    result = run_probe(tmp_path / 'probe', mode='synthetic-hang')
    assert result['reason'] == 'monitor_error:OSError'
    assert_reaped(result)


def test_existing_output_preserved(tmp_path):
    marker = tmp_path / 'keep'
    marker.write_text('keep')
    with pytest.raises(FileExistsError):
        run_probe(tmp_path, mode='synthetic-ok')
    assert marker.read_text() == 'keep'


@pytest.mark.parametrize(
    'values',
    [
        {'seconds': 0},
        {'seconds': True},
        {'seconds': float('nan')},
        {'rss_bytes': -1},
        {'address_bytes': True},
        {'reserve_bytes': 0},
    ],
)
def test_invalid_limits(values):
    with pytest.raises(ValueError):
        Limits(**values)


@pytest.mark.parametrize('failure', [None, 'RuntimeError', 'TypeError'])
@pytest.mark.parametrize('mode', ['load', 'infer', 'infer-mixed'])
def test_load_path_with_stub_runtime(tmp_path, failure, mode):
    """Exercise real child orchestration without any torch import or weights."""
    import subprocess
    import sys

    code = r"""
import json, sys, types
from pathlib import Path
from scripts import image_load_probe as probe
root = Path(sys.argv[1])
(root / 'model_index.json').write_text('{}')
probe.SNAPSHOT = root
calls = []
class Module:
    def __init__(self, dtype):
        self.dtype = dtype
        self.device = types.SimpleNamespace(type='cpu')
class VAE:
    @staticmethod
    def from_pretrained(path, **kwargs):
        calls.append(('vae', kwargs))
        return Module('f32')
class Pipeline:
    @staticmethod
    def from_pretrained(path, **kwargs):
        calls.append(('pipeline', {k:v for k,v in kwargs.items() if k != 'vae'}))
        return types.SimpleNamespace(vae=kwargs['vae'], unet=Module('f16'),
            text_encoder=Module('f16'), text_encoder_2=Module('f16'))
sys.modules['torch'] = types.SimpleNamespace(float32='f32', float16='f16',
    set_num_threads=lambda n: None, set_num_interop_threads=lambda n: None)
sys.modules['diffusers'] = types.SimpleNamespace(StableDiffusionXLPipeline=Pipeline)
sys.modules['scripts.image_stream_load'] = types.SimpleNamespace(
    load_sdxl_components=lambda snapshot, record: {'vae': Module('f32'), 'unet': Module('f16'),
        'text_encoder': Module('f16'), 'text_encoder_2': Module('f16')})
status = probe.child_probe('load', root/'stage.json', 5, 1024**3)
assert status == 0
for name, kwargs in calls:
    assert kwargs['local_files_only'] is True
    assert kwargs['use_safetensors'] is True
    assert kwargs['low_cpu_mem_usage'] is True
assert calls[0][1]['torch_dtype'] == 'f16'
assert json.loads((root/'stage.json').read_text())['stage'] == 'loaded'
"""
    if mode in ('infer', 'infer-mixed'):
        expected_kwargs = (
            {'mixed_conv': True, 'diagnose_memory': True} if mode == 'infer-mixed' else {}
        )
        code = code.replace(
            "status = probe.child_probe('load'",
            'def fake_generate(pipe, output, snapshot, record, **kwargs):\n'
            + f'    assert kwargs == {expected_kwargs}\n'
            + '    assert output == root and snapshot == root\n'
            "    record('image_saved')\n"
            "sys.modules['scripts.image_inference'] = types.SimpleNamespace(\n"
            '    generate_image=fake_generate)\n'
            "status = probe.child_probe('infer'",
        ).replace("['stage'] == 'loaded'", "['stage'] == 'image_saved'")
    if failure:
        code = code.replace(
            'status = probe.child_probe',
            'def broken_loader(snapshot, record):\n'
            "    record('loading_unet')\n"
            f"    raise {failure}('Injected component failure')\n"
            "sys.modules['scripts.image_stream_load'].load_sdxl_components = broken_loader\n"
            'status = probe.child_probe',
        )
        code = (
            code[: code.index('assert status == 0')]
            + f"""
assert status == 1
evidence = json.loads((root/'stage.json').read_text())
assert evidence['stage'] == 'error'
assert evidence['failed_stage'] == 'loading_unet'
assert evidence['error_type'] == '{failure}'
assert evidence['error_message'] == 'Injected component failure'
assert evidence['traceback_frames'][-1]['function'] == 'broken_loader'
"""
        )
    if mode == 'infer-mixed':
        code = code.replace("child_probe('infer'", "child_probe('infer-mixed'")
    result = subprocess.run(
        [sys.executable, '-c', code, str(tmp_path)], timeout=10, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr.decode()


def test_stage_timing_history_bounded_and_payload_free(tmp_path):
    from scripts.image_load_probe import StageRecorder

    record = StageRecorder(tmp_path / 'stage.json')
    for index in range(record.MAX_EVENTS):
        record('stage', private_payload='not in event history')
    events = [json.loads(line) for line in record.events_path.read_text().splitlines()]
    assert len(events) == record.MAX_EVENTS
    for field in ('elapsed_seconds', 'cpu_seconds'):
        values = [event[field] for event in events]
        assert values == sorted(values) and values[0] >= 0
    assert all(
        set(event)
        == {
            'stage',
            'elapsed_seconds',
            'cpu_seconds',
            'rss_bytes',
            'hwm_bytes',
            'anon_bytes',
            'file_bytes',
        }
        for event in events
    )
    assert json.loads(record.stage_path.read_text())['private_payload'] == 'not in event history'
    before = record.events_path.read_bytes()
    with pytest.raises(ValueError, match='event limit'):
        record('overflow')
    assert record.events_path.read_bytes() == before
    with pytest.raises(FileExistsError):
        StageRecorder(tmp_path / 'stage.json')
    assert record.events_path.read_bytes() == before


def test_timeout_retains_timing_event(tmp_path):
    result = run_probe(tmp_path / 'probe', mode='synthetic-hang', limits=Limits(seconds=0.5))
    assert result['reason'] == 'timeout'
    events = [
        json.loads(line) for line in (tmp_path / 'probe/events.jsonl').read_text().splitlines()
    ]
    assert events[-1]['stage'] == 'guarded'
    assert events[-1]['elapsed_seconds'] >= 0
    assert_reaped(result)
