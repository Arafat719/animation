import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from scripts import image_split_probe as split


@pytest.fixture(autouse=True)
def no_real_gpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)


def test_real_latent_roundtrip_and_tamper(tmp_path):
    latents = torch.arange(4 * 64 * 64, dtype=torch.float32).reshape(1, 4, 64, 64).half()
    split.save_latents(latents, tmp_path, '/local')
    result, metadata = split.load_latents(tmp_path, '/local')
    assert torch.equal(latents, result)
    assert metadata['seed'] == 42
    with pytest.raises(FileExistsError):
        split.save_latents(latents, tmp_path, '/local')
    with pytest.raises(ValueError, match='provenance'):
        split.load_latents(tmp_path, '/different')
    path = tmp_path / 'latents.npy'
    path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='provenance'):
        split.load_latents(tmp_path, '/local')


@pytest.mark.parametrize('bad', ['shape', 'dtype', 'nan'])
def test_invalid_saved_array_rejected(tmp_path, bad):
    split.save_latents(torch.ones(1, 4, 64, 64).half(), tmp_path, '/local')
    array = np.zeros((1, 4, 64, 64), dtype=np.float16)
    if bad == 'shape':
        array = array[:, :, :1]
    elif bad == 'dtype':
        array = array.astype(np.float32)
    else:
        array[0, 0, 0, 0] = np.nan
    path = tmp_path / 'latents.npy'
    np.save(path, array, allow_pickle=False)
    metadata = json.loads((tmp_path / 'latents.json').read_text())
    metadata['latent_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path / 'latents.json').write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match='array'):
        split.load_latents(tmp_path, '/local')


@pytest.mark.parametrize('success', [True, False])
@pytest.mark.parametrize('policy', ['cpu', 'cuda'])
def test_decode_only_after_successful_generation_reap(tmp_path, monkeypatch, success, policy):
    calls = []
    monkeypatch.setattr(split, 'available_memory', lambda: 12 * split.GIB)
    monkeypatch.setattr(
        split.shutil, 'disk_usage', lambda path: SimpleNamespace(free=split.GIB * 2)
    )
    monkeypatch.setattr(split, 'verify_artifact', lambda path: 'verified')

    def probe(path, *, mode, address_policy='cpu'):
        assert address_policy == policy
        calls.append(mode)
        if mode == 'latent-only':
            return {
                'outcome': 'latents_saved' if success else 'failed',
                'returncode': 0 if success else -24,
                'pid': 999999999,
            }
        assert calls == ['latent-only', 'decode-real']
        return {'outcome': 'image_saved', 'returncode': 0}

    monkeypatch.setattr(split, 'run_probe', probe)
    report = split.experiment(tmp_path / 'experiment', address_policy=policy)
    assert calls == (['latent-only', 'decode-real'] if success else ['latent-only'])
    assert report['outcome'] == ('image_saved' if success else 'failed')


@pytest.mark.parametrize('cuda_enabled', [False, True])
def test_decode_real_scales_latents_and_verifies_image(tmp_path, monkeypatch, cuda_enabled):
    from contextlib import nullcontext

    import accelerate
    import diffusers

    from scripts import image_stream_load

    generation = tmp_path / 'generation'
    generation.mkdir()
    output = tmp_path / 'decode'
    output.mkdir()
    split.save_latents(torch.ones(1, 4, 64, 64).half(), generation, '/local')

    class VAE(torch.nn.Module):
        config = SimpleNamespace(latents_mean=None, latents_std=None, scaling_factor=0.5)

        @staticmethod
        def load_config(path):
            return {}

        @staticmethod
        def from_config(config):
            return VAE()

        def decode(self, latents, return_dict):
            assert not torch.is_grad_enabled() and latents.dtype == torch.float32
            assert torch.all(latents == 2) and not return_dict
            return (torch.zeros((1, 3, 512, 512)),)

    monkeypatch.setattr(diffusers, 'AutoencoderKL', VAE)
    monkeypatch.setattr(accelerate, 'init_empty_weights', lambda **kw: nullcontext())
    monkeypatch.setattr(image_stream_load, 'load_f32_component', lambda model, *a, **kw: model)
    monkeypatch.setattr(torch, 'set_num_threads', lambda n: None)
    monkeypatch.setattr(torch, 'set_num_interop_threads', lambda n: None)
    transfers = []
    if cuda_enabled:
        monkeypatch.setattr(torch.cuda, 'is_available', lambda: True)
        monkeypatch.setattr(VAE, 'to', lambda self, device: transfers.append(('vae', device)))
        original_to = torch.Tensor.to

        def tensor_to(tensor, *args, **kwargs):
            if kwargs.get('device') == 'cuda':
                transfers.append(('latents', kwargs['device'], kwargs['dtype']))
                kwargs['device'] = 'cpu'
            return original_to(tensor, *args, **kwargs)

        monkeypatch.setattr(torch.Tensor, 'to', tensor_to)
    events = []
    split.decode_real(split.Path('/local'), output, lambda stage, **kw: events.append(stage))
    assert events[-1] == 'image_saved'
    assert split.verify_artifact(output)
    metadata = json.loads((output / 'metadata.json').read_text())
    assert metadata['device'] == ('cuda' if cuda_enabled else 'cpu')
    assert transfers == (
        [('vae', 'cuda'), ('latents', 'cuda', torch.float32)] if cuda_enabled else []
    )
