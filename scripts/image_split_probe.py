"""One-off experiment: reap SDXL before starting a fresh real-latent VAE child."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from scripts.image_inference import PROMPT, SEED, SIZE, save_pixels, verify_artifact
from scripts.image_load_probe import GIB, available_memory, run_probe
from scripts.image_memory import decode_memory, memory_sample, model_sample, watch_model


def save_latents(latents, output, snapshot, *, unet_conv_compute='float32'):
    import numpy as np
    import torch

    if latents.dtype != torch.float16 or tuple(latents.shape) != (1, 4, 64, 64):
        raise ValueError('Unexpected real latent contract')
    array = latents.detach().cpu().numpy()
    if not np.isfinite(array).all():
        raise ValueError('Nonfinite latents')
    path = output / 'latents.npy'
    with path.open('xb') as stream:
        np.save(stream, array, allow_pickle=False)
    metadata = {
        'model': 'stabilityai/sdxl-turbo',
        'snapshot': str(snapshot),
        'prompt': PROMPT,
        'seed': SEED,
        'width': SIZE,
        'height': SIZE,
        'steps': 1,
        'guidance_scale': 0.0,
        'generation_device': latents.device.type,
        'unet_conv_compute': unet_conv_compute,
        'latent_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    with (output / 'latents.json').open('x') as stream:
        json.dump(metadata, stream, indent=2)


def load_latents(source, snapshot):
    import numpy as np
    import torch

    path = source / 'latents.npy'
    if path.stat().st_size > 128 * 1024:
        raise ValueError('Latent file exceeds bound')
    metadata = json.loads((source / 'latents.json').read_text())
    if (
        metadata['snapshot'] != str(snapshot)
        or metadata['prompt'] != PROMPT
        or metadata['seed'] != SEED
        or metadata['latent_sha256'] != hashlib.sha256(path.read_bytes()).hexdigest()
    ):
        raise ValueError('Latent provenance mismatch')
    array = np.load(path, allow_pickle=False)
    if array.shape != (1, 4, 64, 64) or array.dtype != np.float16 or not np.isfinite(array).all():
        raise ValueError('Invalid latent array')
    return torch.from_numpy(array), metadata


def decode_real(snapshot, output, record):
    import torch
    from accelerate import init_empty_weights
    from diffusers import AutoencoderKL
    from diffusers.image_processor import VaeImageProcessor

    from scripts.image_device import prepare_device
    from scripts.image_stream_load import load_f32_component

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    latents, metadata = load_latents(output.parent / 'generation', snapshot)
    record('real_latents_verified')
    with init_empty_weights(include_buffers=False):
        vae = AutoencoderKL.from_config(AutoencoderKL.load_config(str(snapshot / 'vae')))
    load_f32_component(
        vae, snapshot / 'vae/diffusion_pytorch_model.safetensors', dtype=torch.float32
    )
    if vae.config.latents_mean is not None or vae.config.latents_std is not None:
        raise ValueError('Unsupported latent normalization')
    device = prepare_device(vae, record)
    record('vae_inventory', module_name='vae', **model_sample(watch_model(vae)))
    with torch.inference_mode():
        record('decoding', latent_bytes=latents.numel() * latents.element_size())
        with decode_memory(vae, record):
            decoded = vae.decode(
                latents.to(device=device, dtype=torch.float32) / vae.config.scaling_factor,
                return_dict=False,
            )[0]
        record('decode_returned')
        if not torch.isfinite(decoded).all():
            raise ValueError('Nonfinite decoded pixels')
        pixels = VaeImageProcessor().postprocess(decoded, output_type='np')
        digest = save_pixels(pixels, output)
        del pixels, decoded, latents
        record('decode_outputs_released')
    metadata.update(
        sha256=digest,
        image='image.png',
        experiment='separate-process-decode',
        vae_dtype='float32',
        unet_conv_compute=metadata.get('unet_conv_compute', 'float32'),
        device=device,
    )
    with (output / 'metadata.json').open('x') as stream:
        json.dump(metadata, stream, indent=2)
    record('image_saved', sha256=digest)


def experiment(output, *, address_policy='cpu'):
    """Sequential children, each existing 300s/8GiB guard; no retries or overlap."""
    if available_memory() <= 10 * GIB or shutil.disk_usage('.').free < GIB:
        raise RuntimeError('Memory/disk readiness failed')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'parent_before': memory_sample(), 'outcome': 'failed'}
    generation = run_probe(output / 'generation', mode='latent-only', address_policy=address_policy)
    report['generation'] = generation
    report['parent_after_generation'] = memory_sample()
    # run_probe waits/reaps before returning; a saved file alone is insufficient.
    if generation['outcome'] == 'latents_saved' and generation['returncode'] == 0:
        if Path(f'/proc/{generation["pid"]}').exists():
            raise RuntimeError('Generation child must exit before decode')
        report['generation_reaped_before_decode'] = True
        if available_memory() > 4 * GIB:
            report['decode'] = run_probe(
                output / 'decode', mode='decode-real', address_policy=address_policy
            )
            if report['decode']['outcome'] == 'image_saved':
                verify_artifact(output / 'decode')
                report['outcome'] = 'image_saved'
        else:
            report['reason'] = 'decode_readiness_failed'
    report['parent_after_decode'] = memory_sample()
    (output / 'experiment.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--address-policy', choices=('cpu', 'cuda'), default='cpu')
    args = parser.parse_args()
    result = experiment(args.output, address_policy=args.address_policy)
    print(json.dumps(result))
    raise SystemExit(0 if result['outcome'] == 'image_saved' else 1)
