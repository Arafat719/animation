import copy

import pytest
import torch

from scripts.image_mixed_conv import mixed_convolutions


@pytest.mark.parametrize(
    'kwargs',
    [
        {},
        {'bias': False, 'stride': 2},
        {'groups': 2, 'dilation': 2},
        {'padding_mode': 'reflect'},
        {'padding_mode': 'replicate'},
        {'padding_mode': 'circular'},
        {'padding': 'same'},
    ],
)
def test_equivalence_storage_and_restore(kwargs):
    options = {'padding': 1, **kwargs}
    module = torch.nn.Conv2d(4, 4, 3, **options).half().eval()
    reference = copy.deepcopy(module).float()
    x = torch.randn(1, 4, 8, 8).half()
    state = {k: v.clone() for k, v in module.state_dict().items()}
    pointers = [p.data_ptr() for p in module.parameters()]
    events = []
    hook = module.register_forward_hook(lambda *args: events.append('called'))
    with torch.inference_mode(), mixed_convolutions(module):
        output = module(x)
        assert torch.equal(output, reference(x.float()).half())
    hook.remove()
    assert events == ['called'] and 'forward' not in module.__dict__
    assert pointers == [p.data_ptr() for p in module.parameters()]
    assert all(torch.equal(v, state[k]) for k, v in module.state_dict().items())


def test_cleanup_on_failure_and_rejections():
    module = torch.nn.Conv2d(4, 4, 3).half().eval()
    with pytest.raises(ValueError), mixed_convolutions(module):
        module(torch.randn(1, 4, 8, 8).half())  # gradients enabled
    assert 'forward' not in module.__dict__
    with torch.inference_mode(), pytest.raises(ValueError), mixed_convolutions(module):
        module(torch.randn(1, 4, 8, 8))
    with pytest.raises(ValueError), mixed_convolutions(module.train()):
        pass
    model = torch.nn.Sequential(module.eval(), torch.nn.Conv2d(4, 4, 3).eval())
    with pytest.raises(ValueError), mixed_convolutions(model):
        pass
    assert 'forward' not in module.__dict__
    with pytest.raises(ValueError), mixed_convolutions(torch.nn.Identity()):
        pass
