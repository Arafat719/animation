"""Raw image upload validation; no multipart dependency or stored personal assets."""

import asyncio

from fastapi import APIRouter, HTTPException, Request
from starlette.requests import ClientDisconnect

from animation_studio.media.reference_image import (
    MAX_BYTES,
    ReferenceImageError,
    ReferenceImageValidation,
    validate_reference_headers,
    validate_reference_image,
)

router = APIRouter()
UPLOAD_TIMEOUT_SECONDS = 15


@router.post('/reference-images/validate', response_model=ReferenceImageValidation)
async def validate_upload(request: Request):
    filename = request.headers.get('x-filename', '')
    media_type = request.headers.get('content-type', '')
    try:
        validate_reference_headers(filename, media_type)
        if request.headers.get('content-encoding', 'identity') != 'identity':
            raise ReferenceImageError('unsupported_encoding', 415)
        declared = request.headers.get('content-length')
        if declared is not None:
            if not declared.isascii() or not declared.isdecimal() or len(declared) > 20:
                raise ReferenceImageError('invalid_content_length', 400)
            if int(declared) > MAX_BYTES:
                raise ReferenceImageError('image_too_large', 413)
        body = bytearray()
        async with asyncio.timeout(UPLOAD_TIMEOUT_SECONDS):
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_BYTES:
                    raise ReferenceImageError('image_too_large', 413)
                body.extend(chunk)
        if declared is not None and int(declared) != len(body):
            raise ReferenceImageError('content_length_mismatch', 400)
        return await asyncio.to_thread(
            validate_reference_image, bytes(body), filename=filename, media_type=media_type
        )
    except ReferenceImageError as error:
        raise HTTPException(error.status, detail={'code': error.code}) from None
    except TimeoutError:
        raise HTTPException(408, detail={'code': 'upload_timeout'}) from None
    except ClientDisconnect:
        raise HTTPException(400, detail={'code': 'upload_disconnected'}) from None
