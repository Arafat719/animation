"""Narrow object_info inventory check; no model/GPU/weight attestation."""

from animation_studio.providers.comfy_workflow import validate_image_workflow
from animation_studio.providers.image import ImageProviderError

OUTPUTS = {
    'DiffusersLoader': ['MODEL', 'CLIP', 'VAE'],
    'CLIPTextEncode': ['CONDITIONING'],
    'EmptyLatentImage': ['LATENT'],
    'KSampler': ['LATENT'],
    'VAEDecode': ['IMAGE'],
    'SaveImage': [],
}
COMBOS = {'model_path', 'sampler_name', 'scheduler'}


def validate_node_inventory(graph: dict, inventory: dict) -> None:
    """Check this profile's declared ports, required inputs and selected combos.

    Numeric limits, custom validators, runtime availability and remote content
    identity remain server-validation/runtime gates. Extra unused nodes are allowed.
    """
    validate_image_workflow(graph)
    try:
        for node in graph.values():
            kind = node['class_type']
            info = inventory[kind]
            if info['output'] != OUTPUTS[kind]:
                raise ValueError
            if info['output_node'] is not (kind == 'SaveImage'):
                raise ValueError
            if info['is_input_list'] is not False or info['output_is_list'] != [False] * len(
                OUTPUTS[kind]
            ):
                raise ValueError
            # JSON bools must not silently compare equal to numeric values.
            if any(type(value) is not bool for value in info['output_is_list']):
                raise ValueError
            required = info['input']['required']
            if set(required) != set(node['inputs']):
                raise ValueError
            for name, value in node['inputs'].items():
                declaration = required[name]
                if not isinstance(declaration, list) or not 1 <= len(declaration) <= 2:
                    raise ValueError
                if len(declaration) == 2 and not isinstance(declaration[1], dict):
                    raise ValueError
                declared = declaration[0]
                if name in COMBOS:
                    if not isinstance(declared, list) or not all(type(x) is str for x in declared):
                        raise ValueError
                    if value not in declared:
                        raise ValueError
                else:
                    if isinstance(value, list):
                        source = graph[value[0]]['class_type']
                        expected = OUTPUTS[source][value[1]]
                    else:
                        expected = {str: 'STRING', int: 'INT', float: 'FLOAT'}[type(value)]
                    if declared != expected:
                        raise ValueError
    except (KeyError, IndexError, TypeError, ValueError):
        raise ImageProviderError('unsupported', 'Comfy node/model inventory incompatible') from None
