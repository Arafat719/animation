"""Small real safetensors only; never load the SDXL checkpoint."""

import pytest
import torch
from accelerate import init_empty_weights
from safetensors.torch import save_file

from scripts.image_stream_load import load_f32_component


def test_loader_avoids_checkpoint_mappings(tmp_path, monkeypatch):
    """Check actual mappings during header validation and tensor reads."""
    from pathlib import Path

    import safetensors

    path = tmp_path / 'weights.safetensors'
    save_file(torch.nn.Linear(8, 4).state_dict(), str(path))
    real_open = safetensors.safe_open
    opened = []

    class CheckedOpen:
        def __init__(self, *args, **kwargs):
            self.inner = real_open(*args, **kwargs)

        def __enter__(self):
            self.source = self.inner.__enter__()
            assert str(path) not in Path('/proc/self/maps').read_text()
            opened.append(True)
            return self

        def __exit__(self, *args):
            return self.inner.__exit__(*args)

        def keys(self):
            return self.source.keys()

        def get_slice(self, name):
            return self.source.get_slice(name)

        def get_tensor(self, name):
            value = self.source.get_tensor(name)
            assert str(path) not in Path('/proc/self/maps').read_text()
            return value

    monkeypatch.setattr(safetensors, 'safe_open', CheckedOpen)
    with init_empty_weights():
        model = torch.nn.Linear(8, 4)
    load_f32_component(model, path, dtype=torch.float16)
    assert len(opened) == 3  # Header validation, bias, weight.


@pytest.mark.parametrize('dtype', [torch.float16, torch.float32])
def test_values_output_and_owned_storage(tmp_path, dtype):
    torch.manual_seed(42)
    original = torch.nn.Linear(8, 4)
    path = tmp_path / 'weights.safetensors'
    save_file(original.state_dict(), str(path))
    before = path.read_bytes()
    with init_empty_weights():
        target = torch.nn.Linear(8, 4)
    load_f32_component(target, path, dtype=dtype)
    assert not target.training
    for key, value in target.state_dict().items():
        assert value.dtype == dtype
        assert torch.equal(value, original.state_dict()[key].to(dtype))
    x = torch.ones(1, 8, dtype=dtype)
    assert torch.allclose(target(x), original.to(dtype)(x))
    with torch.no_grad():
        target.weight.add_(1)
    assert path.read_bytes() == before


@pytest.mark.parametrize('bad', ['missing', 'extra', 'shape', 'dtype', 'corrupt'])
def test_invalid_checkpoint_before_materialization(tmp_path, bad):
    source = torch.nn.Linear(8, 4).state_dict()
    if bad == 'missing':
        del source['bias']
    elif bad == 'extra':
        source['extra'] = torch.ones(1)
    elif bad == 'shape':
        source['bias'] = torch.ones(5)
    elif bad == 'dtype':
        source['bias'] = source['bias'].half()
    path = tmp_path / 'weights.safetensors'
    save_file(source, str(path))
    if bad == 'corrupt':
        path.write_bytes(b'bad')
    with init_empty_weights():
        model = torch.nn.Linear(8, 4)
    from safetensors import SafetensorError

    with pytest.raises((ValueError, SafetensorError)):
        load_f32_component(model, path, dtype=torch.float16)
    assert all(p.device.type == 'meta' for p in model.parameters())


def test_non_meta_model_rejected(tmp_path):
    with pytest.raises(ValueError, match='meta'):
        load_f32_component(torch.nn.Linear(2, 2), tmp_path / 'absent', dtype=torch.float16)


def test_shared_weights_rejected(tmp_path):
    with init_empty_weights():
        model = torch.nn.Module()
        model.a = torch.nn.Linear(2, 2)
    model.b = model.a
    with pytest.raises(ValueError, match='Shared'):
        load_f32_component(model, tmp_path / 'absent', dtype=torch.float16)


