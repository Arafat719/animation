"""One fixed offline SDXL-Turbo image; called only inside the guarded child."""

import gc
import hashlib
import json
from contextlib import contextmanager, nullcontext
from pathlib import Path

PROMPT = 'Anime illustration of a young adult explorer in a blue jacket, mountain meadow, daylight'
SEED = 42
SIZE = 512


@contextmanager
def component_timing(pipe, record):
    """Observe top-level forwards without retaining or replacing tensors."""
    handles = []

    def before(name):
        def hook(module, args):
            record(f'{name}_enter')

        return hook

    def after(name):
        def hook(module, args, output):
            record(f'{name}_exit')

        return hook

    try:
        for name in ('text_encoder', 'text_encoder_2', 'unet'):
            module = getattr(pipe, name)
            handles.append(module.register_forward_pre_hook(before(name)))
            handles.append(module.register_forward_hook(after(name)))
        yield
    finally:
        for handle in handles:
            handle.remove()


def verify_png(path):
    from PIL import Image

    with Image.open(path) as image:
        if image.format != 'PNG' or image.size != (SIZE, SIZE) or image.mode != 'RGB':
            raise ValueError('Unexpected image format/size/mode')
        image.verify()
    with Image.open(path) as image:
        image.load()
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_pixels(pixels, output):
    import numpy as np
    from PIL import Image

    if pixels.shape != (1, SIZE, SIZE, 3) or not np.isfinite(pixels).all():
        raise ValueError('Invalid image shape or nonfinite pixels')
    if pixels.min() < 0 or pixels.max() > 1:
        raise ValueError('Pixels outside normalized range')
    path = output / 'image.png'
    with path.open('xb') as stream:
        Image.fromarray((pixels[0] * 255).round().astype('uint8')).save(stream, format='PNG')
    return verify_png(path)


def generate_image(
    pipe, output, snapshot, record, *, mixed_conv=False, diagnose_memory=False, latent_only=False
):
    import torch

    # Explicit decode keeps the validated F32 VAE and checks values before clamp.
    if pipe.vae.config.latents_mean is not None or pipe.vae.config.latents_std is not None:
        raise ValueError('Unsupported VAE latent normalization')
    from scripts.image_device import prepare_device
    from scripts.image_mixed_conv import mixed_convolutions

    device = prepare_device(pipe, record)
    mixed_conv = mixed_conv and device == 'cpu'
    convolution_context = mixed_convolutions(pipe.unet) if mixed_conv else nullcontext()
    record('pipeline_enter')
    with torch.inference_mode():
        with component_timing(pipe, record), convolution_context:
            latents = pipe(
                prompt=PROMPT,
                height=SIZE,
                width=SIZE,
                num_inference_steps=1,
                guidance_scale=0.0,
                num_images_per_prompt=1,
                generator=torch.Generator(device=device).manual_seed(SEED),
                output_type='latent',
            ).images
            record('pipeline_returned')
            if not torch.isfinite(latents).all():
                raise ValueError('Nonfinite latents')
            record('latents_validated')
        if latent_only:
            from scripts.image_split_probe import save_latents

            save_latents(
                latents,
                output,
                snapshot,
                unet_conv_compute='float32' if mixed_conv else 'float16',
            )
            record('latents_saved')
            return
        if diagnose_memory:
            from scripts.image_memory import decode_memory, model_sample, watch_model

            watches = {
                name: watch_model(getattr(pipe, name))
                for name in ('unet', 'text_encoder', 'text_encoder_2', 'vae')
            }
            for name, watch in watches.items():
                record('model_before_release', module_name=name, **model_sample(watch))
        # Single-use harness: close hooks/adapter before dropping model ownership.
        del convolution_context
        for name in ('unet', 'text_encoder', 'text_encoder_2'):
            setattr(pipe, name, None)
        gc.collect()
        record('denoisers_released')
        if diagnose_memory:
            for name, watch in watches.items():
                record('model_after_release', module_name=name, **model_sample(watch))
        record('decoding', latent_bytes=latents.numel() * latents.element_size())
        with decode_memory(pipe.vae, record) if diagnose_memory else nullcontext():
            decoded = pipe.vae.decode(
                latents.to(device=device, dtype=torch.float32) / pipe.vae.config.scaling_factor,
                return_dict=False,
            )[0]
        record('decode_returned')
        if not torch.isfinite(decoded).all():
            raise ValueError('Nonfinite decoded pixels')
        pixels = pipe.image_processor.postprocess(decoded, output_type='np')
    record('saving_image')
    digest = save_pixels(pixels, output)
    metadata = {
        'model': 'stabilityai/sdxl-turbo',
        'snapshot': str(snapshot),
        'prompt': PROMPT,
        'seed': SEED,
        'width': SIZE,
        'height': SIZE,
        'steps': 1,
        'guidance_scale': 0.0,
        'device': device,
        'dtypes': {
            'unet': 'float16',
            'text_encoder': 'float16',
            'text_encoder_2': 'float16',
            'vae': 'float32',
        },
        'released_before_decode': ['unet', 'text_encoder', 'text_encoder_2'],
        'unet_conv_compute': 'float32' if mixed_conv else 'float16',
        'image': 'image.png',
        'sha256': digest,
    }
    with (output / 'metadata.json').open('x') as stream:
        json.dump(metadata, stream, indent=2)
    record('image_saved', sha256=digest)


def verify_artifact(output):
    metadata = json.loads((output / 'metadata.json').read_text())
    digest = verify_png(output / 'image.png')
    if metadata['sha256'] != digest or metadata['seed'] != SEED or metadata['prompt'] != PROMPT:
        raise ValueError('Image metadata mismatch')
    return digest
