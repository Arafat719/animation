"""Bounded reference upload validation; no persistence or model execution."""

import hashlib
import io
import re
from pathlib import PurePosixPath

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict

MAX_BYTES = 8 * 1024 * 1024
MAX_DIMENSION = 4096
MEDIA = {'image/png': ('PNG', {'.png'}), 'image/jpeg': ('JPEG', {'.jpg', '.jpeg'})}


class ReferenceImageError(ValueError):
    def __init__(self, code: str, status: int = 422):
        super().__init__(code)
        self.code = code
        self.status = status


class ReferenceImageValidation(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    filename: str
    media_type: str
    size_bytes: int
    width: int
    height: int
    sha256: str
    stored: bool = False


def validate_reference_headers(filename: str, media_type: str) -> None:
    if (
        len(filename) > 120
        or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_. -]*', filename) is None
        or '..' in filename
    ):
        raise ReferenceImageError('invalid_filename')
    if media_type not in MEDIA:
        raise ReferenceImageError('unsupported_media_type', 415)
    if PurePosixPath(filename).suffix.lower() not in MEDIA[media_type][1]:
        raise ReferenceImageError('extension_mismatch')


def validate_reference_image(
    data: bytes, *, filename: str, media_type: str
) -> ReferenceImageValidation:
    validate_reference_headers(filename, media_type)
    if len(data) > MAX_BYTES:
        raise ReferenceImageError('image_too_large', 413)
    if not data:
        raise ReferenceImageError('empty_image')
    try:
        with Image.open(io.BytesIO(data), formats=['PNG', 'JPEG']) as image:
            if image.format != MEDIA[media_type][0]:
                raise ReferenceImageError('content_type_mismatch')
            width, height = image.size
            if not (1 <= width <= MAX_DIMENSION and 1 <= height <= MAX_DIMENSION):
                raise ReferenceImageError('invalid_dimensions')
            if getattr(image, 'n_frames', 1) != 1:
                raise ReferenceImageError('animated_image')
            image.verify()
        # verify alone does not decode all pixels (notably JPEG).
        with Image.open(io.BytesIO(data), formats=['PNG', 'JPEG']) as image:
            image.load()
    except ReferenceImageError:
        raise
    except Image.DecompressionBombError:
        raise ReferenceImageError('invalid_dimensions') from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError):
        raise ReferenceImageError('invalid_image') from None
    return ReferenceImageValidation(
        filename=filename,
        media_type=media_type,
        size_bytes=len(data),
        width=width,
        height=height,
        sha256=hashlib.sha256(data).hexdigest(),
    )
