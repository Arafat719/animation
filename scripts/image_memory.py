"""Scalar-only CPU decode diagnostics; no tensor copies or retained model roots."""

import weakref
from contextlib import contextmanager
from pathlib import Path


def memory_sample():
    fields = {
        'VmRSS': 'rss_bytes',
        'VmHWM': 'hwm_bytes',
        'RssAnon': 'anon_bytes',
        'RssFile': 'file_bytes',
    }
    result = {value: None for value in fields.values()}
    try:
        lines = Path('/proc/self/status').read_text().splitlines()
    except OSError:
        return result
    for line in lines:
        key, _, value = line.partition(':')
        if key in fields:
            result[fields[key]] = int(value.split()[0]) * 1024
    return result


def watch_model(module):
    tensors = list(module.parameters()) + list(module.buffers())
    # References track tensor objects, not the lifetime of every underlying storage.
    return weakref.ref(module), [(weakref.ref(t), t.numel() * t.element_size()) for t in tensors]


def model_sample(watch):
    root, tensors = watch
    live = [size for ref, size in tensors if ref() is not None]
    return {
        'root_alive': root() is not None,
        'live_tensor_count': len(live),
        'live_tensor_bytes': sum(live),
    }


@contextmanager
def decode_memory(vae, record):
    """Bracket decoder and leaf operations to locate growth without changing outputs."""
    handles = []

    def hook(name, suffix):
        def observe(module, args, *output):
            record('vae_' + suffix, module_name=name)

        return observe

    try:
        for name, module in vae.named_modules():
            if name == 'decoder' or (
                name.startswith(('decoder.', 'post_quant_conv')) and not list(module.children())
            ):
                handles.append(module.register_forward_pre_hook(hook(name, 'enter')))
                handles.append(module.register_forward_hook(hook(name, 'exit')))
        yield
    finally:
        for handle in handles:
            handle.remove()


def probe_decode_only(snapshot, record):
    """Existing real F32 VAE, zero latents; isolation diagnostic, not image acceptance."""
    import torch
    from accelerate import init_empty_weights
    from diffusers import AutoencoderKL

    from scripts.image_stream_load import load_f32_component

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    record('loading_vae_only')
    with init_empty_weights(include_buffers=False):
        vae = AutoencoderKL.from_config(AutoencoderKL.load_config(str(snapshot / 'vae')))
    load_f32_component(
        vae, snapshot / 'vae/diffusion_pytorch_model.safetensors', dtype=torch.float32
    )
    record('vae_inventory', module_name='vae', **model_sample(watch_model(vae)))
    with torch.inference_mode():
        latents = torch.zeros((1, 4, 64, 64), dtype=torch.float32)
        record('decoding', latent_bytes=latents.numel() * latents.element_size())
        with decode_memory(vae, record):
            decoded = vae.decode(latents, return_dict=False)[0]
        record('decode_returned')
        if tuple(decoded.shape) != (1, 3, 512, 512) or not torch.isfinite(decoded).all():
            raise ValueError('Invalid isolated decode output')
        del decoded, latents
        record('decode_outputs_released')
    record('synthetic_complete')
