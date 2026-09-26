"""Real audio/video normalization and preservation checks."""

import array
import json
import subprocess
from pathlib import Path

import pytest

from animation_studio.media.ffmpeg import normalize_video


def ffmpeg(*args):
    return subprocess.check_output(['ffmpeg', '-v', 'error', '-y', *map(str, args)])


@pytest.mark.parametrize('audio_duration', [None, 0.5, 3])
def test_normalized_streams_keep_video_and_audio(tmp_path, audio_duration):
    source = tmp_path / 'source.mkv'
    args = ['-f', 'lavfi', '-i', 'color=c=red:size=96x48:rate=10:duration=2']
    if audio_duration is not None:
        args += [
            '-f',
            'lavfi',
            '-i',
            f'sine=frequency=440:sample_rate=24000:duration={audio_duration}',
        ]
    ffmpeg(*args, '-c:v', 'ffv1', *(['-c:a', 'pcm_s16le'] if audio_duration else []), source)
    original = source.read_bytes()
    output = tmp_path / 'normalized.mp4'
    normalize_video(source, output, width=80, height=64, fps=12)
    info = json.loads(
        subprocess.check_output(
            ['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(output)]
        )
    )
    video, audio = info['streams']
    assert (
        video['codec_name'],
        video['width'],
        video['height'],
        video['r_frame_rate'],
        video['pix_fmt'],
        video['sample_aspect_ratio'],
    ) == ('h264', 80, 64, '12/1', 'yuv420p', '1:1')
    assert (audio['codec_name'], audio['sample_rate'], audio['channels']) == ('aac', '48000', 2)
    assert abs(float(video['duration']) - 2) < 0.09
    assert abs(float(audio['duration']) - 2) < 0.15
    samples = array.array('h', ffmpeg('-i', output, '-map', '0:a:0', '-f', 's16le', '-'))
    if audio_duration is None:
        assert max(map(abs, samples)) <= 1
    else:
        assert max(map(abs, samples[:24000])) > 500
        if audio_duration == 0.5:
            assert max(map(abs, samples[96000:])) <= 2
    ffmpeg('-i', output, '-f', 'null', '-')
    assert source.read_bytes() == original


@pytest.mark.parametrize('options', [{'width': 63}, {'height': 0}, {'fps': True}, {'fps': 1.5}])
def test_invalid_settings_do_not_touch_output(tmp_path, options):
    source = Path(__file__).parent / 'fixtures/composer/shapes.mp4'
    output = tmp_path / 'saved.mp4'
    output.write_bytes(b'keep')
    with pytest.raises(ValueError):
        normalize_video(source, output, **options)
    assert output.read_bytes() == b'keep'


def test_reject_same_file_and_nonvideo_and_preserve_output_on_encode_failure(tmp_path, monkeypatch):
    source = Path(__file__).parent / 'fixtures/composer/shapes.mp4'
    with pytest.raises(ValueError):
        normalize_video(source, source)
    output = tmp_path / 'saved.mp4'
    output.write_bytes(b'keep')
    with pytest.raises(ValueError):
        normalize_video(source.with_name('tone.wav'), output)

    original_run = subprocess.run

    def fail(*args, **kwargs):
        if Path(args[0][0]).name == 'ffmpeg':
            raise subprocess.CalledProcessError(1, args[0])
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        normalize_video(source, output)
    assert output.read_bytes() == b'keep'
    assert list(tmp_path.iterdir()) == [output]
