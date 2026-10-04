"""Six bounded synthetic CPU cases; no model files or inference."""

import argparse
import json
import resource
import time
from pathlib import Path

from scripts.image_load_probe import GIB, Limits, run_probe

CASES = [('conv', d) for d in ('float32', 'float16', 'bfloat16')] + [
    ('linear', d) for d in ('float16', 'bfloat16', 'float32')
]


def mixed_conv(x, weight):
    """Synthetic CPU conv only; retain FP16 storage, return FP16 activations."""
    import torch
    from torch.nn import functional

    if x.dtype != torch.float16 or weight.dtype != torch.float16:
        raise ValueError('Mixed convolution requires FP16 tensors')
    return functional.conv2d(x.float(), weight.float(), padding=1).to(x.dtype)


def measure(operator, dtype_name, record, *, small=False):
    import torch
    from torch.nn import functional

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    mixed = operator == 'conv_mixed'
    convolution = operator in ('conv', 'conv_mixed')
    dtype = getattr(torch, dtype_name)
    generator = torch.Generator().manual_seed(42)
    channels = 8 if small else (320 if convolution else 1280)
    spatial = 4 if small else 64
    shape = (1, channels, spatial, spatial) if convolution else (1, 256, channels)
    weights = (channels, channels, 3, 3) if convolution else (channels, channels)
    source = torch.randn(shape, generator=generator)
    weight = torch.randn(weights, generator=generator) * 0.02
    x, w = source.to(dtype), weight.to(dtype)

    def apply(a, b):
        return functional.conv2d(a, b, padding=1) if convolution else functional.linear(a, b)

    samples = []
    with torch.inference_mode():
        for index in range(3):
            record(
                'operator_call', operator=operator, dtype=dtype_name, call=index, samples=samples
            )
            wall, cpu = time.monotonic(), time.process_time()
            before_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
            result = mixed_conv(x, w) if mixed else apply(x, w)
            sample = {
                'wall_seconds': time.monotonic() - wall,
                'cpu_seconds': time.process_time() - cpu,
                'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                'peak_rss_growth_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
                - before_peak,
            }
            if not torch.isfinite(result).all():
                raise ValueError('Nonfinite operator output')
            samples.append(sample)
            record('operator_return', operator=operator, dtype=dtype_name, samples=samples)
        record('reference', operator=operator, dtype=dtype_name, samples=samples)
        reference = apply(source, weight)
        if not torch.isfinite(reference).all():
            raise ValueError('Nonfinite reference output')
        difference = result.float() - reference
        metrics = {
            'max_abs_error': difference.abs().max().item(),
            'relative_l2_error': (difference.norm() / reference.norm().clamp_min(1e-12)).item(),
        }
    record(
        'synthetic_complete',
        operator=operator,
        dtype=dtype_name,
        shape=list(shape),
        seed=42,
        storage_bytes=(x.numel() * x.element_size() + w.numel() * w.element_size()),
        explicit_f32_conversion_bytes=(x.numel() + w.numel()) * 4 if mixed else 0,
        samples=samples,
        **metrics,
    )


def run_suite(output, *, mixed=False):
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    results = []
    cases = [('conv', 'float32'), ('conv_mixed', 'float16')] if mixed else CASES
    budget = 20 * len(cases)
    for operator, dtype in cases:
        remaining = budget - (time.monotonic() - started)
        if remaining <= 0:
            break
        result = run_probe(
            output / f'{operator}-{dtype}',
            mode=f'operator:{operator}:{dtype}',
            limits=Limits(
                seconds=min(20, remaining),
                rss_bytes=2 * GIB,
                reserve_bytes=2 * GIB,
                address_bytes=8 * GIB,
            ),
        )
        results.append(result)
        if result['outcome'] != 'synthetic_pass':
            break
    summary = {
        'outcome': 'passed'
        if len(results) == len(cases) and all(r['outcome'] == 'synthetic_pass' for r in results)
        else 'failed',
        'elapsed_seconds': time.monotonic() - started,
        'results': results,
    }
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mixed', action='store_true')
    args = parser.parse_args()
    result = run_suite(args.output, mixed=args.mixed)
    print(json.dumps(result))
    return 0 if result['outcome'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