def test_small_real_component_configs(tmp_path):
    from diffusers import AutoencoderKL, UNet2DConditionModel
    from transformers import CLIPTextConfig, CLIPTextModel, CLIPTextModelWithProjection

    from scripts.image_stream_load import load_sdxl_components

    config = CLIPTextConfig(
        hidden_size=8,
        intermediate_size=16,
        num_hidden_layers=1,
        num_attention_heads=2,
        vocab_size=16,
        max_position_embeddings=8,
        projection_dim=8,
    )
    models = {
        'vae': AutoencoderKL(
            block_out_channels=(8,),
            norm_num_groups=4,
            down_block_types=('DownEncoderBlock2D',),
            up_block_types=('UpDecoderBlock2D',),
        ),
        'unet': UNet2DConditionModel(
            block_out_channels=(8,),
            norm_num_groups=4,
            down_block_types=('CrossAttnDownBlock2D',),
            up_block_types=('CrossAttnUpBlock2D',),
            cross_attention_dim=8,
            attention_head_dim=2,
        ),
        'text_encoder': CLIPTextModel(config),
        'text_encoder_2': CLIPTextModelWithProjection(config),
    }
    for name, model in models.items():
        model.save_pretrained(tmp_path / name, safe_serialization=True)
    stages = []
    loaded = load_sdxl_components(tmp_path, stages.append)
    assert stages == [
        'loading_vae',
        'loading_unet',
        'loading_text_encoder',
        'loading_text_encoder_2',
    ]
    for name, model in loaded.items():
        dtype = torch.float32 if name == 'vae' else torch.float16
        for key, tensor in model.state_dict().items():
            assert torch.equal(tensor, models[name].state_dict()[key].to(dtype))
        assert all(b.device.type == 'cpu' for b in model.buffers())


@pytest.mark.parametrize('dtype', [torch.float16, torch.float32])
def test_legacy_clip_prefix_values_and_forward(tmp_path, dtype):
    from transformers import CLIPTextConfig, CLIPTextModel

    config = CLIPTextConfig(
        hidden_size=8,
        intermediate_size=16,
        num_hidden_layers=1,
        num_attention_heads=2,
        vocab_size=16,
        max_position_embeddings=8,
    )
    original = CLIPTextModel(config).eval()
    path = tmp_path / 'legacy.safetensors'
    save_file({'text_model.' + k: v for k, v in original.state_dict().items()}, str(path))
    before = path.read_bytes()
    with init_empty_weights(include_buffers=False):
        target = CLIPTextModel(config)
    load_f32_component(target, path, dtype=dtype)
    for key, value in target.state_dict().items():
        assert torch.equal(value, original.state_dict()[key].to(dtype))
    original.to(dtype)
    inputs = torch.tensor([[1, 2, 3]])
    with torch.no_grad():
        assert torch.equal(target(inputs).last_hidden_state, original(inputs).last_hidden_state)
    assert path.read_bytes() == before


@pytest.mark.parametrize('bad', ['missing', 'extra', 'mixed', 'shape', 'dtype'])
def test_legacy_clip_invalid_rejected_before_loading(tmp_path, bad):
    from transformers import CLIPTextConfig, CLIPTextModel

    config = CLIPTextConfig(
        hidden_size=8,
        intermediate_size=16,
        num_hidden_layers=1,
        num_attention_heads=2,
        vocab_size=16,
        max_position_embeddings=8,
    )
    values = {'text_model.' + k: v for k, v in CLIPTextModel(config).state_dict().items()}
    key = next(iter(values))
    if bad == 'missing':
        del values[key]
    elif bad == 'extra':
        values['unexpected'] = torch.ones(1)
    elif bad == 'mixed':
        values[key.removeprefix('text_model.')] = values.pop(key)
    elif bad == 'shape':
        values[key] = torch.ones(1)
    elif bad == 'dtype':
        values[key] = values[key].half()
    path = tmp_path / 'invalid.safetensors'
    save_file(values, str(path))
    with init_empty_weights(include_buffers=False):
        model = CLIPTextModel(config)
    with pytest.raises(ValueError):
        load_f32_component(model, path, dtype=torch.float16)
    assert all(p.device.type == 'meta' for p in model.parameters())


def test_prefix_migration_rejects_non_clip_model(tmp_path):
    path = tmp_path / 'linear.safetensors'
    save_file(
        {'text_model.' + k: v for k, v in torch.nn.Linear(2, 2).state_dict().items()}, str(path)
    )
    with init_empty_weights():
        model = torch.nn.Linear(2, 2)
    with pytest.raises(ValueError, match='keys differ'):
        load_f32_component(model, path, dtype=torch.float16)
