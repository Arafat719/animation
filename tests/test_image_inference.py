import json
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from scripts.image_inference import PROMPT, SEED, SIZE, generate_image, save_pixels, verify_artifact


@pytest.fixture(autouse=True)
def no_real_gpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)


class Pipeline:
    def __init__(self, bad=None):
        self.bad = bad
        self.text_encoder = torch.nn.Identity()
        self.text_encoder_2 = torch.nn.Identity()
        self.unet = torch.nn.Identity()
        self.vae = SimpleNamespace(
            config=SimpleNamespace(latents_mean=None, latents_std=None, scaling_factor=0.5),
            decode=self.decode,
        )
        self.image_processor = SimpleNamespace(postprocess=self.postprocess)

    def __call__(self, **kwargs):
        assert kwargs['prompt'] == PROMPT
        assert kwargs['height'] == kwargs['width'] == SIZE
        assert kwargs['num_inference_steps'] == kwargs['num_images_per_prompt'] == 1
        assert kwargs['guidance_scale'] == 0
        assert kwargs['output_type'] == 'latent'
        assert kwargs['generator'].initial_seed() == SEED
        assert not torch.is_grad_enabled()
        value = torch.tensor([1.0])
        for module in (self.text_encoder, self.text_encoder_2, self.unet):
            assert module(value) is value
        return SimpleNamespace(
            images=torch.full(
                (1, 4, 2, 2), float('nan') if self.bad == 'latent' else 1.0, dtype=torch.float16
            )
        )

    def decode(self, latents, return_dict):
        assert latents.dtype == torch.float32 and torch.all(latents == 2)
        assert return_dict is False
        return (torch.tensor([float('inf') if self.bad == 'decode' else 0.0]),)

    def postprocess(self, decoded, output_type):
        assert output_type == 'np'
        return np.full((1, SIZE, SIZE, 3), 0.5, dtype=np.float32)


def test_stub_inference_verified_image_and_metadata(tmp_path):
    stages = []
    generate_image(
        Pipeline(), tmp_path, '/local/snapshot', lambda stage, **kw: stages.append(stage)
    )
    assert stages == [
        'device_selected',
        'pipeline_enter',
        'text_encoder_enter',
        'text_encoder_exit',
        'text_encoder_2_enter',
        'text_encoder_2_exit',
        'unet_enter',
        'unet_exit',
        'pipeline_returned',
        'latents_validated',
        'denoisers_released',
        'decoding',
        'decode_returned',
        'saving_image',
        'image_saved',
    ]
    metadata = json.loads((tmp_path / 'metadata.json').read_text())
    assert metadata['snapshot'] == '/local/snapshot'
    assert metadata['sha256'] == verify_artifact(tmp_path)
    metadata['sha256'] = 'wrong'
    (tmp_path / 'metadata.json').write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match='metadata'):
        verify_artifact(tmp_path)


@pytest.mark.parametrize('bad', ['latent', 'decode'])
def test_nonfinite_values_fail_before_image(tmp_path, bad):
    with pytest.raises(ValueError, match='Nonfinite'):
        generate_image(Pipeline(bad), tmp_path, '/local', lambda *a, **kw: None)
    assert not (tmp_path / 'image.png').exists()


@pytest.mark.parametrize('bad', ['nan', 'range', 'shape'])
def test_bad_pixels_rejected(tmp_path, bad):
    pixels = np.zeros((1, SIZE, SIZE, 3), dtype=np.float32)
    if bad == 'nan':
        pixels[0, 0, 0, 0] = np.nan
    elif bad == 'range':
        pixels[0, 0, 0, 0] = 2
    else:
        pixels = pixels[:, :1]
    with pytest.raises(ValueError):
        save_pixels(pixels, tmp_path)
    assert not (tmp_path / 'image.png').exists()


def test_existing_image_preserved(tmp_path):
    path = tmp_path / 'image.png'
    path.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        save_pixels(np.zeros((1, SIZE, SIZE, 3)), tmp_path)
    assert path.read_bytes() == b'keep'


def test_parent_rejects_missing_image_despite_success_stage(tmp_path, monkeypatch):
    from scripts.image_load_probe import run_probe

    class Child:
        pid = 123456
        returncode = 0

        def poll(self):
            return 0

        def wait(self):
            return 0

    def spawn(*args, **kwargs):
        (tmp_path / 'probe/stage.json').write_text('{"stage":"image_saved"}')
        return Child()

    monkeypatch.setattr('scripts.image_load_probe.subprocess.Popen', spawn)
    monkeypatch.setattr('scripts.image_load_probe.resident_memory', lambda pid: 0)
    monkeypatch.setattr('scripts.image_load_probe.available_memory', lambda: 10 * 1024**3)
    result = run_probe(tmp_path / 'probe', mode='infer')
    assert result['outcome'] == 'failed'
    assert result['reason'] == 'invalid_image_artifact'


@pytest.mark.parametrize('failure', [False, True])
def test_component_hooks_cleaned_and_output_preserved(failure):
    from scripts.image_inference import component_timing

    pipe = Pipeline()
    events = []
    value = torch.tensor([3.0])

    class Broken(torch.nn.Module):
        def forward(self, value):
            raise RuntimeError('forward failed')

    if failure:
        pipe.unet = Broken()
    try:
        with component_timing(pipe, lambda stage: events.append(stage)):
            assert pipe.text_encoder(value) is value
            assert pipe.unet(value) is value
    except RuntimeError as error:
        assert failure and str(error) == 'forward failed'
    else:
        assert not failure
    assert events[-1] == ('unet_enter' if failure else 'unet_exit')
    for module in (pipe.text_encoder, pipe.text_encoder_2, pipe.unet):
        assert not module._forward_hooks and not module._forward_pre_hooks


