import io
import logging
from urllib.parse import quote

import httpx
import pytest
from pydantic import SecretStr

from animation_studio.providers.gpu_http import HTTPGPUProvider
from animation_studio.providers.gpu_secrets import (
    TOKEN_ENV,
    SecretRedactingFormatter,
    configure_gpu_logging,
    load_gpu_token,
)
from animation_studio.workers.mock_gpu import create_app_from_env


@pytest.mark.parametrize('value', [None, '', ' ', 'has space', 'line\nbreak', 'tab\tkey', 'বাংলা'])
def test_invalid_env_does_not_echo_input(value):
    with pytest.raises(ValueError) as error:
        load_gpu_token({} if value is None else {TOKEN_ENV: value})
    assert str(error.value) == 'ANIMATION_GPU_TOKEN must contain a non-empty printable ASCII token'


def test_explicit_env_and_masked_representation(monkeypatch):
    monkeypatch.setenv(TOKEN_ENV, 'actual-test-secret')
    secret = load_gpu_token()
    assert secret.get_secret_value() == 'actual-test-secret'
    assert 'actual-test-secret' not in str(secret) + repr(secret)
    assert load_gpu_token({TOKEN_ENV: 'isolated-token'}).get_secret_value() == 'isolated-token'
    with pytest.raises(ValueError):
        load_gpu_token({})


@pytest.fixture
def output():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter('%(levelname)s %(message)s %(details)s'))
    logger = logging.getLogger('animation_studio.test_secrets')
    previous = logger.handlers[:], logger.level, logger.propagate
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    # Restore formatters on shared handlers changed by startup helpers.
    handlers = list(logging.getLogger().handlers)
    for item in list(logging.Logger.manager.loggerDict.values()):
        if isinstance(item, logging.Logger):
            handlers.extend(item.handlers)
    originals = [(item, item.formatter) for item in handlers]
    try:
        yield logger, stream, handler
    finally:
        for item, formatter in originals:
            item.setFormatter(formatter)
        logger.handlers, logger.level, logger.propagate = previous
        handler.close()


def test_formatted_args_headers_extra_and_traceback_are_redacted(output):
    logger, stream, _ = output
    token = 'fixture-key/+special'
    configure_gpu_logging(SecretStr(token))
    logger.info(
        'headers=%s encoded=%s',
        {'Authorization': f'Bearer {token}'},
        quote(token, safe=''),
        extra={'details': token},
    )
    try:
        raise RuntimeError(f'connection failed with {token}')
    except RuntimeError:
        logger.exception('failure %s', token, extra={'details': 'retained-detail'})
    text = stream.getvalue()
    assert token not in text and quote(token, safe='') not in text
    assert '[REDACTED]' in text and 'RuntimeError' in text and 'retained-detail' in text
    assert 'INFO headers=' in text


def test_rotation_and_repeated_configuration(output):
    logger, stream, handler = output
    configure_gpu_logging(SecretStr('old-fixture-token'))
    formatter = handler.formatter
    configure_gpu_logging(SecretStr('new-fixture-token'))
    assert handler.formatter is formatter
    logger.warning('old-fixture-token new-fixture-token', extra={'details': 'safe'})
    assert 'old-fixture-token' not in stream.getvalue()
    assert 'new-fixture-token' not in stream.getvalue()


def test_client_environment_token_reaches_wire_but_not_logs(output, monkeypatch):
    logger, stream, _ = output
    token = 'env-fixture-token'
    monkeypatch.setenv(TOKEN_ENV, token)

    def transport(request):
        assert request.headers['Authorization'] == f'Bearer {token}'
        logger.info('request=%s', dict(request.headers), extra={'details': 'wire'})
        return httpx.Response(
            200, json={'healthy': True, 'provider_name': 'mock', 'provider_version': '1'}
        )

    with HTTPGPUProvider.from_env(
        'http://127.0.0.1', transport=httpx.MockTransport(transport)
    ) as client:
        assert client.health_check().healthy
    assert token not in stream.getvalue() and '[REDACTED]' in stream.getvalue()


def test_worker_env_authentication(output, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv(TOKEN_ENV, 'worker-fixture-token')
    with TestClient(create_app_from_env()) as client:
        assert client.get('/health').status_code == 401
        assert (
            client.get(
                '/health', headers={'Authorization': 'Bearer worker-fixture-token'}
            ).status_code
            == 200
        )


@pytest.mark.parametrize(
    'factory', [create_app_from_env, lambda: HTTPGPUProvider.from_env('http://127.0.0.1')]
)
def test_missing_token_fails_startup(monkeypatch, factory):
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    with pytest.raises(ValueError, match=TOKEN_ENV):
        factory()


def test_empty_redaction_secret_rejected():
    with pytest.raises(ValueError):
        SecretRedactingFormatter().add_secret(SecretStr(''))


def test_escaped_header_and_json_values_are_redacted(output):
    import json

    logger, stream, _ = output
    token = 'fixture\\quoted\'"key'
    configure_gpu_logging(SecretStr(token))
    logger.info(
        '%r %s %r',
        {'Authorization': token},
        json.dumps({'token': token}),
        token.encode(),
        extra={'details': 'safe'},
    )
    rendered = stream.getvalue()
    for variant in (token, repr(token)[1:-1], json.dumps(token)[1:-1]):
        assert variant not in rendered
    assert '[REDACTED]' in rendered
