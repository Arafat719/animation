"""Temporary, inference-only CPU Conv2d computation in F32 with FP16 storage."""

from contextlib import contextmanager
from types import MethodType


def mixed_forward(module, input):
    import torch
    from torch.nn import functional as F

    if torch.is_grad_enabled() or module.training:
        raise ValueError('Mixed convolution requires eval and disabled gradients')
    tensors = [input, module.weight] + ([] if module.bias is None else [module.bias])
    if any(t.device.type != 'cpu' or t.dtype != torch.float16 for t in tensors):
        raise ValueError('Mixed convolution requires CPU FP16 tensors')
    if torch.is_autocast_enabled('cpu'):
        raise ValueError('Mixed convolution does not support autocast')
    x = input.float()
    padding = module.padding
    if module.padding_mode != 'zeros':
        x = F.pad(x, module._reversed_padding_repeated_twice, mode=module.padding_mode)
        padding = (0, 0)
    return F.conv2d(
        x,
        module.weight.float(),
        None if module.bias is None else module.bias.float(),
        module.stride,
        padding,
        module.dilation,
        module.groups,
    ).to(input.dtype)


@contextmanager
def mixed_convolutions(model):
    import torch

    modules = [m for m in model.modules() if isinstance(m, torch.nn.Conv2d)]
    if not modules:
        raise ValueError('No Conv2d modules found')
    for module in modules:
        if type(module) is not torch.nn.Conv2d or 'forward' in module.__dict__:
            raise ValueError('Unsupported customized Conv2d')
        if module.training or any(
            p.device.type != 'cpu' or p.dtype != torch.float16 for p in module.parameters()
        ):
            raise ValueError('Expected eval CPU FP16 Conv2d')
    changed = []
    try:
        for module in modules:
            module.forward = MethodType(mixed_forward, module)
            changed.append(module)
        yield len(modules)
    finally:
        for module in changed:
            del module.forward
