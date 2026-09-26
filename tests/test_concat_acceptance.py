"""Real concat path, concurrency, timing and failure preservation checks."""

import hashlib
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from animation_studio.media.ffmpeg import concatenate_videos, normalize_video

FIXTURE = Path(__file__).parent / 'fixtures/composer/shapes.mp4'


def inspect(path):
    info = json.loads(
        subprocess.check_output(
            ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]
        )
    )
    assert abs(float(info['format']['duration']) - 2) <= 0.5
    assert [stream['codec_name'] for stream in info['streams']] == ['h264', 'aac']
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-'],
        check=True,
        capture_output=True,
    )


def test_relative_special_paths_parallel_calls_and_cleanup(tmp_path, monkeypatch):
    first = tmp_path / "a ' quote বাংলা.mp4"
    second = tmp_path / 'b \\ space.mp4'
    normalize_video(FIXTURE, first)
    shutil.copyfile(first, second)
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (first, second)]
    sentinel = tmp_path / 'concat_input.txt'
    sentinel.write_text('unrelated file')
    monkeypatch.chdir(tmp_path)
    outputs = [Path('outputs') / f'joined {i}.mp4' for i in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda output: concatenate_videos([first.name, second.name], output), outputs)
        )
    assert results == list(map(str, outputs))
    for output in outputs:
        inspect(output)
    assert sorted(p.name for p in (tmp_path / 'outputs').iterdir()) == [
        'joined 0.mp4',
        'joined 1.mp4',
    ]
    assert sentinel.read_text() == 'unrelated file'
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in (first, second)] == before


def test_failure_preserves_destination_and_cleans_temporary_files(tmp_path):
    bad = tmp_path / 'bad.mp4'
    bad.write_bytes(b'not media')
    output = tmp_path / 'existing.mp4'
    output.write_bytes(b'keep output')
    with pytest.raises(subprocess.CalledProcessError):
        concatenate_videos([bad], output)
    assert output.read_bytes() == b'keep output'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['bad.mp4', 'existing.mp4']


def test_invalid_paths_and_aliases_do_not_modify_inputs(tmp_path):
    source = tmp_path / 'source.mp4'
    shutil.copyfile(FIXTURE, source)
    alias = tmp_path / 'alias.mp4'
    alias.hardlink_to(source)
    before = source.read_bytes()
    with pytest.raises(ValueError):
        concatenate_videos([source], alias)
    with pytest.raises(ValueError):
        concatenate_videos([], tmp_path / 'out.mp4')
    with pytest.raises(FileNotFoundError):
        concatenate_videos([tmp_path / 'missing.mp4'], tmp_path / 'out.mp4')
    newline = tmp_path / 'line\nbreak.mp4'
    shutil.copyfile(source, newline)
    with pytest.raises(ValueError):
        concatenate_videos([newline], tmp_path / 'out.mp4')
    assert source.read_bytes() == before
    assert not (tmp_path / 'out.mp4').exists()


def test_concat_preserves_clip_order(tmp_path):
    clips = []
    for color in ('red', 'blue'):
        clip = tmp_path / f'{color}.mp4'
        subprocess.run(
            [
                'ffmpeg',
                '-v',
                'error',
                '-f',
                'lavfi',
                '-i',
                f'color={color}:size=64x64:rate=12:duration=1',
                '-c:v',
                'libx264',
                '-pix_fmt',
                'yuv420p',
                str(clip),
            ],
            check=True,
            capture_output=True,
        )
        clips.append(clip)
    output = tmp_path / 'ordered.mp4'
    concatenate_videos(clips, output)
    for instant, channel in (('0.5', 0), ('1.5', 2)):
        frame = subprocess.check_output(
            [
                'ffmpeg',
                '-v',
                'error',
                '-ss',
                instant,
                '-i',
                str(output),
                '-frames:v',
                '1',
                '-f',
                'rawvideo',
                '-pix_fmt',
                'rgb24',
                '-',
            ]
        )
        assert len(frame) == 64 * 64 * 3
        pixel = frame[(32 * 64 + 32) * 3 : (32 * 64 + 32) * 3 + 3]
        assert pixel[channel] > 220
        assert sum(pixel) - pixel[channel] < 30
