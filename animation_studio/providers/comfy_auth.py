"""Selected-origin bearer request boundary, restricted to mock transport."""

from contextlib import contextmanager

import httpx

from animation_studio.providers.comfy_config import ComfyEndpointConfig
from animation_studio.providers.comfy_request_policy import validate_comfy_request
from animation_studio.providers.image import ImageProviderError


class MockComfyAuthenticatedClient:
    """No live sockets, retries, redirects or ambient proxy/auth configuration.

    Returned bytes still require workflow/MIME/media validation by a caller.
    Caller owns close(). Injected mock handlers are trusted and can see headers.
    """

    is_mock = True

    def __init__(self, config: ComfyEndpointConfig, *, transport: httpx.MockTransport):
        if type(config) is not ComfyEndpointConfig or type(transport) is not httpx.MockTransport:
            raise TypeError('Expected explicit config and MockTransport')
        self._config = ComfyEndpointConfig(origin=config.origin, token=config.token)
        self._client = httpx.Client(
            base_url=self._config.origin,
            transport=transport,
            verify=True,
            follow_redirects=False,
            trust_env=False,
            timeout=10,
            headers={'Accept-Encoding': 'identity'},
        )

    def close(self):
        self._client.close()

    @property
    def origin(self):
        return self._config.origin

    @contextmanager
    def stream(self, method, path, *, timeout=10, json=None, params=None):
        payload = json
        validate_comfy_request(
            origin=self.origin,
            method=method,
            path=path,
            timeout=timeout,
            payload=payload,
            params=params,
        )
        try:
            with self._client.stream(
                method,
                path,
                json=payload,
                params=params,
                timeout=timeout,
                headers={'Authorization': 'Bearer ' + self._config.token.get_secret_value()},
            ) as response:
                if response.status_code != 200:
                    raise ImageProviderError('execution_failed', 'Comfy request rejected')
                if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                    raise ImageProviderError('execution_failed', 'Compressed response unsupported')
                yield response
        except httpx.TimeoutException:
            raise ImageProviderError(
                'timeout', 'Comfy request timed out; outcome unknown'
            ) from None
        except httpx.TransportError:
            raise ImageProviderError(
                'execution_failed', 'Comfy transport failed; outcome unknown'
            ) from None

    def request(self, method: str, path: str, *, payload: dict | None = None) -> bytes:
        with self.stream(method, path, json=payload) as response:
            content = bytearray()
            for chunk in response.iter_bytes(chunk_size=65536):
                if len(content) + len(chunk) > 16 * 1024 * 1024:
                    raise ImageProviderError('execution_failed', 'Comfy response too large')
                content.extend(chunk)
            return bytes(content)
