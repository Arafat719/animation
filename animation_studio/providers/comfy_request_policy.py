"""Pure request policy for future Comfy transport; no client or live activation."""

import math
import re

from animation_studio.providers.comfy_identity import canonical_origin
from animation_studio.providers.image import ImageProviderError


def validate_comfy_request(
    *,
    origin: str,
    method: str,
    path: str,
    timeout: float,
    payload: dict | None = None,
    params: dict | None = None,
) -> str:
    """Validate at dispatch time and return the canonical selected origin.

    No clock, DNS, credential access, mutation or transport construction. This
    validates request shape, not workflow contents or TLS/server identity.
    Inputs are not retained; callers must not treat this as a reusable permit
    for mutable payload/params. The future transport must call it at dispatch.
    """
    try:
        selected = canonical_origin(origin)
    except (ValueError, TypeError):
        raise ImageProviderError('unsupported', 'Invalid Comfy HTTPS origin') from None
    if type(timeout) not in (int, float):
        raise ImageProviderError('unsupported', 'Invalid Comfy timeout')
    try:
        valid_timeout = math.isfinite(timeout) and timeout > 0
    except OverflowError:
        valid_timeout = False
    if not valid_timeout:
        raise ImageProviderError('unsupported', 'Invalid Comfy timeout')
    # Keep the existing authenticated boundary's narrow route grammar.
    if type(path) is not str or not re.fullmatch(
        r'(?:prompt|view|object_info/[A-Za-z][A-Za-z0-9_]*|history/[a-f0-9-]{36}|api/jobs/[a-f0-9-]{36}/cancel)',
        path,
    ):
        raise ImageProviderError('unsupported', 'Invalid Comfy route')
    expected = 'POST' if path == 'prompt' or path.endswith('/cancel') else 'GET'
    if (
        type(method) is not str
        or method != expected
        or (payload is not None and (path != 'prompt' or type(payload) is not dict))
    ):
        raise ImageProviderError('unsupported', 'Invalid Comfy request')
    if (path == 'view' or params is not None) and (
        path != 'view'
        or type(params) is not dict
        or set(params) != {'filename', 'subfolder', 'type'}
        or any(type(value) is not str for value in params.values())
        or params['subfolder'] != ''
        or params['type'] != 'output'
        or not re.fullmatch(r'animation_sdxl_turbo_[A-Za-z0-9_-]{1,100}\.png', params['filename'])
    ):
        raise ImageProviderError('unsupported', 'Invalid Comfy view parameters')
    return selected
