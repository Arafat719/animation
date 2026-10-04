import copy
from threading import Event

import httpx
import pytest
from test_comfy_http import Server

from animation_studio.providers.comfy_checked import CheckedComfyExecutor
from animation_studio.providers.comfy_http import ComfyHTTPExecutor
from animation_studio.providers.comfy_image import ComfyImageProvider
from animation_studio.providers.comfy_preflight import validate_node_inventory
from animation_studio.providers.comfy_workflow import (
    MODEL_NAME,
    MODEL_VERSION,
    build_image_workflow,
)
from animation_studio.providers.image import ImageProviderError, ImageRequest


@pytest.fixture
def request_model():
    return ImageRequest(
        prompt='A house', model_name=MODEL_NAME, model_version=MODEL_VERSION, seed=42
    )


@pytest.fixture
def inventory():
    # Synthetic object_info contract fixture, not a captured running server.
    definitions = {
        'DiffusersLoader': (
            {'model_path': [['other-model', 'sdxl-turbo']]},
            ['MODEL', 'CLIP', 'VAE'],
        ),
        'CLIPTextEncode': (
            {'text': ['STRING', {'multiline': True}], 'clip': ['CLIP']},
            ['CONDITIONING'],
        ),
        'EmptyLatentImage': (
            {'width': ['INT'], 'height': ['INT'], 'batch_size': ['INT']},
            ['LATENT'],
        ),
        'KSampler': (
            {
                'model': ['MODEL'],
                'positive': ['CONDITIONING'],
                'negative': ['CONDITIONING'],
                'latent_image': ['LATENT'],
                'seed': ['INT'],
                'steps': ['INT'],
                'cfg': ['FLOAT'],
                'sampler_name': [['euler', 'other']],
                'scheduler': [['normal']],
                'denoise': ['FLOAT'],
            },
            ['LATENT'],
        ),
        'VAEDecode': ({'samples': ['LATENT'], 'vae': ['VAE']}, ['IMAGE']),
        'SaveImage': ({'images': ['IMAGE'], 'filename_prefix': ['STRING']}, []),
    }
    return {
        kind: {
            'input': {'required': required},
            'output': outputs,
            'output_node': kind == 'SaveImage',
            'is_input_list': False,
            'output_is_list': [False] * len(outputs),
        }
        for kind, (required, outputs) in definitions.items()
    }


@pytest.fixture
def setup(request_model, inventory):
    graph = build_image_workflow(request_model)
    server = Server(graph)

    def respond(request):
        if request.url.path.startswith('/object_info/'):
            kind = request.url.path.rsplit('/', 1)[1]
            return httpx.Response(200, json={kind: inventory[kind]} if kind in inventory else {})

    server.override = respond
    client = ComfyHTTPExecutor(transport=httpx.MockTransport(server))
    yield server, client, graph
    client.close()


def test_preflight_is_read_only(setup):
    server, client, graph = setup
    client.preflight(graph)
    assert len(server.calls) == 6
    assert all(r.method == 'GET' and r.url.path.startswith('/object_info/') for r in server.calls)
    assert sum('CLIPTextEncode' in r.url.path for r in server.calls) == 1


