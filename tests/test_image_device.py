import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest
import torch

from scripts.image_device import prepare_device, select_device
from scripts.image_load_probe import StageRecorder


@pytest.mark.parametrize('available,expected', [(False, 'cpu'), (True, 'cuda')])
def test_device_selection_and_dtype_preserving_transfer(monkeypatch, tmp_path, available, expected):
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: available)
    calls = []
    model = SimpleNamespace(to=lambda *args, **kw: calls.append((args, kw)))
    record = StageRecorder(tmp_path / 'stage.json')
    assert select_device() == expected
    assert prepare_device(model, record) == expected
    assert calls == ([(('cuda',), {})] if available else [])
    event = json.loads(record.events_path.read_text())
    assert event['device'] == expected


def test_cuda_transfer_failure_is_not_silent_cpu_fallback(monkeypatch):
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: True)

    def fail(device):
        raise RuntimeError('CUDA initialization failed')

    with pytest.raises(RuntimeError, match='CUDA initialization'):
        prepare_device(SimpleNamespace(to=fail), lambda *a, **kw: None)


def test_snapshot_override_is_local_and_inherited(tmp_path):
    result = subprocess.run(
        [sys.executable, '-c', 'from scripts.image_load_probe import SNAPSHOT; print(SNAPSHOT)'],
        env={**os.environ, 'SDXL_TURBO_SNAPSHOT': str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == str(tmp_path)
