"""Actual repeatable bundle export, content hashes and failure cleanup."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from animation_studio.media.export import export_bundle
from animation_studio.media.subtitles import SubtitleCue

FIXTURES = Path(__file__).parent / 'fixtures/composer'


@pytest.mark.parametrize('burn_in', [False, True])
def test_repeatable_bundle_and_manifest(tmp_path, burn_in):
    options = dict(
        dialogue=FIXTURES / 'tone.wav',
        background=FIXTURES / 'tone.wav',
        cues=[SubtitleCue(0, 1, 'Hello')],
        burn_in=burn_in,
        width=160,
        height=96,
    )
    first, second = tmp_path / 'first', tmp_path / 'second'
    export_bundle([FIXTURES / 'shapes.mp4'] * 2, first, **options)
    export_bundle([FIXTURES / 'shapes.mp4'] * 2, second, **options)
    assert sorted(p.name for p in first.iterdir()) == [
        'render_manifest.json',
        'subtitles.srt',
        'thumbnail.png',
        'video.mp4',
    ]
    for file in first.iterdir():
        assert file.read_bytes() == (second / file.name).read_bytes()
    manifest = json.loads((first / 'render_manifest.json').read_text())
    assert manifest['schema_version'] == 1
    assert manifest['settings']['burn_in'] == burn_in
    assert [item['role'] for item in manifest['inputs']] == [
        'clip',
        'clip',
        'dialogue',
        'background',
    ]
    for record in manifest['inputs']:
        assert record['sha256'] == hashlib.sha256(Path(record['path']).read_bytes()).hexdigest()
    for name, record in manifest['outputs'].items():
        content = (first / name).read_bytes()
        assert record == {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}
    assert abs(float(manifest['media']['format']['duration']) - 2) <= 0.5
    with Image.open(first / 'thumbnail.png') as image:
        image.load()
        assert image.size == (160, 96)
    frame = subprocess.check_output(
        [
            'ffmpeg',
            '-v',
            'error',
            '-i',
            str(first / 'video.mp4'),
            '-frames:v',
            '1',
            '-f',
            'rawvideo',
            '-pix_fmt',
            'rgb24',
            '-',
        ]
    )
    with Image.open(first / 'thumbnail.png') as image:
        assert image.convert('RGB').tobytes() == frame
    assert not list(tmp_path.glob('.export-*'))


def test_existing_destination_and_failed_export_are_preserved(tmp_path):
    target = tmp_path / 'saved'
    target.mkdir()
    (target / 'keep').write_text('original')
    with pytest.raises(FileExistsError):
        export_bundle([FIXTURES / 'shapes.mp4'], target)
    assert (target / 'keep').read_text() == 'original'
    bad = tmp_path / 'bad.mp4'
    bad.write_bytes(b'corrupt')
    with pytest.raises(subprocess.CalledProcessError):
        export_bundle([bad], tmp_path / 'failed')
    assert not (tmp_path / 'failed').exists()
    assert not list(tmp_path.glob('.export-*'))


def test_minimal_bundle_and_invalid_combinations(tmp_path):
    output = tmp_path / 'minimal'
    export_bundle([FIXTURES / 'shapes.mp4'], output)
    assert not (output / 'subtitles.srt').exists()
    for options in ({'background': FIXTURES / 'tone.wav'}, {'burn_in': True}):
        with pytest.raises(ValueError):
            export_bundle([FIXTURES / 'shapes.mp4'], tmp_path / 'invalid', **options)
    assert not (tmp_path / 'invalid').exists()
