"""Tensor-at-a-time loader for the inventoried F32 safetensors components.

No checkpoint conversion on disk. Read one tensor with pread, avoiding retained
whole-file mappings while destination weights accumulate. Opening can still
require transient virtual address space for the checkpoint.
"""

from pathlib import Path


def checkpoint_keys(model, source_keys):
    """Map only the exact legacy CLIPTextModel prefix migration, bijectively."""
    names = set(model.state_dict())
    if set(source_keys) == names:
        return {name: name for name in names}
    from transformers import CLIPTextModel

    # Installed Transformers' CLIPTextModel conversion removes `text_model`.
    # Projection models keep that prefix and must never use this migration.
    if type(model) is CLIPTextModel and set(source_keys) == {'text_model.' + n for n in names}:
        return {name: 'text_model.' + name for name in names}
    raise ValueError('Checkpoint/model keys differ')


def load_f32_component(model, checkpoint: Path, *, dtype):
    """Validate the full key/shape/dtype contract before allocating any weights.

    Accepts only non-shared meta parameters/persistent buffers, all from F32
    safetensors. Nonpersistent buffers must already be materialized on CPU.
    Destination tensors are owned copies, never views into checkpoint mappings.
    """
    import torch
    from accelerate.utils import set_module_tensor_to_device
    from safetensors import safe_open

    if dtype not in (torch.float16, torch.float32):
        raise ValueError('Only FP16/F32 destinations are supported')
    state = model.state_dict()
    if any(t.device.type != 'meta' for t in state.values()):
        raise ValueError('Expected an empty meta model')
    parameters = list(model.named_parameters(remove_duplicate=False))
    buffers = list(model.named_buffers(remove_duplicate=False))
    ids = [id(t) for _, t in parameters + buffers]
    if len(ids) != len(set(ids)):
        raise ValueError('Shared tensors are unsupported')
    if any(t.device.type != 'cpu' for name, t in buffers if name not in state):
        raise ValueError('Nonpersistent buffers must already be on CPU')
    with safe_open(str(checkpoint), framework='pt', device='cpu', backend='pread') as source:
        key_map = checkpoint_keys(model, source.keys())
        for name, expected in state.items():
            tensor_slice = source.get_slice(key_map[name])
            if tensor_slice.get_dtype() != 'F32' or tuple(tensor_slice.get_shape()) != tuple(
                expected.shape
            ):
                raise ValueError('Checkpoint tensor dtype/shape differs')
    # Do not retain a checkpoint mapping or a full source state_dict.
    for name in state:
        with safe_open(str(checkpoint), framework='pt', device='cpu', backend='pread') as source:
            original = source.get_tensor(key_map[name])
            value = original.to(device='cpu', dtype=dtype, copy=True)
            del original
        set_module_tensor_to_device(model, name, 'cpu', value=value, dtype=dtype)
        del value
    if any(t.device.type != 'cpu' for t in model.parameters()) or any(
        t.device.type != 'cpu' for t in model.buffers()
    ):
        raise ValueError('Model still contains non-CPU tensors')
    model.eval()
    return model


def load_sdxl_components(snapshot: Path, record):
    """Build configs on meta and load only the four existing local components."""
    import torch
    from accelerate import init_empty_weights
    from diffusers import AutoencoderKL, UNet2DConditionModel
    from transformers import CLIPTextConfig, CLIPTextModel, CLIPTextModelWithProjection

    result = {}
    for name, cls, filename, dtype in (
        ('vae', AutoencoderKL, 'diffusion_pytorch_model.safetensors', torch.float32),
        ('unet', UNet2DConditionModel, 'diffusion_pytorch_model.safetensors', torch.float16),
        ('text_encoder', CLIPTextModel, 'model.safetensors', torch.float16),
        ('text_encoder_2', CLIPTextModelWithProjection, 'model.safetensors', torch.float16),
    ):
        record('loading_' + name)
        config_path = snapshot / name
        # Keep nonpersistent position buffers on CPU; parameters stay on meta.
        with init_empty_weights(include_buffers=False):
            if name.startswith('text_encoder'):
                config = CLIPTextConfig.from_pretrained(str(config_path), local_files_only=True)
                model = cls(config)
            else:
                config = cls.load_config(str(config_path), local_files_only=True)
                model = cls.from_config(config)
        result[name] = load_f32_component(model, config_path / filename, dtype=dtype)
    return result