def test_partial_hook_registration_cleanup():
    from scripts.image_inference import component_timing

    pipe = Pipeline()
    pipe.text_encoder_2 = object()
    with pytest.raises(AttributeError), component_timing(pipe, lambda stage: None):
        pytest.fail('registration must fail')
    assert not pipe.text_encoder._forward_hooks
    assert not pipe.text_encoder._forward_pre_hooks


def test_mixed_opt_in_context_and_metadata(tmp_path, monkeypatch):
    from contextlib import contextmanager

    pipe = Pipeline()
    events = []

    @contextmanager
    def adapter(module):
        assert module is pipe.unet
        events.append('enter')
        try:
            yield
        finally:
            events.append('exit')

    monkeypatch.setattr('scripts.image_mixed_conv.mixed_convolutions', adapter)
    generate_image(pipe, tmp_path, '/local', lambda *a, **kw: None, mixed_conv=True)
    assert events == ['enter', 'exit']
    assert json.loads((tmp_path / 'metadata.json').read_text())['unet_conv_compute'] == 'float32'


@pytest.mark.parametrize('bad', [None, 'decode'])
def test_denoisers_collected_before_decode(tmp_path, bad):
    import weakref

    pipe = Pipeline(bad)
    refs = [weakref.ref(getattr(pipe, name)) for name in ('unet', 'text_encoder', 'text_encoder_2')]
    original_decode = pipe.vae.decode

    def decode(*args, **kwargs):
        assert all(ref() is None for ref in refs)
        assert pipe.unet is pipe.text_encoder is pipe.text_encoder_2 is None
        return original_decode(*args, **kwargs)

    pipe.vae.decode = decode
    if bad:
        with pytest.raises(ValueError, match='Nonfinite decoded'):
            generate_image(pipe, tmp_path, '/local', lambda *a, **kw: None)
    else:
        generate_image(pipe, tmp_path, '/local', lambda *a, **kw: None)
        assert verify_artifact(tmp_path)


def test_invalid_latents_do_not_release_models(tmp_path):
    pipe = Pipeline('latent')
    with pytest.raises(ValueError, match='Nonfinite latents'):
        generate_image(pipe, tmp_path, '/local', lambda *a, **kw: None)
    assert pipe.unet is not None
    assert not pipe.unet._forward_hooks and not pipe.unet._forward_pre_hooks


def test_memory_diagnostics_observe_released_models(tmp_path):
    pipe = Pipeline()
    original = pipe.vae

    class VAE(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.config = original.config
            self.decoder = torch.nn.Identity()

        def decode(self, latents, return_dict):
            return (self.decoder(original.decode(latents, return_dict)[0]),)

    pipe.vae = VAE()
    events = []
    generate_image(
        pipe,
        tmp_path,
        '/local',
        lambda stage, **kw: events.append((stage, kw)),
        diagnose_memory=True,
    )
    released = {kw['module_name']: kw for stage, kw in events if stage == 'model_after_release'}
    for name in ('unet', 'text_encoder', 'text_encoder_2'):
        assert not released[name]['root_alive']
        assert released[name]['live_tensor_count'] == 0
    assert released['vae']['root_alive']
    assert any(stage == 'vae_enter' for stage, _ in events)
    assert not pipe.vae.decoder._forward_hooks
    assert verify_artifact(tmp_path)


def test_latent_only_returns_without_decode(tmp_path, monkeypatch):
    pipe = Pipeline()
    saved = []
    monkeypatch.setattr(
        'scripts.image_split_probe.save_latents',
        lambda latent, output, snapshot, **kw: saved.append((latent.shape, output, snapshot)),
    )

    def forbidden(*args, **kwargs):
        pytest.fail('latent-only must never decode')

    pipe.vae.decode = forbidden
    events = []
    generate_image(
        pipe, tmp_path, '/local', lambda stage, **kw: events.append(stage), latent_only=True
    )
    assert saved == [(torch.Size([1, 4, 2, 2]), tmp_path, '/local')]
    assert events[-1] == 'latents_saved'
    assert not pipe.unet._forward_hooks
    assert not (tmp_path / 'image.png').exists()


def test_cuda_route_generator_decode_and_metadata_without_gpu(tmp_path, monkeypatch):
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: True)
    pipe = Pipeline()
    transfers = []
    pipe.to = lambda device: transfers.append(('pipeline', device))
    original_generator = torch.Generator
    original_to = torch.Tensor.to

    def generator(*, device):
        transfers.append(('generator', device))
        return original_generator(device='cpu')

    def tensor_to(tensor, *args, **kwargs):
        if kwargs.get('device') == 'cuda':
            transfers.append(('decode', kwargs['device'], kwargs['dtype']))
            kwargs['device'] = 'cpu'
        return original_to(tensor, *args, **kwargs)

    def forbidden(*args, **kwargs):
        pytest.fail('CPU mixed convolution must not be enabled for CUDA')

    monkeypatch.setattr(torch, 'Generator', generator)
    monkeypatch.setattr(torch.Tensor, 'to', tensor_to)
    monkeypatch.setattr('scripts.image_mixed_conv.mixed_convolutions', forbidden)
    generate_image(pipe, tmp_path, '/local', lambda *a, **kw: None, mixed_conv=True)
    assert transfers == [
        ('pipeline', 'cuda'),
        ('generator', 'cuda'),
        ('decode', 'cuda', torch.float32),
    ]
    metadata = json.loads((tmp_path / 'metadata.json').read_text())
    assert metadata['device'] == 'cuda'
    assert metadata['unet_conv_compute'] == 'float16'
    assert metadata['dtypes']['vae'] == 'float32'
    assert verify_artifact(tmp_path)
