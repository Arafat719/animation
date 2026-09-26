"""Create an allowlisted reproducible build context. Never builds/pulls/pushes."""

import argparse
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    'Dockerfile': 'deploy/gpu-health/Dockerfile',
    'requirements.txt': 'deploy/gpu-health/requirements.txt',
    **{
        name: name
        for name in (
            'animation_studio/__init__.py',
            'animation_studio/providers/__init__.py',
            'animation_studio/providers/gpu.py',
            'animation_studio/providers/gpu_secrets.py',
            'animation_studio/workers/__init__.py',
            'animation_studio/workers/gpu_health.py',
        )
    },
}


def package(output: Path, base_image: str) -> str:
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9./:_-]*@sha256:[a-f0-9]{64}', base_image):
        raise ValueError('A digest-pinned base image reference is required')
    entries = {name: (ROOT / source).read_bytes() for name, source in FILES.items()}
    # Bake the validated pin in, so the archive builds without an unpinned override.
    entries['Dockerfile'] = entries['Dockerfile'].replace(
        b'ARG WORKER_BASE_IMAGE\nFROM ${WORKER_BASE_IMAGE}', f'FROM {base_image}'.encode()
    )
    entries['manifest.json'] = (
        json.dumps(
            {
                'base_image': base_image,
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in entries.items()},
            },
            sort_keys=True,
            indent=2,
        )
        + '\n'
    ).encode()
    with output.open('xb') as target, tarfile.open(fileobj=target, mode='w') as archive:
        for name, data in sorted(entries.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    return hashlib.sha256(output.read_bytes()).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(package(args.output, args.base_image))
