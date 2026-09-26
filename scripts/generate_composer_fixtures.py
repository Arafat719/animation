"""Generate local synthetic composer fixtures in a new directory."""

import argparse
import hashlib
import json
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw


def generate(destination: Path) -> None:
    binary = shutil.which('ffmpeg')
    if binary is None:
        raise FileNotFoundError('ffmpeg is required')
    destination.mkdir(parents=True, exist_ok=False)
    picture = Image.new('RGB', (96, 64), '#183048')
    draw = ImageDraw.Draw(picture)
    draw.rectangle((8, 8, 39, 55), fill='#eeb544')
    draw.ellipse((48, 12, 87, 51), fill='#50c6b4')
    picture.save(destination / 'shapes.png')
    with wave.open(str(destination / 'tone.wav'), 'wb') as audio:
        audio.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        audio.writeframes(
            b''.join(
                struct.pack('<h', round(4096 * math.sin(2 * math.pi * 440 * i / 24000)))
                for i in range(24000)
            )
        )
    subprocess.run(
        [
            binary,
            '-nostdin',
            '-v',
            'error',
            '-loop',
            '1',
            '-i',
            str(destination / 'shapes.png'),
            '-t',
            '1',
            '-r',
            '12',
            '-c:v',
            'libx264',
            '-pix_fmt',
            'yuv420p',
            '-an',
            '-map_metadata',
            '-1',
            str(destination / 'shapes.mp4'),
        ],
        check=True,
    )
    manifest = {
        'source': 'Locally generated geometric shapes and mathematical sine wave; no external assets, recordings or AI.',
        'generator': 'scripts/generate_composer_fixtures.py',
        'ffmpeg_version': subprocess.check_output([binary, '-version'], text=True).splitlines()[0],
        'files': {
            name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
            for name in ('shapes.png', 'tone.wav', 'shapes.mp4')
        },
    }
    (destination / 'provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='New directory; existing paths are refused')
    generate(parser.parse_args().destination)
