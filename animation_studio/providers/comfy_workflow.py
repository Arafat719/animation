"""Offline builder/validator for one deliberately narrow ComfyUI API graph.

This validates our SDXL-Turbo profile, not arbitrary ComfyUI workflows or a live
server's node/model inventory. It never submits a prompt or loads model weights.
"""

import json

from animation_studio.providers.image import ImageRequest

MODEL_NAME = 'stabilityai/sdxl-turbo'
MODEL_VERSION = '71153311d3dbb46851df1931d3ca6e939de83304'
MODEL_PATH = 'sdxl-turbo'  # Relative to a future configured ComfyUI diffusers root.


def build_image_workflow(request: ImageRequest) -> dict[str, dict]:
    """Return a fresh API-format graph; model registration is a later preflight."""
    request = ImageRequest.model_validate(request)
    if (request.model_name, request.model_version) != (MODEL_NAME, MODEL_VERSION):
        raise ValueError('This workflow supports only the inventoried SDXL-Turbo revision')
    return {
        '1': {'class_type': 'DiffusersLoader', 'inputs': {'model_path': MODEL_PATH}},
        '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': request.prompt, 'clip': ['1', 1]}},
        '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': '', 'clip': ['1', 1]}},
        '4': {
            'class_type': 'EmptyLatentImage',
            'inputs': {'width': 512, 'height': 512, 'batch_size': 1},
        },
        '5': {
            'class_type': 'KSampler',
            'inputs': {
                'model': ['1', 0],
                'positive': ['2', 0],
                'negative': ['3', 0],
                'latent_image': ['4', 0],
                'seed': request.seed,
                'steps': 1,
                'cfg': 1.0,
                'sampler_name': 'euler',
                'scheduler': 'normal',
                'denoise': 1.0,
            },
        },
        '6': {'class_type': 'VAEDecode', 'inputs': {'samples': ['5', 0], 'vae': ['1', 2]}},
        '7': {
            'class_type': 'SaveImage',
            'inputs': {
                'images': ['6', 0],
                'filename_prefix': 'animation_sdxl_turbo',
            },
        },
    }


def validate_image_workflow(graph: object) -> ImageRequest:
    """Validate exact topology/ports/settings and recover its request metadata.

    Extra nodes/inputs, dangling links, cycles and changed scalar types fail
    closed. Model identity is this profile's declared mapping, not proof of the
    actual files a future ComfyUI server registers under model_path.
    """
    try:
        if not isinstance(graph, dict) or any(type(key) is not str for key in graph):
            raise ValueError('Expected an API node mapping')
        prompt = graph['2']['inputs']['text']
        seed = graph['5']['inputs']['seed']
        request = ImageRequest(
            prompt=prompt,
            seed=seed,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
        )
        expected = build_image_workflow(request)
        # JSON serialization compares both structure and JSON scalar types.
        if json.dumps(graph, sort_keys=True, allow_nan=False) != json.dumps(
            expected, sort_keys=True, allow_nan=False
        ):
            raise ValueError('Graph differs from the supported image workflow profile')
        return request
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Invalid SDXL-Turbo API workflow') from error


def load_image_workflow(raw: str) -> dict[str, dict]:
    """Parse JSON without silently accepting duplicate keys or non-finite values."""

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate workflow key')
            result[key] = value
        return result

    graph = json.loads(raw, object_pairs_hook=unique)
    validate_image_workflow(graph)
    return graph
