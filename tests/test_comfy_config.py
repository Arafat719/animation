import json
import logging
from dataclasses import FrozenInstanceError

import httpx
import pytest
from pydantic import SecretStr

from animation_studio.providers.comfy_config import ComfyEndpointConfig

TOKEN = 'synthetic-test-credential'


@pytest.mark.parametrize(
    'origin,expected',
    [
        ('https://COMFY.invalid', 'https://comfy.invalid:443/'),
        ('https://comfy.invalid:443/', 'https://comfy.invalid:443/'),
        ('https://127.0.0.1:8443', 'https://127.0.0.1:8443/'),
        ('https://[2001:0db8::1]', 'https://[2001:db8::1]:443/'),
    ],
)
def test_canonical_origin(origin, expected):
    config = ComfyEndpointConfig(origin=origin, token=SecretStr(TOKEN))
    assert config.origin == expected
    assert config.token.get_secret_value() == TOKEN


@pytest.mark.parametrize(
    'origin',
    [
        'http://host',
        'https://user:synthetic-test-credential@host/',
        'https://host/?token=synthetic-test-credential',
        'https://host/#secret',
        'https://host/path',
        'https://host\r\n',
        'https://host\\path',
        'https://',
        'https://0.0.0.0',
        'https://[::]',
        'https://127.1',
        'https://[::1]other',
        'https://host:65536',
        None,
        123,
    ],
)
def test_invalid_origin_sanitized(origin):
    with pytest.raises(ValueError) as error:
        ComfyEndpointConfig(origin=origin, token=SecretStr(TOKEN))
    assert str(error.value) == 'Invalid Comfy HTTPS origin'
    assert TOKEN not in repr(error.value)


@pytest.mark.parametrize(
    'value', ['', ' ', '\t', '\r', '\n', 'abc\r\nInjected: yes', 'abc def', '\x00', '\x7f', 'বাংলা']
)
def test_invalid_secret(value):
    with pytest.raises(ValueError, match='^Invalid Comfy credential$'):
        ComfyEndpointConfig(origin='https://comfy.invalid', token=SecretStr(value))


@pytest.mark.parametrize('value', [TOKEN, None, 123, b'secret'])
def test_explicit_secret_type(value):
    with pytest.raises(ValueError, match='^Comfy credential must be SecretStr$'):
        ComfyEndpointConfig(origin='https://comfy.invalid', token=value)


def test_repr_logging_export_and_rotation(caplog):
    first = ComfyEndpointConfig(origin='https://comfy.invalid', token=SecretStr(TOKEN))
    rotated = ComfyEndpointConfig(
        origin='https://COMFY.invalid:443/', token=SecretStr('rotated-test')
    )
    with caplog.at_level(logging.INFO):
        logging.getLogger(__name__).info(
            'config=%s repr=%r export=%s', first, first, first.public_config()
        )
    public = json.dumps(first.public_config())
    assert TOKEN not in public + repr(first) + str(first) + caplog.text
    assert 'token' not in first.public_config()
    assert first.public_config() == rotated.public_config()
    assert first == rotated  # Configuration identity excludes credentials.
    assert first.token.get_secret_value() != rotated.token.get_secret_value()
    assert first.public_config() == {
        'origin': 'https://comfy.invalid:443/',
        'verify_tls': True,
        'follow_redirects': False,
        'trust_env': False,
        'retries': 0,
    }
    public_copy = first.public_config()
    public_copy['verify_tls'] = False
    assert first.public_config()['verify_tls'] is True
    with pytest.raises(FrozenInstanceError):
        first.origin = 'https://other.invalid:443/'


def test_no_client_network_environment_or_files(monkeypatch, tmp_path):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('No client/network construction')

    monkeypatch.setattr(httpx, 'Client', forbidden)
    monkeypatch.setattr(httpx, 'AsyncClient', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setenv('COMFY_TOKEN', 'environment-secret')
    monkeypatch.setenv('HTTPS_PROXY', 'https://proxy.invalid')
    monkeypatch.chdir(tmp_path)
    config = ComfyEndpointConfig(origin='https://comfy.invalid', token=SecretStr(TOKEN))
    assert config.token.get_secret_value() == TOKEN
    assert list(tmp_path.iterdir()) == []
    with pytest.raises(TypeError):
        ComfyEndpointConfig(origin='https://comfy.invalid')


@pytest.mark.parametrize(
    'option,value',
    [('verify_tls', False), ('follow_redirects', True), ('trust_env', True), ('retries', 2)],
)
def test_policy_override_not_accepted(option, value):
    with pytest.raises(TypeError):
        ComfyEndpointConfig(
            origin='https://comfy.invalid', token=SecretStr(TOKEN), **{option: value}
        )
