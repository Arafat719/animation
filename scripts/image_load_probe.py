"""Linux-only offline SDXL probe; explicit inference opt-in, never retries."""

import argparse
import json
import math
import os
import resource
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

SNAPSHOT = Path(
    os.environ.get(
        'SDXL_TURBO_SNAPSHOT',
        '/home/arafat/.cache/huggingface/hub/models--stabilityai--sdxl-turbo/snapshots/71153311d3dbb46851df1931d3ca6e939de83304',
    )
)
GIB = 1024**3


def error_details(error):
    """Bound persisted diagnostics; never capture frame locals or source lines."""
    frames = []
    current = error.__traceback__
    while current is not None:
        code = current.tb_frame.f_code
        frames.append(
            {
                'file': code.co_filename[-256:],
                'function': code.co_name[:256],
                'line': current.tb_lineno,
            }
        )
        frames = frames[-12:]
        current = current.tb_next
    return {
        'error_type': type(error).__name__[:128],
        'error_message': str(error)[:2048],
        'traceback_frames': frames,
    }


@dataclass(frozen=True)
class Limits:
    seconds: float = 300
    rss_bytes: int = 8 * GIB
    reserve_bytes: int = 2 * GIB
    address_bytes: int = 24 * GIB

    def __post_init__(self):
        if (
            type(self.seconds) not in (int, float)
            or not math.isfinite(self.seconds)
            or self.seconds <= 0
        ):
            raise ValueError('Invalid time limit')
        for value in (self.rss_bytes, self.reserve_bytes, self.address_bytes):
            if type(value) is not int or value <= 0:
                raise ValueError('Invalid memory limit')


def available_memory():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1]) * 1024
    raise ValueError('MemAvailable unavailable')


def resident_memory(pid):
    try:
        lines = Path(f'/proc/{pid}/status').read_text().splitlines()
    except FileNotFoundError:
        return 0
    for line in lines:
        if line.startswith('VmRSS:'):
            return int(line.split()[1]) * 1024
    # A zombie has no RSS and will be reaped by the supervisor.
    if any(line.startswith('State:') and 'Z' in line for line in lines):
        return 0
    # During exit, mm teardown can precede the visible zombie state.
    # Caller must confirm exit; absence of VmRSS is not a zero-RSS sample.
    return None


