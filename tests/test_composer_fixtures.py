"""Real decoding and source reproduction for synthetic composer fixtures."""

import hashlib
import json
import subprocess
import wave
from pathlib import Path

import pytest
from PIL import Image

from scripts.generate_composer_fixtures import generate

FIXTURES = Path(__file__).parent / 'fixtures/composer'


def check_media(directory):
    with Image.open(directory / 'shapes.png') as picture:
        picture.load()
        assert picture.size == (96, 64)
        assert picture.getpixel((10, 10)) == (238, 181, 68)
    with wave.open(str(directory / 'tone.wav')) as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, 24000)
        assert audio.getnframes() == 24000
        assert any(audio.readframes(24000))
    info = json.loads(
        subprocess.check_output(
            [
                'ffprobe',
                '-v',
                'error',
                '-show_streams',
                '-show_format',
                '-of',
                'json',
                str(directory / 'shapes.mp4'),
            ]
        )
    )
    (stream,) = info['streams']
    assert (stream['codec_name'], stream['pix_fmt']) == ('h264', 'yuv420p')
    assert (stream['width'], stream['height'], stream['r_frame_rate']) == (96, 64, '12/1')
    assert abs(float(info['format']['duration']) - 1) < 0.1
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(directory / 'shapes.mp4'), '-f', 'null', '-'],
        check=True,
        capture_output=True,
    )
    manifest = json.loads((directory / 'provenance.json').read_text())
    assert set(manifest['files']) == {'shapes.png', 'tone.wav', 'shapes.mp4'}
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest


def test_committed_composer_fixtures_decode_and_match_provenance():
    check_media(FIXTURES)


def test_generator_reproduces_content_without_overwriting(tmp_path):
    destination = tmp_path / 'fresh'
    generate(destination)
    check_media(destination)
    for name in ('shapes.png', 'tone.wav'):
        assert (destination / name).read_bytes() == (FIXTURES / name).read_bytes()
    before = (destination / 'provenance.json').read_bytes()
    with pytest.raises(FileExistsError):
        generate(destination)
    assert (destination / 'provenance.json').read_bytes() == before
