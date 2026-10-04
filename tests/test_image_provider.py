"""Reusable image boundary checks plus fixture-only failure coverage."""

import hashlib
from threading import Event

import pytest
from PIL import Image
from pydantic import ValidationError

from animation_studio.providers.image import (
    ImageProvider,
    ImageProviderError,
    ImageRequest,
    ImageResult,
    MockImageProvider,
)


@pytest.fixture
def provider() -> ImageProvider:
    return MockImageProvider()


@pytest.fixture
def image_request():
    return ImageRequest(
        prompt='নদীর পাশে একটি বাড়ি', model_name='fixture-image', model_version='1', seed=42
    )


@pytest.fixture(params=['mock', 'comfy', 'durable', 'durable_v2'])
def contract_case(request, tmp_path, image_request):
    if request.param == 'mock':
        return MockImageProvider(), image_request
    import io

    from animation_studio.providers.comfy_image import ComfyImageProvider
    from animation_studio.providers.comfy_workflow import MODEL_NAME, MODEL_VERSION

    if request.param in ('durable', 'durable_v2'):
        import httpx
        from test_comfy_http import Server

        from animation_studio.providers.comfy_durable_image import DurableComfyImageProvider
        from animation_studio.providers.comfy_http import ComfyHTTPExecutor
        from animation_studio.providers.comfy_journal import DurableComfyExecutor
        from animation_studio.providers.comfy_workflow import build_image_workflow

        selected = image_request.model_copy(
            update={'model_name': MODEL_NAME, 'model_version': MODEL_VERSION}
        )
        client = ComfyHTTPExecutor(
            transport=httpx.MockTransport(Server(build_image_workflow(selected)))
        )
        request.addfinalizer(client.close)
        if request.param == 'durable':
            executor = DurableComfyExecutor(client, tmp_path / 'job.json')
        else:
            from animation_studio.providers.comfy_identity import ComfyExecutionContext
            from animation_studio.providers.comfy_journal import _fingerprint
            from animation_studio.providers.comfy_v2_executor import DurableComfyExecutorV2

            tmp_path.chmod(0o700)
            context = ComfyExecutionContext(
                mode='mock',
                job_id='12345678-1234-4234-8234-123456789abc',
                graph_sha256=_fingerprint(build_image_workflow(selected)),
                origin='https://comfy.invalid:443/',
                deployment_id='12345678-1234-4234-8234-123456789abc',
                runtime_manifest_sha256='a' * 64,
                model_manifest_sha256='b' * 64,
            )
            executor = DurableComfyExecutorV2(client, tmp_path, context)
        return DurableComfyImageProvider(executor, tmp_path / 'output'), selected

    class Executor:
        is_mock = True

        def execute(self, graph, *, cancel=None):
            content = io.BytesIO()
            Image.new('RGB', (512, 512)).save(content, format='PNG')
            return content.getvalue()

    return ComfyImageProvider(Executor(), tmp_path), image_request.model_copy(
        update={'model_name': MODEL_NAME, 'model_version': MODEL_VERSION}
    )


def test_contract_verified_media_and_metadata(contract_case):
    provider, image_request = contract_case
    result = provider.generate(image_request)
    assert (result.model_name, result.model_version, result.seed) == (
        image_request.model_name,
        image_request.model_version,
        image_request.seed,
    )
    assert result.path.is_absolute()
    assert result.sha256 == hashlib.sha256(result.path.read_bytes()).hexdigest()
    with Image.open(result.path) as image:
        image.load()
        assert image.format == 'PNG'
        assert image.size == (result.width, result.height)
    assert ImageResult.model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValidationError):
        result.seed = 10


def test_mock_repeatability_and_honest_identity(provider, image_request):
    first = provider.generate(image_request)
    assert first.is_mock and first.provider_name == 'mock-image'
    assert provider.generate(image_request) == first
    changed = provider.generate(image_request.model_copy(update={'seed': 8, 'prompt': 'Another'}))
    assert changed.seed == 8 and changed.sha256 == first.sha256
    assert provider.generate(image_request) == first


def test_contract_cancel_before_io(contract_case):
    provider, image_request = contract_case
    cancel = Event()
    cancel.set()
    with pytest.raises(ImageProviderError) as error:
        provider.generate(image_request, cancel=cancel)
    assert error.value.code == 'cancelled'


@pytest.mark.parametrize(
    'update',
    [
        {'prompt': ' '},
        {'seed': True},
        {'seed': -1},
        {'seed': 2**32},
        {'seed': '4'},
        {'model_name': ''},
        {'model_version': ''},
    ],
)
def test_contract_revalidates_bypassed_models(contract_case, update):
    provider, image_request = contract_case
    with pytest.raises(ValidationError):
        provider.generate(image_request.model_copy(update=update))


def test_extra_input_rejected(image_request):
    with pytest.raises(ValidationError):
        ImageRequest(**image_request.model_dump(), unexpected=1)


@pytest.mark.parametrize('update', [{'model_name': 'sdxl-turbo'}, {'model_version': '2'}])
def test_mock_unsupported_model(image_request, update):
    with pytest.raises(ImageProviderError) as error:
        MockImageProvider().generate(image_request.model_copy(update=update))
    assert error.value.code == 'unsupported'


@pytest.mark.parametrize('content', [b'', b'not an image', b'\x89PNG\r\n\x1a\n'])
def test_corrupt_fixture(tmp_path, image_request, content):
    path = tmp_path / 'image.png'
    path.write_bytes(content)
    with pytest.raises(ImageProviderError) as error:
        MockImageProvider(path).generate(image_request)
    assert error.value.code == 'invalid_image'
    assert path.read_bytes() == content


def test_wrong_format(tmp_path, image_request):
    path = tmp_path / 'image.png'
    Image.new('RGB', (4, 4)).save(path, format='JPEG')
    with pytest.raises(ImageProviderError) as error:
        MockImageProvider(path).generate(image_request)
    assert error.value.code == 'invalid_image'


def test_missing_and_io_error(tmp_path, image_request):
    for path, code in [(tmp_path / 'missing.png', 'fixture_missing'), (tmp_path, 'io_error')]:
        with pytest.raises(ImageProviderError) as error:
            MockImageProvider(path).generate(image_request)
        assert error.value.code == code


def test_cancel_during_decode(monkeypatch, image_request):
    cancel = Event()
    original = Image.Image.load

    def load(image, *args, **kwargs):
        cancel.set()
        return original(image, *args, **kwargs)

    monkeypatch.setattr(Image.Image, 'load', load)
    with pytest.raises(ImageProviderError) as error:
        MockImageProvider().generate(image_request, cancel=cancel)
    assert error.value.code == 'cancelled'


def test_byte_limit(tmp_path, image_request):
    path = tmp_path / 'large.png'
    with path.open('wb') as stream:
        stream.truncate(16 * 1024 * 1024 + 1)
    with pytest.raises(ImageProviderError) as error:
        MockImageProvider(path).generate(image_request)
    assert error.value.code == 'invalid_image'


def test_truncated_png(tmp_path, image_request):
    path = tmp_path / 'truncated.png'
    content = MockImageProvider().fixture_path.read_bytes()
    path.write_bytes(content[: len(content) // 2])
    with pytest.raises(ImageProviderError) as error:
        MockImageProvider(path).generate(image_request)
    assert error.value.code == 'invalid_image'


def test_no_network_or_fixture_mutation(monkeypatch, provider, image_request):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('No network allowed')

    monkeypatch.setattr(socket, 'socket', forbidden)
    before = provider.fixture_path.read_bytes()
    provider.generate(image_request)
    assert provider.fixture_path.read_bytes() == before
