import hashlib
import io
from threading import Event

import pytest
from PIL import Image

from animation_studio.providers.comfy_image import MAX_IMAGE_BYTES, ComfyImageProvider
from animation_studio.providers.comfy_workflow import (
    MODEL_NAME,
    MODEL_VERSION,
    validate_image_workflow,
)
from animation_studio.providers.image import ImageProviderError, ImageRequest


class FakeExecutor:
    is_mock = True

    def __init__(self, content=None):
        if content is None:
            stream = io.BytesIO()
            Image.new('RGB', (512, 512)).save(stream, format='PNG')
            content = stream.getvalue()
        self.content = content
        self.calls = []
        self.error = None
        self.cancel_on_execute = False

    def execute(self, graph, *, cancel=None):
        self.calls.append(graph)
        if self.error:
            raise self.error
        if self.cancel_on_execute:
            cancel.set()
        return self.content


@pytest.fixture
def image_request():
    return ImageRequest(
        prompt='নদীর পাশে বাড়ি', model_name=MODEL_NAME, model_version=MODEL_VERSION, seed=42
    )


def test_verified_output_and_no_network(tmp_path, image_request, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('Network is forbidden')

    monkeypatch.setattr(socket, 'socket', forbidden)
    executor = FakeExecutor()
    provider = ComfyImageProvider(executor, tmp_path)
    first = provider.generate(image_request)
    second = provider.generate(image_request)
    assert first.is_mock and first.provider_name == 'comfy-image'
    assert first.path != second.path
    assert first.path.read_bytes() == second.path.read_bytes() == executor.content
    assert first.sha256 == hashlib.sha256(executor.content).hexdigest()
    assert validate_image_workflow(executor.calls[0]) == image_request


@pytest.mark.parametrize(
    'content',
    [b'', b'bad', b'x' * (MAX_IMAGE_BYTES + 1), 'not bytes'],
    ids=['empty', 'corrupt', 'oversize', 'wrong-type'],
)
def test_invalid_content(tmp_path, image_request, content):
    with pytest.raises(ImageProviderError) as caught:
        ComfyImageProvider(FakeExecutor(content), tmp_path).generate(image_request)
    assert caught.value.code == 'invalid_image'
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('format,size', [('JPEG', (512, 512)), ('PNG', (4, 4))])
def test_format_and_dimensions(tmp_path, image_request, format, size):
    stream = io.BytesIO()
    Image.new('RGB', size).save(stream, format=format)
    with pytest.raises(ImageProviderError) as caught:
        ComfyImageProvider(FakeExecutor(stream.getvalue()), tmp_path).generate(image_request)
    assert caught.value.code == 'invalid_image'


@pytest.mark.parametrize(
    'error,code',
    [
        (TimeoutError('private details'), 'timeout'),
        (OSError('private details'), 'execution_failed'),
        (ImageProviderError('cancelled', 'cancelled'), 'cancelled'),
    ],
)
def test_failure_without_retry(tmp_path, image_request, error, code):
    executor = FakeExecutor()
    executor.error = error
    with pytest.raises(ImageProviderError) as caught:
        ComfyImageProvider(executor, tmp_path).generate(image_request)
    assert caught.value.code == code
    assert len(executor.calls) == 1
    assert not list(tmp_path.iterdir())


def test_cancel_after_execution(tmp_path, image_request):
    executor = FakeExecutor()
    executor.cancel_on_execute = True
    with pytest.raises(ImageProviderError) as caught:
        ComfyImageProvider(executor, tmp_path).generate(image_request, cancel=Event())
    assert caught.value.code == 'cancelled'
    assert not list(tmp_path.iterdir())


def test_unsupported_does_not_execute(tmp_path, image_request):
    executor = FakeExecutor()
    with pytest.raises(ImageProviderError) as caught:
        ComfyImageProvider(executor, tmp_path).generate(
            image_request.model_copy(update={'model_version': 'main'})
        )
    assert caught.value.code == 'unsupported'
    assert executor.calls == []


def test_output_failure(tmp_path, image_request):
    target = tmp_path / 'file'
    target.write_text('preserve')
    with pytest.raises(ImageProviderError) as caught:
        ComfyImageProvider(FakeExecutor(), target).generate(image_request)
    assert caught.value.code == 'io_error'
    assert target.read_text() == 'preserve'


def test_cancel_after_write_cleans_output(tmp_path, image_request, monkeypatch):
    cancel = Event()
    provider = ComfyImageProvider(FakeExecutor(), tmp_path)
    original = provider._check_cancel

    def check(event):
        if list(tmp_path.glob('*.png')):
            cancel.set()
        original(event)

    monkeypatch.setattr(provider, '_check_cancel', check)
    with pytest.raises(ImageProviderError) as caught:
        provider.generate(image_request, cancel=cancel)
    assert caught.value.code == 'cancelled'
    assert not list(tmp_path.iterdir())
