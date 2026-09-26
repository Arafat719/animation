"""Real signal/timing checks for dialogue mixing and background fades."""

import array
import json
import math
import subprocess
from pathlib import Path

import pytest

from animation_studio.media.audio import mix_audio
from animation_studio.media.ffmpeg import image_to_video


def run(*args):
    return subprocess.check_output(['ffmpeg', '-v', 'error', '-y', *map(str, args)])


def rms(samples):
    return math.sqrt(sum(x * x for x in samples) / len(samples))


@pytest.mark.parametrize('background', [False, True])
def test_dialogue_and_background_have_correct_signal_and_duration(tmp_path, background):
    video = tmp_path / 'video.mp4'
    image_to_video(Path(__file__).parent / 'fixtures/composer/shapes.png', video, duration=2)
    dialogue = tmp_path / 'dialogue.wav'
    run('-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=24000:duration=0.5', dialogue)
    music = tmp_path / 'music.wav'
    run('-f', 'lavfi', '-i', 'sine=frequency=880:sample_rate=44100:duration=3', music)
    output = tmp_path / 'mixed.mp4'
    mix_audio(
        video, dialogue, output, background_path=music if background else None, fade_seconds=0.4
    )
    info = json.loads(
        subprocess.check_output(
            ['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(output)]
        )
    )
    v, a = info['streams']
    assert v['codec_name'] == 'h264'
    assert (a['codec_name'], a['sample_rate'], a['channels']) == ('aac', '48000', 2)
    assert abs(float(a['duration']) - 2) < 0.1
    assert run('-i', video, '-map', '0:v', '-f', 'hash', '-') == run(
        '-i', output, '-map', '0:v', '-f', 'hash', '-'
    )
    samples = array.array('h', run('-i', output, '-map', '0:a', '-ac', '1', '-f', 's16le', '-'))

    def section(start, end):
        return samples[int(start * 48000) : int(end * 48000)]

    assert rms(section(0.1, 0.3)) > 1500
    if background:
        assert rms(section(1, 1.2)) > 300
        assert rms(section(1.95, 1.99)) < rms(section(1, 1.2)) * 0.3
    else:
        assert rms(section(1, 1.5)) < 2


def test_silent_dialogue_exposes_background_fade_in_and_long_dialogue_trims(tmp_path):
    video = tmp_path / 'v.mp4'
    image_to_video(Path(__file__).parent / 'fixtures/composer/shapes.png', video, duration=1)
    long = tmp_path / 'long.wav'
    silence = tmp_path / 'silence.wav'
    run('-f', 'lavfi', '-i', 'sine=duration=2', long)
    run('-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono', '-t', '1', silence)
    output = tmp_path / 'mix.mp4'
    mix_audio(video, silence, output, background_path=long, fade_seconds=0.3)
    samples = array.array('h', run('-i', output, '-ac', '1', '-f', 's16le', '-'))
    assert rms(samples[480:1440]) < rms(samples[19200:24000]) * 0.2
    mix_audio(video, long, output)
    samples = array.array('h', run('-i', output, '-ac', '1', '-f', 's16le', '-'))
    assert abs(len(samples) / 48000 - 1) < 0.05
    assert rms(samples[10000:20000]) > 1500


@pytest.mark.parametrize(
    'options',
    [
        {'background_gain': float('nan')},
        {'background_gain': -1},
        {'fade_seconds': True},
        {'fade_seconds': -1},
    ],
)
def test_invalid_options_preserve_destination(tmp_path, options):
    fixture = Path(__file__).parent / 'fixtures/composer'
    output = tmp_path / 'saved.mp4'
    output.write_bytes(b'keep')
    with pytest.raises(ValueError):
        mix_audio(fixture / 'shapes.mp4', fixture / 'tone.wav', output, **options)
    assert output.read_bytes() == b'keep'


def test_encode_failure_cleans_up_and_preserves_output(tmp_path, monkeypatch):
    fixture = Path(__file__).parent / 'fixtures/composer'
    output = tmp_path / 'saved.mp4'
    output.write_bytes(b'keep')
    original = subprocess.run

    def fail(*args, **kwargs):
        if Path(args[0][0]).name == 'ffmpeg':
            raise subprocess.CalledProcessError(1, args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(subprocess, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        mix_audio(fixture / 'shapes.mp4', fixture / 'tone.wav', output)
    assert output.read_bytes() == b'keep'
    assert list(tmp_path.iterdir()) == [output]