def test_checked_verified_image(setup, request_model, tmp_path, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('No real network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    server, client, _ = setup
    result = ComfyImageProvider(CheckedComfyExecutor(client), tmp_path).generate(request_model)
    assert result.is_mock and result.path.read_bytes() == server.png
    assert [r.method for r in server.calls[:7]] == ['GET'] * 6 + ['POST']


@pytest.mark.parametrize(
    'kind',
    ['DiffusersLoader', 'CLIPTextEncode', 'EmptyLatentImage', 'KSampler', 'VAEDecode', 'SaveImage'],
)
def test_missing_nodes_block_submit(setup, inventory, kind):
    server, client, graph = setup
    del inventory[kind]
    with pytest.raises(ImageProviderError) as caught:
        CheckedComfyExecutor(client).execute(graph)
    assert caught.value.code == 'unsupported'
    assert all(r.method == 'GET' for r in server.calls)


@pytest.mark.parametrize(
    'change',
    [
        'alias',
        'alias_substring',
        'sampler',
        'scheduler',
        'output_order',
        'input_type',
        'missing_input',
        'new_required',
        'output_node',
        'output_bool',
        'input_list',
        'output_list',
        'bad_options',
        'null_node',
        'malformed_combo',
    ],
)
def test_incompatible_inventory_blocks_submit(setup, inventory, change):
    server, client, graph = setup
    loader = inventory['DiffusersLoader']
    sampler = inventory['KSampler']['input']['required']
    if change == 'alias':
        loader['input']['required']['model_path'] = [['different']]
    elif change == 'alias_substring':
        loader['input']['required']['model_path'] = ['prefix-sdxl-turbo']
    elif change in ('sampler', 'scheduler'):
        sampler['sampler_name' if change == 'sampler' else 'scheduler'] = [['absent']]
    elif change == 'output_order':
        loader['output'] = ['CLIP', 'MODEL', 'VAE']
    elif change == 'input_type':
        sampler['seed'] = ['STRING']
    elif change == 'missing_input':
        del sampler['cfg']
    elif change == 'new_required':
        sampler['unexpected'] = ['STRING']
    elif change == 'output_node':
        inventory['SaveImage']['output_node'] = False
    elif change == 'output_bool':
        inventory['SaveImage']['output_node'] = 1
    elif change == 'input_list':
        loader['is_input_list'] = True
    elif change == 'output_list':
        loader['output_is_list'] = [0, 0, 0]
    elif change == 'bad_options':
        sampler['seed'] = ['INT', []]
    elif change == 'null_node':
        inventory['VAEDecode'] = None
    else:
        loader['input']['required']['model_path'] = [[123, 'sdxl-turbo']]
    with pytest.raises(ImageProviderError):
        CheckedComfyExecutor(client).execute(graph)
    assert all(r.method == 'GET' for r in server.calls)


def test_preflight_not_cached(setup, inventory):
    server, client, graph = setup
    checked = CheckedComfyExecutor(client)
    checked.execute(graph)
    count = len(server.calls)
    inventory['DiffusersLoader']['input']['required']['model_path'] = [[]]
    with pytest.raises(ImageProviderError):
        checked.execute(graph)
    assert all(r.method == 'GET' for r in server.calls[count:])
    assert sum(r.url.path == '/prompt' for r in server.calls) == 1


@pytest.mark.parametrize('case', ['http', 'malformed', 'timeout', 'cancel'])
def test_preflight_failures_never_submit(setup, case):
    server, client, graph = setup
    cancel = Event()

    def fail(request):
        if case == 'timeout':
            raise httpx.ReadTimeout('private', request=request)
        if case == 'cancel':
            cancel.set()
            return httpx.Response(200, json={})
        if case == 'http':
            return httpx.Response(503)
        return httpx.Response(200, headers={'content-type': 'application/json'}, content=b'{')

    server.override = fail
    with pytest.raises(ImageProviderError):
        CheckedComfyExecutor(client).execute(graph, cancel=cancel)
    assert len(server.calls) == 1 and server.calls[0].method == 'GET'


def test_cancel_before_preflight(setup):
    server, client, graph = setup
    cancel = Event()
    cancel.set()
    with pytest.raises(ImageProviderError):
        CheckedComfyExecutor(client).execute(graph, cancel=cancel)
    assert not server.calls


def test_extra_unrelated_inventory_allowed(request_model, inventory):
    original = copy.deepcopy(inventory)
    inventory['UnusedNode'] = {}
    validate_node_inventory(build_image_workflow(request_model), inventory)
    del inventory['UnusedNode']
    assert inventory == original