def run_probe(output: Path, *, mode: str, limits: Limits | None = None, address_policy='cpu'):
    """Create a new evidence directory; all abnormal exits are failures.

    RSS/host reserve are sampled every 50 ms, not hard allocation ceilings.
    CPU RLIMIT_AS and ITIMER_REAL apply independently of parent monitoring.
    Explicit CUDA policy omits only the application AS cap, never host RSS guards.
    Scope is one trusted child without worker subprocesses; no process-tree claim.
    """
    limits = limits or Limits()
    validate_address_policy(mode, address_policy)
    operator_modes = {
        f'operator:{op}:{dtype}'
        for op in ('conv', 'linear')
        for dtype in ('float32', 'float16', 'bfloat16')
    }
    operator_modes.add('operator:conv_mixed:float16')
    if mode not in operator_modes and mode not in (
        'load',
        'infer',
        'infer-mixed',
        'decode-only',
        'latent-only',
        'decode-real',
        'synthetic-ok',
        'synthetic-hang',
        'synthetic-rss',
        'synthetic-as',
        'synthetic-error',
    ):
        raise ValueError('Unknown probe mode')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    stage_path = output / 'stage.json'
    result = {
        'mode': mode,
        'address_policy': address_policy,
        'outcome': 'failed',
        'reason': None,
        'pid': None,
        'returncode': None,
        'peak_sampled_rss_bytes': 0,
        'stage': 'not_started',
    }
    from scripts.image_memory import memory_sample

    result['parent_peak_sampled_rss_bytes'] = 0
    result['combined_peak_sampled_rss_bytes'] = 0
    started = time.monotonic()
    child = None
    try:
        if available_memory() < limits.reserve_bytes:
            result['reason'] = 'host_memory'
        else:
            env = {
                **os.environ,
                'HF_HUB_OFFLINE': '1',
                'TRANSFORMERS_OFFLINE': '1',
                'HF_HUB_DISABLE_TELEMETRY': '1',
                'OMP_NUM_THREADS': '2',
                'MKL_NUM_THREADS': '2',
                'TOKENIZERS_PARALLELISM': 'false',
            }
            child = subprocess.Popen(
                [
                    sys.executable,
                    '-m',
                    'scripts.image_load_probe',
                    '--child',
                    mode,
                    '--stage',
                    str(stage_path),
                    '--seconds',
                    str(limits.seconds),
                    '--address-bytes',
                    str(limits.address_bytes),
                    '--address-policy',
                    address_policy,
                ],
                cwd=Path(__file__).resolve().parents[1],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            result['pid'] = child.pid
            while True:
                if time.monotonic() - started >= limits.seconds:
                    result['reason'] = 'timeout'
                    break
                rss = resident_memory(child.pid)
                if rss is None:
                    remaining = max(0, limits.seconds - (time.monotonic() - started))
                    try:
                        child.wait(timeout=min(0.05, remaining))
                    except subprocess.TimeoutExpired as error:
                        raise ValueError('Child RSS unavailable while still alive') from error
                    break
                result['peak_sampled_rss_bytes'] = max(result['peak_sampled_rss_bytes'], rss)
                parent_rss = memory_sample()['rss_bytes']
                if parent_rss is None:
                    raise ValueError('Parent RSS unavailable')
                result['parent_peak_sampled_rss_bytes'] = max(
                    result['parent_peak_sampled_rss_bytes'], parent_rss
                )
                result['combined_peak_sampled_rss_bytes'] = max(
                    result['combined_peak_sampled_rss_bytes'], rss + parent_rss
                )
                if rss > limits.rss_bytes:
                    result['reason'] = 'rss_limit'
                    break
                if available_memory() < limits.reserve_bytes:
                    result['reason'] = 'host_memory'
                    break
                if child.poll() is not None:
                    break
                time.sleep(0.05)
    except (OSError, ValueError) as error:
        result['reason'] = f'monitor_error:{type(error).__name__}'
    finally:
        if child is not None:
            if child.poll() is None:
                child.kill()
            child.wait()
            result['returncode'] = child.returncode
        result['elapsed_seconds'] = time.monotonic() - started
    if stage_path.exists():
        try:
            result['child_evidence'] = json.loads(stage_path.read_text())
            result['stage'] = result['child_evidence']['stage']
        except (OSError, ValueError, KeyError, TypeError):
            result['reason'] = result['reason'] or 'invalid_evidence'
    expected = {
        'load': 'loaded',
        'infer': 'image_saved',
        'infer-mixed': 'image_saved',
        'latent-only': 'latents_saved',
        'decode-real': 'image_saved',
    }.get(mode, 'synthetic_complete')
    if result['reason'] is None:
        if result['returncode'] == 0 and result['stage'] == expected:
            result['outcome'] = {
                'latent-only': 'latents_saved',
                'decode-real': 'image_saved',
                'load': 'loaded',
                'infer': 'image_saved',
                'infer-mixed': 'image_saved',
            }.get(mode, 'synthetic_pass')
        else:
            result['reason'] = 'child_failed'
    if result['outcome'] == 'image_saved':
        from scripts.image_inference import verify_artifact

        try:
            verify_artifact(output)
        except (OSError, ValueError, KeyError, TypeError):
            result['outcome'] = 'failed'
            result['reason'] = 'invalid_image_artifact'
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


class StageRecorder:
    """Bounded timing/memory history with explicitly allowed diagnostic scalars."""

    MAX_EVENTS = 512

    def __init__(self, stage_path):
        self.stage_path = stage_path
        self.events_path = stage_path.with_name('events.jsonl')
        self.events_path.open('x').close()
        self.started = time.monotonic()
        self.cpu_started = time.process_time()
        self.count = 0
        self.last_stage = 'not_started'

    def __call__(self, stage, **values):
        if not isinstance(stage, str) or not stage or len(stage) > 64:
            raise ValueError('Invalid diagnostic stage')
        if self.count >= self.MAX_EVENTS:
            raise ValueError('Diagnostic event limit exceeded')
        from scripts.image_memory import memory_sample

        allowed = {
            'address_policy': str,
            'device': str,
            'module_name': str,
            'root_alive': bool,
            'live_tensor_count': int,
            'live_tensor_bytes': int,
            'latent_bytes': int,
        }
        diagnostics = {}
        for key, kind in allowed.items():
            if key in values:
                if type(values[key]) is not kind or (kind is str and len(values[key]) > 160):
                    raise ValueError('Invalid diagnostic scalar')
                diagnostics[key] = values[key]
        event = {
            **memory_sample(),
            **diagnostics,
            'stage': stage,
            'elapsed_seconds': time.monotonic() - self.started,
            'cpu_seconds': time.process_time() - self.cpu_started,
        }
        with self.events_path.open('a') as stream:
            stream.write(json.dumps(event) + '\n')
        self.count += 1
        temp = self.stage_path.with_suffix('.tmp')
        temp.write_text(json.dumps({**values, **event}))
        temp.replace(self.stage_path)
        self.last_stage = stage


def validate_address_policy(mode, policy):
    if policy not in ('cpu', 'cuda'):
        raise ValueError('Unknown address policy')
    if policy == 'cuda' and mode not in ('infer', 'infer-mixed', 'latent-only', 'decode-real'):
        raise ValueError('CUDA address policy is only for CUDA inference modes')


def apply_address_policy(policy, address_bytes):
    if policy == 'cpu':
        resource.setrlimit(resource.RLIMIT_AS, (address_bytes, address_bytes))
    elif policy == 'cuda':
        if resource.getrlimit(resource.RLIMIT_AS) != (
            resource.RLIM_INFINITY,
            resource.RLIM_INFINITY,
        ):
            raise RuntimeError('CUDA address policy requires unlimited inherited RLIMIT_AS')
        # Do not set/raise host-imposed limits or impose an arbitrary CUDA VA ceiling.
    else:
        raise ValueError('Unknown address policy')


def child_probe(mode, stage_path, seconds, address_bytes, address_policy='cpu'):
    validate_address_policy(mode, address_policy)
    # CPU cap still precedes all imports/allocations; CUDA uses the supervised RSS guard.
    if address_policy == 'cpu':
        apply_address_policy(address_policy, address_bytes)
    resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(seconds), math.ceil(seconds) + 1))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    signal.setitimer(signal.ITIMER_REAL, seconds)

    record = StageRecorder(stage_path)

    def deny_network(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto'):
            raise RuntimeError('Network is disabled for the load probe')

    sys.addaudithook(deny_network)
    record('guarded')
    try:
        if address_policy == 'cuda':
            apply_address_policy(address_policy, address_bytes)
            record('cuda_address_policy', address_policy=address_policy)
            from scripts.image_device import require_cuda

            require_cuda()
        if mode.startswith('operator:'):
            from scripts.image_operator_probe import measure

            _, operator, dtype = mode.split(':')
            measure(operator, dtype, record)
        elif mode == 'synthetic-hang':
            time.sleep(seconds * 4)
        elif mode == 'synthetic-rss':
            allocation = bytearray(64 * 1024**2)
            record('allocated', size=len(allocation))
            time.sleep(seconds * 4)
        elif mode == 'synthetic-as':
            allocation = bytearray(address_bytes * 2)
            record('unexpected_allocation', size=len(allocation))
        elif mode == 'synthetic-error':
            raise RuntimeError('Injected child failure')
        elif mode == 'synthetic-ok':
            try:
                socket.create_connection(('127.0.0.1', 9))
            except RuntimeError:
                record(
                    'synthetic_complete',
                    network_blocked=True,
                    address_limit=resource.getrlimit(resource.RLIMIT_AS)[0],
                )
        elif mode == 'decode-real':
            from scripts.image_split_probe import decode_real

            decode_real(SNAPSHOT, stage_path.parent, record)
        elif mode == 'decode-only':
            from scripts.image_memory import probe_decode_only

            probe_decode_only(SNAPSHOT, record)
        elif mode in ('load', 'infer', 'infer-mixed', 'latent-only'):
            record('checking_snapshot')
            if not (SNAPSHOT / 'model_index.json').is_file():
                raise FileNotFoundError('Existing snapshot unavailable')
            record('importing')
            import torch
            from diffusers import StableDiffusionXLPipeline

            from scripts.image_stream_load import load_sdxl_components

            record('configuring_runtime')
            torch.set_num_threads(2)
            torch.set_num_interop_threads(1)
            components = load_sdxl_components(SNAPSHOT, record)
            record('loading_pipeline')
            pipe = StableDiffusionXLPipeline.from_pretrained(
                str(SNAPSHOT),
                **components,
                torch_dtype=torch.float16,
                local_files_only=True,
                use_safetensors=True,
                low_cpu_mem_usage=True,
                add_watermarker=False,
            )
            record('validating_pipeline')
            modules = {
                name: getattr(pipe, name)
                for name in ('unet', 'text_encoder', 'text_encoder_2', 'vae')
            }
            for name, module in modules.items():
                expected = torch.float32 if name == 'vae' else torch.float16
                if module.dtype != expected or module.device.type != 'cpu':
                    raise ValueError('Unexpected model dtype/device')
            record(
                'loaded',
                snapshot=str(SNAPSHOT),
                dtypes={k: str(v.dtype) for k, v in modules.items()},
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            )
            # Pipeline owns components; drop loader/validation aliases before inference.
            del components, modules, module
            if mode in ('infer', 'infer-mixed', 'latent-only'):
                from scripts.image_inference import generate_image

                if mode == 'latent-only':
                    generate_image(
                        pipe, stage_path.parent, SNAPSHOT, record, mixed_conv=True, latent_only=True
                    )
                elif mode == 'infer-mixed':
                    generate_image(
                        pipe,
                        stage_path.parent,
                        SNAPSHOT,
                        record,
                        mixed_conv=True,
                        diagnose_memory=True,
                    )
                else:
                    generate_image(pipe, stage_path.parent, SNAPSHOT, record)
        else:
            raise ValueError('Unknown child mode')
    except (MemoryError, OSError, RuntimeError, ValueError, ImportError, TypeError) as error:
        record('error', failed_stage=record.last_stage, **error_details(error))
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        '--load', action='store_true', help='Explicitly load local weights, no inference'
    )
    action.add_argument('--infer', action='store_true', help='One bounded offline image')
    action.add_argument('--infer-mixed', action='store_true', help='Opt-in F32 UNet Conv2d compute')
    parser.add_argument('--output', type=Path)
    parser.add_argument(
        '--address-policy',
        choices=('cpu', 'cuda'),
        default='cpu',
        help='CPU: existing AS cap; CUDA: no AS cap, requires CUDA, keeps RSS guard',
    )
    parser.add_argument('--child', help=argparse.SUPPRESS)
    parser.add_argument('--stage', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--seconds', type=float, default=300, help=argparse.SUPPRESS)
    parser.add_argument('--address-bytes', type=int, default=24 * GIB, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child_probe(
            args.child, args.stage, args.seconds, args.address_bytes, args.address_policy
        )
    if args.output is None:
        parser.error('--output must name a new evidence directory')
    mode = 'infer' if args.infer else ('load' if args.load else 'synthetic-ok')
    if args.infer_mixed:
        mode = 'infer-mixed'
    result = run_probe(args.output, mode=mode, address_policy=args.address_policy)
    print(json.dumps(result))
    return 0 if result['outcome'] in ('loaded', 'image_saved', 'synthetic_pass') else 1


if __name__ == '__main__':
    raise SystemExit(main())
