"""Explicit standalone HTTPS transport. No workflow, journal or live app wiring."""

import math
import time
from dataclasses import dataclass

import httpx

from animation_studio.providers.comfy_config import ComfyEndpointConfig
from animation_studio.providers.comfy_request_policy import validate_comfy_request
from animation_studio.providers.image import ImageProviderError

MAX_RESPONSE_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class ComfyTransportResponse:
    content: bytes
    content_type: str


def _config(config):
    if type(config) is not ComfyEndpointConfig:
        raise ValueError('Expected explicit Comfy endpoint config')
    return ComfyEndpointConfig(origin=config.origin, token=config.token)


def create_comfy_transport(config: ComfyEndpointConfig):
    """Construct an owned TLS client without dispatch; no injected production client."""
    config = _config(config)
    transport = httpx.HTTPTransport(verify=True, trust_env=False, retries=0)
    try:
        return ComfyTransport(config, transport, is_mock=False)
    except BaseException as primary:
        try:
            transport.close()
        except Exception:  # noqa: BLE001 — preserve primary and retain owned resource.
            primary.cleanup_handle = transport
        raise


def create_mock_comfy_transport(config: ComfyEndpointConfig, *, transport: httpx.MockTransport):
    """Offline factory; injected handlers are trusted and can see synthetic tokens."""
    config = _config(config)
    if type(transport) is not httpx.MockTransport:
        raise TypeError('Expected exact MockTransport')
    return ComfyTransport(config, transport, is_mock=True)


class ComfyTransport:
    """Single-owner synchronous byte boundary; parser/media checks remain upstream.

    Request failure never retries. close() blocks further requests immediately;
    failed cleanup retains this object on error.cleanup_handle for later close().
    This is cooperative I/O timing, not an independent hard wall-clock supervisor.
    """

    def __init__(self, config, transport, *, is_mock):
        config = _config(config)
        expected = httpx.MockTransport if is_mock is True else httpx.HTTPTransport
        if type(is_mock) is not bool or type(transport) is not expected:
            raise TypeError('Invalid transport provenance')
        self._transport = transport
        self._close_attempted = False
        self._config = config
        self._is_mock = is_mock
        self._closed = False
        self._client_closed = False
        self._pending_streams = []
        self._client = httpx.Client(
            base_url=config.origin,
            transport=transport,
            verify=True,
            trust_env=False,
            follow_redirects=False,
            timeout=10,
            headers={'Accept-Encoding': 'identity'},
        )

    @property
    def is_mock(self):
        return self._is_mock

    def require_mock(self):
        # Recheck at composition and dispatch, not just a caller-writable label.
        if self.is_mock is not True or type(self._transport) is not httpx.MockTransport:
            raise TypeError('Expected offline mock transport')

    @property
    def origin(self):
        return self._config.origin

    def _cleanup_error(self):
        error = ImageProviderError('execution_failed', 'Comfy cleanup incomplete')
        error.cleanup_handle = self
        return error

    def close(self):
        self._closed = True
        failed = []
        for stream in self._pending_streams:
            try:
                stream.close()
            except Exception:  # noqa: BLE001 — bounded error with retained cleanup handle.
                failed.append(stream)
        self._pending_streams = failed
        if not self._client_closed:
            try:
                if self._close_attempted:
                    self._transport.close()
                else:
                    self._close_attempted = True
                    self._client.close()
                self._client_closed = True
            except Exception:  # noqa: BLE001 — retry underlying close after HTTPX marks closed.
                # HTTPX marks the client closed before the owned transport closes.
                self._closed = True
                raise self._cleanup_error() from None
        if failed:
            raise self._cleanup_error() from None

    def request(
        self,
        method,
        path,
        *,
        deadline,
        timeout=10,
        payload=None,
        params=None,
        cancel=None,
        limit=None,
        mime=None,
    ):
        """Return bounded bytes, requiring caller JSON/MIME/media validation later."""
        if limit is None:
            limit = MAX_RESPONSE_BYTES
        if type(limit) is not int or not 0 < limit <= MAX_RESPONSE_BYTES:
            raise ValueError('Invalid response byte limit')
        if mime is not None and mime not in ('application/json', 'image/png'):
            raise ValueError('Invalid expected response MIME')
        if self._closed:
            raise ImageProviderError('unsupported', 'Comfy transport is closed')
        validate_comfy_request(
            origin=self.origin,
            method=method,
            path=path,
            timeout=timeout,
            payload=payload,
            params=params,
        )
        try:
            valid = type(deadline) in (int, float) and math.isfinite(deadline) and deadline >= 0
        except OverflowError:
            valid = False
        if not valid:
            raise ImageProviderError('unsupported', 'Invalid Comfy deadline')

        def check():
            if cancel is not None and cancel.is_set():
                raise ImageProviderError('cancelled', 'Comfy request cancelled; outcome unknown')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ImageProviderError('timeout', 'Comfy deadline exceeded; outcome unknown')
            return remaining

        response = None
        primary = None
        content = bytearray()
        try:
            budget = min(timeout, check())
            request = self._client.build_request(
                method,
                path,
                json=payload,
                params=params,
                timeout=budget,
                headers={'Authorization': 'Bearer ' + self._config.token.get_secret_value()},
            )
            check()
            response = self._client.send(request, stream=True)
            check()
            if response.status_code != 200:
                raise ImageProviderError('execution_failed', 'Comfy request rejected')
            if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                raise ImageProviderError('execution_failed', 'Compressed response unsupported')
            if (
                mime is not None
                and response.headers.get('content-type', '').split(';')[0].strip() != mime
            ):
                raise ImageProviderError('execution_failed', 'Unexpected response content type')
            declared = response.headers.get('content-length')
            if declared is not None and (
                not declared.isascii()
                or not declared.isdecimal()
                or len(declared) > 10
                or int(declared) > limit
            ):
                raise ImageProviderError(
                    'execution_failed', 'Comfy response too large; response byte limit exceeded'
                )
            iterator = response.iter_bytes(chunk_size=65536)
            while True:
                check()
                try:
                    chunk = next(iterator)
                except StopIteration:
                    break
                check()
                if len(content) + len(chunk) > limit:
                    raise ImageProviderError(
                        'execution_failed', 'Comfy response too large; response byte limit exceeded'
                    )
                content.extend(chunk)
        except httpx.TimeoutException:
            primary = ImageProviderError('timeout', 'Comfy request timed out; outcome unknown')
        except (httpx.TransportError, OSError):
            primary = ImageProviderError(
                'execution_failed', 'Comfy transport failed; outcome unknown'
            )
        except BaseException as error:  # noqa: BLE001 — re-raised after owned cleanup.
            primary = error
        finally:
            if response is not None:
                try:
                    response.stream.close()
                except Exception:  # noqa: BLE001 — retain resource, preserve primary error.
                    self._pending_streams.append(response.stream)
                    self._closed = True
                    if primary is None:
                        primary = self._cleanup_error()
                    else:
                        primary.cleanup_handle = self
        if primary is not None:
            raise primary from None
        return ComfyTransportResponse(bytes(content), response.headers.get('content-type', ''))
