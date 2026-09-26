"""Mock-only RunPod Pods adapter skeleton; no provision/start/stop operations."""

import math
import re
from typing import Literal

import httpx
from pydantic import Field, SecretStr, ValidationError

from animation_studio.providers.gpu import Contract, GPUProviderError
from animation_studio.providers.gpu_http import HTTPGPUProvider


class PodSnapshot(Contract):
    pod_id: str = Field(min_length=1)
    desired_status: Literal['RUNNING', 'EXITED', 'TERMINATED', 'UNKNOWN']
    # Desired state is not proof of readiness, actual compute state or billing.


class RunPodGPUProvider(HTTPGPUProvider):
    """GPUProvider over the project worker on a Pod, with separate API credentials.

    Only injected MockTransports are accepted in Phase 4.6. REST v1 metadata is
    read-only, single-attempt; worker retries retain the existing HTTP contract.
    No Serverless /run translation, cloud mutations, or readiness inference.
    """

    def __init__(
        self,
        *,
        pod_id: str,
        worker_port: int,
        api_key: SecretStr,
        worker_token: SecretStr,
        control_transport: httpx.MockTransport,
        worker_transport: httpx.MockTransport,
    ):
        if not isinstance(pod_id, str) or not re.fullmatch(r'[a-z0-9]{1,64}', pod_id):
            raise ValueError('Invalid Pod ID')
        if type(worker_port) is not int or not 1 <= worker_port <= 65535:
            raise ValueError('Invalid worker port')
        if not isinstance(control_transport, httpx.MockTransport) or not isinstance(
            worker_transport, httpx.MockTransport
        ):
            raise TypeError('RunPod skeleton requires mock transports')
        for secret in (api_key, worker_token):
            if not isinstance(secret, SecretStr):
                raise TypeError('Credentials must be SecretStr')
            value = secret.get_secret_value()
            if not value or any(ord(c) < 33 or ord(c) > 126 for c in value):
                raise ValueError('Invalid credential')
        super().__init__(
            f'https://{pod_id}-{worker_port}.proxy.runpod.net',
            token=worker_token.get_secret_value(),
            transport=worker_transport,
        )
        self._pod_id = pod_id
        self._control = httpx.Client(
            base_url='https://rest.runpod.io/v1/',
            headers={'Authorization': f'Bearer {api_key.get_secret_value()}'},
            transport=control_transport,
            follow_redirects=False,
            trust_env=False,
        )

    @classmethod
    def from_env(cls, *args, **kwargs):
        raise ValueError(
            'RunPod skeleton requires explicit fixture credentials and mock transports'
        )

    def pod_snapshot(self, *, timeout_seconds: float = 10) -> PodSnapshot:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise GPUProviderError('invalid_input', 'Invalid Pod lookup timeout')
        try:
            response = self._control.get(f'pods/{self._pod_id}', timeout=timeout_seconds)
        except httpx.TimeoutException:
            raise GPUProviderError('timeout', 'Pod lookup timed out') from None
        except httpx.TransportError:
            raise GPUProviderError('unavailable', 'Pod lookup unavailable') from None
        if response.status_code != 200:
            code = {
                401: 'unauthorized',
                403: 'unauthorized',
                404: 'not_found',
                429: 'unavailable',
                502: 'unavailable',
                503: 'unavailable',
                504: 'timeout',
            }.get(response.status_code, 'invalid_response')
            raise GPUProviderError(code, 'Pod lookup rejected')
        try:
            data = response.json()
            if not isinstance(data, dict) or data.get('id') != self._pod_id:
                raise ValueError('Mismatched Pod')
            state = data['desiredStatus']
            if not isinstance(state, str) or not state:
                raise ValueError('Missing desired state')
            return PodSnapshot(
                pod_id=self._pod_id,
                desired_status=(
                    state if state in ('RUNNING', 'EXITED', 'TERMINATED') else 'UNKNOWN'
                ),
            )
        except (ValueError, KeyError, ValidationError):
            raise GPUProviderError('invalid_response', 'Invalid Pod response') from None

    def close(self):
        try:
            super().close()
        finally:
            self._control.close()
