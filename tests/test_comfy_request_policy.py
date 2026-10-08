import copy
import socket
import traceback

import httpx
import pytest

from animation_studio.providers.comfy_request_policy import validate_comfy_request
from animation_studio.providers.image import ImageProviderError

JOB = '12345678-1234-4234-8234-123456789abc'
VIEW = {'filename': 'animation_sdxl_turbo_test.png', 'subfolder': '', 'type': 'output'}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Pure policy must not construct a client or use network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setattr(httpx, 'Client', forbidden)


def validate(**changes):
    return validate_comfy_request(
        **{
            'origin': 'https://Selected.invalid',
            'method': 'GET',
            'path': 'object_info/SaveImage',
            'timeout': 10,
            **changes,
        }
    )


@pytest.mark.parametrize(
    'method,path,payload,params',
    [
        ('GET', 'object_info/SaveImage', None, None),
        ('GET', 'history/' + JOB, None, None),
        ('GET', 'view', None, VIEW),
        ('POST', 'prompt', {'prompt': {}}, None),
        ('POST', 'api/jobs/' + JOB + '/cancel', None, None),
    ],
)
def test_allowed_routes_without_io_or_mutation(method, path, payload, params):
    before = copy.deepcopy((payload, params))
    assert (
        validate(method=method, path=path, payload=payload, params=params)
        == 'https://selected.invalid:443/'
    )
    assert (payload, params) == before


@pytest.mark.parametrize(
    'origin',
    [
        'http://selected.invalid',
        'https://user:secret@selected.invalid',
        'https://selected.invalid/base',
        'https://selected.invalid?secret',
        'https://selected.invalid#secret',
        'https://selected.invalid:0',
        '//selected.invalid',
        '',
        None,
        True,
    ],
)
def test_invalid_origin(origin):
    with pytest.raises(ImageProviderError) as caught:
        validate(origin=origin)
    assert caught.value.code == 'unsupported'


@pytest.mark.parametrize(
    'timeout', [None, True, False, '10', 0, -1, float('nan'), float('inf'), -float('inf'), 10**1000]
)
def test_invalid_timeout(timeout):
    with pytest.raises(ImageProviderError, match='Invalid Comfy timeout'):
        validate(timeout=timeout)


@pytest.mark.parametrize('timeout', [1, 0.01, 1e100])
def test_positive_finite_timeout(timeout):
    validate(timeout=timeout)


@pytest.mark.parametrize(
    'path',
    [
        'https://foreign.invalid/prompt',
        '//foreign.invalid/view',
        '/view',
        '../view',
        'view?secret=x',
        'view#secret',
        'view\\x',
        'view\n',
        'view%2f',
        'object_info/../SaveImage',
        'object_info/',
        'history/short',
        'api/jobs/cancel',
        'interrupt',
        'queue',
        '',
        None,
        True,
    ],
)
def test_route_injection(path):
    with pytest.raises(ImageProviderError, match='Invalid Comfy route'):
        validate(path=path)


@pytest.mark.parametrize(
    'changes',
    [
        {'method': 'POST'},
        {'method': 'get'},
        {'method': None},
        {'method': True},
        {'payload': {}},
        {'path': 'prompt', 'method': 'POST', 'payload': []},
        {'params': {}},
        {'path': 'view'},
        {'path': 'view', 'params': {}},
        {'path': 'view', 'params': VIEW | {'extra': 'secret'}},
        {'path': 'view', 'params': VIEW | {'filename': '../secret.png'}},
        {'path': 'view', 'params': VIEW | {'subfolder': 'secret'}},
        {'path': 'view', 'params': VIEW | {'type': 'input'}},
        {'path': 'view', 'params': VIEW | {'filename': None}},
        {'path': 'view', 'params': VIEW | {'type': True}},
    ],
)
def test_request_shape_rejected(changes):
    with pytest.raises(ImageProviderError) as caught:
        validate(**changes)
    assert caught.value.code == 'unsupported'


def test_public_failure_does_not_echo_input():
    secret = 'synthetic-private-value'
    for changes in (
        {'origin': 'https://u:' + secret + '@host.invalid'},
        {'path': 'view?' + secret},
        {'timeout': secret},
        {'params': {'secret': secret}},
    ):
        with pytest.raises(ImageProviderError) as caught:
            validate(**changes)
        assert secret not in ''.join(traceback.format_exception(caught.value))


def test_private_selected_origin_allowed():
    assert validate(origin='https://127.0.0.1:8443') == 'https://127.0.0.1:8443/'


def test_no_validation_permit_for_mutated_params():
    params = dict(VIEW)
    validate(path='view', params=params)
    params['filename'] = '../secret'
    with pytest.raises(ImageProviderError):
        validate(path='view', params=params)
