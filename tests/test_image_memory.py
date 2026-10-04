import gc
import json
from types import SimpleNamespace

import pytest
import torch

from scripts.image_load_probe import StageRecorder
from scripts.image_memory import decode_memory, memory_sample, model_sample, watch_model


def test_weak_model_inventory_does_not_retain_weights():
    model = torch.nn.Linear(3, 2)
    watch = watch_model(model)
    assert model_sample(watch) == {
        'root_alive': True,
        'live_tensor_count': 2,
        'live_tensor_bytes': 32,
    }
    weight = model.weight
    del model
    gc.collect()
    assert model_sample(watch) == {
        'root_alive': False,
        'live_tensor_count': 1,
        'live_tensor_bytes': 24,
    }
    del weight
    assert model_sample(watch)['live_tensor_bytes'] == 0


@pytest.mark.parametrize('fail', [False, True])
def test_decode_hooks_persist_memory_and_cleanup(tmp_path, fail):
    class Leaf(torch.nn.Module):
        def forward(self, value):
            if fail:
                raise RuntimeError('decode failure')
            return value

    vae = torch.nn.Module()
    vae.decoder = torch.nn.Sequential(Leaf())
    record = StageRecorder(tmp_path / 'stage.json')
    value = torch.ones(1)
    try:
        with decode_memory(vae, record):
            assert vae.decoder(value) is value
    except RuntimeError:
        assert fail
    events = [json.loads(line) for line in record.events_path.read_text().splitlines()]
    assert events[0]['module_name'] == 'decoder'
    assert events[1]['module_name'] == 'decoder.0'
    assert events[-1]['stage'] == ('vae_enter' if fail else 'vae_exit')
    assert all(event['rss_bytes'] > 0 for event in events)
    for module in vae.modules():
        assert not module._forward_hooks and not module._forward_pre_hooks


def test_missing_proc_memory_is_unknown(monkeypatch):
    def missing(*args):
        raise FileNotFoundError

    monkeypatch.setattr('scripts.image_memory.Path.read_text', missing)
    assert all(value is None for value in memory_sample().values())


def test_scalar_allowlist_preserved_and_invalid_rejected(tmp_path):
    record = StageRecorder(tmp_path / 'stage.json')
    record(
        'model',
        module_name='vae',
        root_alive=True,
        live_tensor_count=1,
        live_tensor_bytes=4,
        latent_bytes=8,
        private_payload='excluded',
    )
    event = json.loads(record.events_path.read_text())
    assert event['live_tensor_bytes'] == 4 and event['root_alive'] is True
    assert 'private_payload' not in event
    with pytest.raises(ValueError, match='scalar'):
        record('bad', live_tensor_bytes=SimpleNamespace())


def test_minimal_decode_driver_uses_existing_vae_only(monkeypatch, tmp_path):
    from contextlib import nullcontext

    import accelerate
    import diffusers

    from scripts import image_stream_load
    from scripts.image_memory import probe_decode_only

    class VAE(torch.nn.Module):
        @staticmethod
        def load_config(path):
            assert path == str(tmp_path / 'vae')
            return {}

        @staticmethod
        def from_config(config):
            return VAE()

        def decode(self, latents, return_dict):
            assert tuple(latents.shape) == (1, 4, 64, 64)
            assert latents.dtype == torch.float32 and not latents.any()
            assert not return_dict and not torch.is_grad_enabled()
            return (torch.zeros((1, 3, 512, 512)),)

    def load(model, path, *, dtype):
        assert path == tmp_path / 'vae/diffusion_pytorch_model.safetensors'
        assert dtype == torch.float32
        return model

    monkeypatch.setattr(diffusers, 'AutoencoderKL', VAE)
    monkeypatch.setattr(accelerate, 'init_empty_weights', lambda **kw: nullcontext())
    monkeypatch.setattr(image_stream_load, 'load_f32_component', load)
    monkeypatch.setattr(torch, 'set_num_threads', lambda n: None)
    monkeypatch.setattr(torch, 'set_num_interop_threads', lambda n: None)
    events = []
    probe_decode_only(tmp_path, lambda stage, **kw: events.append(stage))
    assert events == [
        'loading_vae_only',
        'vae_inventory',
        'decoding',
        'decode_returned',
        'decode_outputs_released',
        'synthetic_complete',
    ]
