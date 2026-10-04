import json
import subprocess
import sys

import pytest

from scripts import image_operator_probe as probe


@pytest.mark.parametrize('failure', [False, True])
def test_suite_bounds_order_and_fail_stop(tmp_path, monkeypatch, failure):
    calls = []

    def run(output, *, mode, limits):
        calls.append(mode)
        assert limits.seconds <= 20
        assert limits.rss_bytes == limits.reserve_bytes == 2 * probe.GIB
        assert limits.address_bytes == 8 * probe.GIB
        return {'outcome': 'failed' if failure else 'synthetic_pass'}

    monkeypatch.setattr(probe, 'run_probe', run)
    result = probe.run_suite(tmp_path / 'run')
    assert len(calls) == (1 if failure else 6)
    assert result['outcome'] == ('failed' if failure else 'passed')
    assert json.loads((tmp_path / 'run/summary.json').read_text()) == result
    with pytest.raises(FileExistsError):
        probe.run_suite(tmp_path / 'run')


def test_suite_aggregate_deadline(tmp_path, monkeypatch):
    ticks = iter([0, 121, 122])
    monkeypatch.setattr(probe.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(probe, 'run_probe', lambda *a, **kw: pytest.fail('must not launch'))
    result = probe.run_suite(tmp_path / 'run')
    assert result['outcome'] == 'failed' and result['results'] == []


@pytest.mark.parametrize('operator', ['conv', 'linear'])
def test_small_numerical_case(operator):
    code = f"""
from scripts.image_operator_probe import measure
stages = []
def record(stage, **values):
    stages.append((stage, values))
measure({operator!r}, 'float16', record, small=True)
assert stages[-1][0] == 'synthetic_complete'
result = stages[-1][1]
assert len(result['samples']) == 3
assert result['relative_l2_error'] < 0.01
assert all(s['wall_seconds'] >= 0 and s['cpu_seconds'] >= 0 for s in result['samples'])
"""
    subprocess.run([sys.executable, '-c', code], check=True, timeout=20)


def test_mixed_suite_stops_without_retry(tmp_path, monkeypatch):
    calls = []

    def run(output, *, mode, limits):
        calls.append(mode)
        assert limits.seconds <= 20 and limits.rss_bytes == 2 * probe.GIB
        return {'outcome': 'synthetic_pass' if len(calls) == 1 else 'failed'}

    monkeypatch.setattr(probe, 'run_probe', run)
    result = probe.run_suite(tmp_path / 'mixed', mixed=True)
    assert calls == ['operator:conv:float32', 'operator:conv_mixed:float16']
    assert result['outcome'] == 'failed'


def test_mixed_preserves_storage_and_matches_explicit_reference():
    import torch
    from torch.nn import functional

    generator = torch.Generator().manual_seed(42)
    x = torch.randn((1, 4, 6, 6), generator=generator).half()
    w = torch.randn((4, 4, 3, 3), generator=generator).half()
    original_x, original_w = x.clone(), w.clone()
    pointers = (x.data_ptr(), w.data_ptr())
    with torch.inference_mode():
        result = probe.mixed_conv(x, w)
        expected = functional.conv2d(x.float(), w.float(), padding=1).half()
    assert result.dtype == torch.float16 and torch.isfinite(result).all()
    assert torch.equal(result, expected)
    assert torch.equal(x, original_x) and torch.equal(w, original_w)
    assert pointers == (x.data_ptr(), w.data_ptr())
    with pytest.raises(ValueError):
        probe.mixed_conv(x.float(), w)
