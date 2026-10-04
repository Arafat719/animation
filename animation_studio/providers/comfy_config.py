"""Offline endpoint/auth configuration. Construction never creates a client."""

from dataclasses import dataclass, field

from pydantic import SecretStr

from animation_studio.providers.comfy_identity import canonical_origin


@dataclass(frozen=True, slots=True, init=False)
class ComfyEndpointConfig:
    """Explicit HTTPS endpoint and in-memory credential for future transport.

    SecretStr must be supplied by the caller; no environment lookup or token
    refresh. public_config() is the supported nonsecret export. Policy values
    describe requirements for a future client, not a running TLS/auth check.
    """

    origin: str
    token: SecretStr = field(repr=False, compare=False)

    def __init__(self, *, origin: str, token: SecretStr):
        try:
            normalized = canonical_origin(origin)
        except (ValueError, TypeError):
            raise ValueError('Invalid Comfy HTTPS origin') from None
        if type(token) is not SecretStr:
            raise ValueError('Comfy credential must be SecretStr')
        value = token.get_secret_value()
        # Header-safe opaque token: no whitespace, controls or non-ASCII bytes.
        if not value or any(not 33 <= ord(char) <= 126 for char in value):
            raise ValueError('Invalid Comfy credential')
        object.__setattr__(self, 'origin', normalized)
        object.__setattr__(self, 'token', token)

    def public_config(self) -> dict:
        """No credential, credential hash or Authorization header is exported."""
        return {
            'origin': self.origin,
            'verify_tls': True,
            'follow_redirects': False,
            'trust_env': False,
            'retries': 0,
        }
