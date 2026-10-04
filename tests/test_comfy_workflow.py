import json
from pathlib import Path

import pytest

from animation_studio.providers.comfy_workflow import (
    MODEL_NAME,
    MODEL_VERSION,
    build_image_workflow,
    load_image_workflow,
    validate_image_workflow,
)
from animation_studio.providers.image import ImageRequest


@pytest.fixture
def request_model():
    return ImageRequest(
        prompt='নদীর পাশে বাড়ি', model_name=MODEL_NAME, model_version=MODEL_VERSION, seed=42
    )


def test_roundtrip_and_independence(request_model):
    graph = build_image_workflow(request_model)
    assert validate_image_workflow(load_image_workflow(json.dumps(graph))) == request_model
    graph['2']['inputs']['text'] = 'changed'
    assert build_image_workflow(request_model)['2']['inputs']['text'] == request_model.prompt


def test_checked_in_api_graph():
    path = Path(__file__).resolve().parents[1] / 'workflows/sdxl-turbo-api.json'
    graph = load_image_workflow(path.read_text())
    assert graph['7']['class_type'] == 'SaveImage'
    assert graph['5']['inputs']['seed'] == 42
    assert len(graph) == 7


@pytest.mark.parametrize(
    'node,field,value',
    [
        ('5', 'model', ['missing', 0]),
        ('5', 'model', ['1', 2]),
        ('5', 'latent_image', ['5', 0]),
        ('6', 'samples', ['7', 0]),
        ('5', 'seed', True),
        ('5', 'seed', -1),
        ('5', 'steps', 20),
        ('5', 'cfg', float('nan')),
        ('4', 'width', 1024),
        ('4', 'batch_size', 2),
        ('1', 'model_path', '/tmp/model'),
        ('1', 'model_path', '../model'),
        ('7', 'filename_prefix', '../escape'),
        ('2', 'text', ''),
        ('5', 'scheduler', 'unknown'),
        ('5', 'model', ['1', False]),
    ],
)
def test_invalid_graph(request_model, node, field, value):
    graph = build_image_workflow(request_model)
    graph[node]['inputs'][field] = value
    with pytest.raises(ValueError):
        validate_image_workflow(graph)


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'class', 'input'])
def test_reject_graph_changes(request_model, mutation):
    graph = build_image_workflow(request_model)
    if mutation == 'missing':
        del graph['7']
    elif mutation == 'extra':
        graph['8'] = graph['7']
    elif mutation == 'class':
        graph['1']['class_type'] = 'CustomLoader'
    else:
        graph['5']['inputs']['extra'] = 1
    with pytest.raises(ValueError):
        validate_image_workflow(graph)


@pytest.mark.parametrize('raw', ['{}', '[]', '{', '{"1": {}, "1": {}}'])
def test_invalid_json(raw):
    with pytest.raises(ValueError):
        load_image_workflow(raw)


@pytest.mark.parametrize(
    'field,value', [('model_name', 'fixture-image'), ('model_version', 'main')]
)
def test_wrong_model(request_model, field, value):
    with pytest.raises(ValueError):
        build_image_workflow(request_model.model_copy(update={field: value}))


def test_offline(monkeypatch, request_model):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('Network must not be used')

    monkeypatch.setattr(socket, 'socket', forbidden)
    assert validate_image_workflow(build_image_workflow(request_model)) == request_model
