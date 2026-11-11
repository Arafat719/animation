import asyncio
import hashlib
import io

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from starlette.requests import Request

from animation_studio.media import reference_image as validator
from apps.api import reference_images as route
from apps.api.main import app


def picture(fmt='PNG', size=(32, 24)):
    output = io.BytesIO()
    Image.new('RGB', size, 'navy').save(output, format=fmt)
    return output.getvalue()


def upload(data, filename='reference.png', media_type='image/png', **headers):
    return TestClient(app).post(
        '/reference-images/validate',
        content=data,
        headers={'x-filename': filename, 'content-type': media_type, **headers},
    )


@pytest.mark.parametrize(
    'fmt,name,mime', [('PNG', 'face.png', 'image/png'), ('JPEG', 'face.JPEG', 'image/jpeg')]
)
def test_valid_image_returns_verified_metadata_only(fmt, name, mime, tmp_path, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', str(tmp_path / 'unused.db'))
    data = picture(fmt)
    response = upload(data, name, mime)
    assert response.status_code == 200
    assert response.json() == {
        'filename': name,
        'media_type': mime,
        'width': 32,
        'height': 24,
        'size_bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'stored': False,
    }
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    'name',
    [
        '../face.png',
        '/tmp/face.png',
        r'a\face.png',
        '.hidden.png',
        'a%2f.png',
        '',
        'a' * 121 + '.png',
    ],
)
def test_unsafe_filenames_rejected(name):
    response = upload(picture(), name)
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'invalid_filename'


@pytest.mark.parametrize(
    'data,name,mime,code,status',
    [
        (b'', 'x.png', 'image/png', 'empty_image', 422),
        (b'<svg/>', 'x.svg', 'image/svg+xml', 'unsupported_media_type', 415),
        (b'bad', 'x.png', 'image/png', 'invalid_image', 422),
        (picture(), 'x.jpg', 'image/png', 'extension_mismatch', 422),
        (picture('JPEG'), 'x.png', 'image/png', 'content_type_mismatch', 422),
        (picture()[:40], 'x.png', 'image/png', 'invalid_image', 422),
        (picture('JPEG')[:-20], 'x.jpg', 'image/jpeg', 'invalid_image', 422),
    ],
)
def test_invalid_uploads(data, name, mime, code, status):
    response = upload(data, name, mime)
    assert response.status_code == status
    assert response.json()['detail'] == {'code': code}


def test_oversized_dimensions_rejected_before_decode():
    response = upload(picture(size=(4097, 1)))
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'invalid_dimensions'


def test_animated_png_rejected():
    output = io.BytesIO()
    Image.new('RGB', (8, 8), 'red').save(
        output,
        format='PNG',
        save_all=True,
        append_images=[Image.new('RGB', (8, 8), 'blue')],
        duration=100,
    )
    assert upload(output.getvalue()).json()['detail']['code'] == 'animated_image'


def test_byte_limit_equality_and_excess(monkeypatch):
    data = picture()
    monkeypatch.setattr(validator, 'MAX_BYTES', len(data))
    assert validator.validate_reference_image(data, filename='x.png', media_type='image/png')
    with pytest.raises(validator.ReferenceImageError, match='image_too_large'):
        validator.validate_reference_image(data + b'x', filename='x.png', media_type='image/png')


@pytest.mark.parametrize(
    'headers,code,status',
    [
        ({'content-length': str(validator.MAX_BYTES + 1)}, 'image_too_large', 413),
        ({'content-length': '-1'}, 'invalid_content_length', 400),
        ({'content-length': '1'}, 'content_length_mismatch', 400),
        ({'content-encoding': 'gzip'}, 'unsupported_encoding', 415),
    ],
)
def test_header_rejections(headers, code, status):
    response = upload(picture(), **headers)
    assert response.status_code == status
    assert response.json()['detail']['code'] == code


@pytest.mark.parametrize('declared', [None, '1'])
def test_stream_limit_without_trusting_declared_size(monkeypatch, declared):
    monkeypatch.setattr(route, 'MAX_BYTES', 10)
    reads = 0

    async def receive():
        nonlocal reads
        reads += 1
        return {'type': 'http.request', 'body': b'x' * 6, 'more_body': True}

    headers = [(b'x-filename', b'x.png'), (b'content-type', b'image/png')]
    if declared:
        headers.append((b'content-length', declared.encode()))
    request = Request({'type': 'http', 'headers': headers}, receive=receive)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(route.validate_upload(request))
    assert caught.value.status_code == 413 and reads == 2


def test_disconnected_upload_has_bounded_error():
    async def receive():
        return {'type': 'http.disconnect'}

    request = Request(
        {
            'type': 'http',
            'headers': [
                (b'x-filename', b'x.png'),
                (b'content-type', b'image/png'),
            ],
        },
        receive=receive,
    )
    with pytest.raises(HTTPException) as caught:
        asyncio.run(route.validate_upload(request))
    assert caught.value.detail == {'code': 'upload_disconnected'}


def test_upload_timeout(monkeypatch):
    monkeypatch.setattr(route, 'UPLOAD_TIMEOUT_SECONDS', 0.01)

    async def receive():
        await asyncio.sleep(1)
        return {'type': 'http.request', 'body': b'', 'more_body': False}

    request = Request(
        {
            'type': 'http',
            'headers': [
                (b'x-filename', b'x.png'),
                (b'content-type', b'image/png'),
            ],
        },
        receive=receive,
    )
    with pytest.raises(HTTPException) as caught:
        asyncio.run(route.validate_upload(request))
    assert caught.value.status_code == 408
    assert caught.value.detail == {'code': 'upload_timeout'}


def test_valid_chunked_upload_without_content_length():
    data = picture(size=(4096, 1))
    chunks = iter([data[:20], data[20:]])
    count = 0

    async def receive():
        nonlocal count
        count += 1
        return {'type': 'http.request', 'body': next(chunks), 'more_body': count == 1}

    request = Request(
        {
            'type': 'http',
            'headers': [
                (b'x-filename', b'x.png'),
                (b'content-type', b'image/png'),
            ],
        },
        receive=receive,
    )
    result = asyncio.run(route.validate_upload(request))
    assert result.width == 4096 and result.height == 1 and not result.stored
