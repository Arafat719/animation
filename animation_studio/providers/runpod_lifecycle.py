"""Single-Pod REST lifecycle contract; injected mock transport only."""

import math
import re
from dataclasses import dataclass

import httpx
from pydantic import SecretStr

from animation_studio.providers.gpu import GPUProviderError


@dataclass(frozen=True)
class PodObservation:
    pod_id: str
    present: bool
    desired_status: str | None
    # Desired state and absence do not prove compute/storage billing has ended.


class RunPodLifecycle:
    """Single-attempt requests. Mutation acknowledgements require later inspection.

    Mock cleanup bridge supported. No provisioning, retries or live transport.
    Timeouts bound individual I/O phases, not total wall-clock execution.
    """

    def __init__(self, *, pod_id: str, api_key: SecretStr, transport: httpx.MockTransport):
        if not isinstance(pod_id, str) or not re.fullmatch(r'[a-z0-9]{1,64}', pod_id):
            raise ValueError('Invalid Pod ID')
        if not isinstance(transport, httpx.MockTransport):
            raise TypeError('Lifecycle requires mock transport')
        if not isinstance(api_key, SecretStr):
            raise TypeError('Credential must be SecretStr')
        value = api_key.get_secret_value()
        if not value or any(ord(c) < 33 or ord(c) > 126 for c in value):
            raise ValueError('Invalid credential')
        self._pod_id = pod_id
        self._client = httpx.Client(
            base_url='https://rest.runpod.io/v1/',
            headers={'Authorization': f'Bearer {value}'},
            transport=transport,
            follow_redirects=False,
            trust_env=False,
        )

    @property
    def pod_id(self) -> str:
        return self._pod_id

    def _request(self, method: str, suffix: str, timeout_seconds: float) -> httpx.Response:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise GPUProviderError('invalid_input', 'Invalid lifecycle timeout')
        try:
            return self._client.request(
                method,
                f'pods/{self._pod_id}{suffix}',
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException:
            raise GPUProviderError('timeout', 'Lifecycle outcome unknown after timeout') from None
        except httpx.TransportError:
            raise GPUProviderError('unavailable', 'Lifecycle outcome unknown') from None

    @staticmethod
    def _expect(response: httpx.Response, status: int):
        if response.status_code != status:
            code = {
                401: 'unauthorized',
                403: 'unauthorized',
                404: 'not_found',
                429: 'unavailable',
                502: 'unavailable',
                503: 'unavailable',
                504: 'timeout',
            }.get(response.status_code, 'invalid_response')
            raise GPUProviderError(code, 'Lifecycle request rejected')

    def inspect(self, *, timeout_seconds: float = 10) -> PodObservation:
        response = self._request('GET', '', timeout_seconds)
        if response.status_code == 404:
            return PodObservation(self._pod_id, False, None)
        self._expect(response, 200)
        try:
            data = response.json()
            if not isinstance(data, dict) or data.get('id') != self._pod_id:
                raise ValueError
            desired = data['desiredStatus']
            if not isinstance(desired, str) or not desired.strip():
                raise ValueError
        except (ValueError, KeyError):
            raise GPUProviderError('invalid_response', 'Invalid lifecycle observation') from None
        return PodObservation(self._pod_id, True, desired)

    def stop(self, *, timeout_seconds: float = 10) -> None:
        self._expect(self._request('POST', '/stop', timeout_seconds), 200)

    def terminate(self, *, timeout_seconds: float = 10) -> None:
        self._expect(self._request('DELETE', '', timeout_seconds), 204)

    def close(self) -> None:
        self._client.close()
