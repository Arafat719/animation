"""Real frame and stream acceptance for the existing image-to-video helper."""

import json
import subprocess
from pathlib import Path

from animation_studio.media.ffmpeg import image_to_video


def test_composer_image_video_has_expected_frames_and_letterboxing(tmp_path):
    source = Path(__file__).parent / 'fixtures/composer/shapes.png'
    output = tmp_path / 'clip.mp4'
    image_to_video(source, output, duration=2)
    probe = json.loads(
        subprocess.check_output(
            [
                'ffprobe',
                '-v',
                'error',
                '-show_streams',
                '-show_format',
                '-of',
                'json',
                str(output),
            ]
        )
    )
    (stream,) = probe['streams']
    assert (stream['codec_name'], stream['pix_fmt']) == ('h264', 'yuv420p')
    assert (stream['width'], stream['height'], stream['r_frame_rate']) == (64, 64, '12/1')
    assert abs(float(probe['format']['duration']) - 2) <= 1 / 12
    frames = subprocess.check_output(
        [
            'ffmpeg',
            '-v',
            'error',
            '-i',
            str(output),
            '-f',
            'rawvideo',
            '-pix_fmt',
            'rgb24',
            '-',
        ]
    )
    size = 64 * 64 * 3
    assert len(frames) == 24 * size
    for offset in (0, 12 * size, 23 * size):
        frame = frames[offset : offset + size]

        def pixel(x, y):
            start = (y * 64 + x) * 3
            return tuple(frame[start : start + 3])

        assert max(pixel(32, 2)) < 12
        assert max(pixel(32, 61)) < 12
        for actual, expected in ((pixel(12, 28), (238, 181, 68)), (pixel(45, 30), (80, 198, 180))):
            assert max(abs(a - b) for a, b in zip(actual, expected)) < 25
