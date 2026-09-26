"""Synchronous HTTP GPU boundary with bounded retries and replay-safe submission."""

import math
import re
import time
from urllib.parse import quote
from uuid import uuid4

import httpx
from pydantic import BaseModel, ValidationError

from animation_studio.providers.gpu import (
    GPUCapabilities,
    GPUHealth,
    GPUJob,
    GPUJobRequest,
    GPUProviderError,
)


class HTTPGPUProvider:
    """Use only workers implementing the idempotency contract.

    One generated key per submit call is reused for all internal retries. Callers
    retrying after an ambiguous failure must retain and supply their own key.
    Timeouts bound each I/O phase; elapsed budget is also checked before retries
    and after responses. This is not a hard wall-clock interrupt of slow streams.
    close() or a context manager releases the client. Redirects/proxies disabled.
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str,
        max_retries: int = 2,
        backoff_seconds: float = 0.1,
        transport: httpx.BaseTransport | None = None,
    ):
        url = httpx.URL(base_url)
        if (
            url.scheme not in ('http', 'https')
            or not url.host
            or url.userinfo
            or url.query
            or url.fragment
            or url.path not in ('', '/')
            or (url.scheme == 'http' and url.host not in ('127.0.0.1', 'localhost', '::1'))
        ):
            raise ValueError('Use HTTPS or loopback HTTP with an origin-only URL')
        if not token or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise ValueError('A printable non-empty token is required')
        if type(max_retries) is not int or not 0 <= max_retries <= 5:
            raise ValueError('max_retries must be between 0 and 5')
        if (
            isinstance(backoff_seconds, bool)
            or not isinstance(backoff_seconds, (int, float))
            or not math.isfinite(backoff_seconds)
            or not 0 <= backoff_seconds <= 10
        ):
            raise ValueError('Invalid backoff')
        self._client = httpx.Client(
            base_url=base_url,
            headers={'Authorization': f'Bearer {token}'},
            transport=transport,
            trust_env=False,
            follow_redirects=False,
        )
        self._retries = max_retries
        self._backoff = backoff_seconds

    @classmethod
    def from_env(
        cls,
        base_url: str,
        *,
        max_retries: int = 2,
        backoff_seconds: float = 0.1,
        transport: httpx.BaseTransport | None = None,
    ):
        """Load the worker token and protect currently configured log handlers."""
        from animation_studio.providers.gpu_secrets import configure_gpu_logging, load_gpu_token

        secret = load_gpu_token()
        configure_gpu_logging(secret)
        return cls(
            base_url,
            token=secret.get_secret_value(),
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            transport=transport,
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _call(
        self,
        method: str,
        path: str,
        model: type[BaseModel],
        *,
        timeout_seconds: float,
        payload=None,
        key: str | None = None,
    ):
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise GPUProviderError('invalid_input', 'Timeout must be positive and finite')
        deadline = time.monotonic() + timeout_seconds
        code = 'unavailable'
        for attempt in range(self._retries + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise GPUProviderError('timeout', 'Worker request budget exhausted')
            try:
                response = self._client.request(
                    method,
                    path,
                    json=payload,
                    headers={} if key is None else {'Idempotency-Key': key},
                    timeout=remaining,
                )
            except httpx.TimeoutException:
                code = 'timeout'
            except httpx.TransportError:
                code = 'unavailable'
            else:
                if time.monotonic() >= deadline:
                    raise GPUProviderError('timeout', 'Worker request budget exhausted')
                if response.status_code in (429, 502, 503, 504):
                    code = 'timeout' if response.status_code == 504 else 'unavailable'
                elif response.status_code == (202 if path == '/jobs' else 200):
                    try:
                        return model.model_validate_json(response.content)
                    except ValidationError:
                        raise GPUProviderError(
                            'invalid_response', 'Invalid worker response'
                        ) from None
                else:
                    code = {
                        401: 'unauthorized',
                        403: 'unauthorized',
                        404: 'not_found',
                        409: 'idempotency_conflict',
                        422: 'invalid_input',
                    }.get(response.status_code, 'invalid_response')
                    if response.status_code == 422:
                        try:
                            if response.json().get('detail', {}).get('code') == 'unsupported':
                                code = 'unsupported'
                        except (ValueError, AttributeError):
                            pass
                    raise GPUProviderError(code, 'Worker rejected request')
            if attempt == self._retries:
                break
            delay = self._backoff * 2**attempt
            if delay >= deadline - time.monotonic():
                raise GPUProviderError('timeout', 'Worker retry budget exhausted')
            time.sleep(delay)
        raise GPUProviderError(code, 'Worker request attempts exhausted')

    def health_check(self, *, timeout_seconds: float = 10) -> GPUHealth:
        return self._call('GET', '/health', GPUHealth, timeout_seconds=timeout_seconds)

    def capabilities(self, *, timeout_seconds: float = 10) -> GPUCapabilities:
        return self._call('GET', '/capabilities', GPUCapabilities, timeout_seconds=timeout_seconds)

    def submit(
        self,
        request: GPUJobRequest,
        *,
        timeout_seconds: float = 10,
        idempotency_key: str | None = None,
    ) -> GPUJob:
        if not isinstance(request, GPUJobRequest):
            raise GPUProviderError('invalid_input', 'Expected GPUJobRequest')
        key = uuid4().hex if idempotency_key is None else idempotency_key
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,128}', key):
            raise GPUProviderError('invalid_input', 'Invalid idempotency key')
        job = self._call(
            'POST',
            '/jobs',
            GPUJob,
            payload=request.model_dump(),
            key=key,
            timeout_seconds=timeout_seconds,
        )
        if job.request != request:
            raise GPUProviderError('invalid_response', 'Worker returned a different request')
        return job

    @staticmethod
    def _job_id(job_id: str) -> str:
        if not isinstance(job_id, str) or not job_id.strip() or len(job_id) > 4000:
            raise GPUProviderError('invalid_input', 'Invalid job ID')
        if job_id in ('.', '..') or '/' in job_id:
            raise GPUProviderError('invalid_input', 'Invalid job ID')
        return job_id

    def status(self, job_id: str, *, timeout_seconds: float = 10) -> GPUJob:
        job_id = self._job_id(job_id)
        job = self._call(
            'GET', '/jobs/' + quote(job_id, safe=''), GPUJob, timeout_seconds=timeout_seconds
        )
        if job.job_id != job_id:
            raise GPUProviderError('invalid_response', 'Worker returned a different job')
        return job

    def cancel(self, job_id: str, *, timeout_seconds: float = 10) -> GPUJob:
        job_id = self._job_id(job_id)
        job = self._call(
            'POST', '/cancel', GPUJob, payload={'job_id': job_id}, timeout_seconds=timeout_seconds
        )
        if job.job_id != job_id:
            raise GPUProviderError('invalid_response', 'Worker returned a different job')
        return job
