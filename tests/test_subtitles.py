"""SRT precision and actual FFmpeg subtitle appearance/timing."""

import json
import subprocess
from pathlib import Path

import pytest

from animation_studio.media.subtitles import SubtitleCue, burn_subtitles, render_srt, write_srt


def test_srt_timestamps_unicode_and_atomic_export(tmp_path):
    cues = [SubtitleCue(0.125, 1.5, 'বাংলা\r\nHello'), SubtitleCue(61.002, 62, 'Next')]
    expected = (
        '1\n00:00:00,125 --> 00:00:01,500\nবাংলা\nHello\n\n2\n00:01:01,002 --> 00:01:02,000\nNext\n\n'
    )
    assert render_srt(cues) == expected
    target = tmp_path / 'captions.srt'
    write_srt(cues, target)
    assert target.read_text() == expected
    assert render_srt([]) == ''
    with pytest.raises(ValueError):
        write_srt([SubtitleCue(1, 0, 'bad')], target)
    assert target.read_text() == expected
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize(
    'cues',
    [
        [SubtitleCue(-1, 1, 'A')],
        [SubtitleCue(0, float('inf'), 'A')],
        [SubtitleCue(True, 2, 'A')],
        [SubtitleCue(0, 0.0001, 'A')],
        [SubtitleCue(0, 2, 'A'), SubtitleCue(1, 3, 'B')],
        [SubtitleCue(0, 1, '')],
        [SubtitleCue(0, 1, 'A\n\nB')],
        [SubtitleCue(0, 1, '<b>A</b>')],
        [SubtitleCue(0, 1, '{override}')],
        [SubtitleCue(0, 1, 'A\x00B')],
    ],
)
def test_invalid_cues(cues):
    with pytest.raises(ValueError):
        render_srt(cues)


def test_real_burn_timing_audio_and_quoted_paths(tmp_path):
    folder = tmp_path / "বাংলা ' quoted: folder"
    folder.mkdir()
    source, output = folder / 'source.mp4', folder / 'burned.mp4'
    subprocess.run(
        [
            'ffmpeg',
            '-v',
            'error',
            '-f',
            'lavfi',
            '-i',
            'color=black:size=320x180:rate=12:duration=2',
            '-f',
            'lavfi',
            '-i',
            'sine=duration=2',
            '-c:v',
            'libx264',
            '-c:a',
            'aac',
            '-shortest',
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    before = source.read_bytes()
    burn_subtitles(source, [SubtitleCue(0.5, 1.5, 'Hello world')], output)
    info = json.loads(
        subprocess.check_output(
            ['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(output)]
        )
    )
    video, audio = info['streams']
    assert (video['width'], video['height'], video['r_frame_rate']) == (320, 180, '12/1')
    assert abs(float(video['duration']) - 2) < 0.1
    assert audio['codec_name'] == 'aac'
    for instant, visible in (('0.1', False), ('1', True), ('1.8', False)):
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
                'gray',
                '-',
            ]
        )
        assert len(frame) == 320 * 180
        assert (sum(value > 150 for value in frame) > 10) == visible

    def audio_bytes(path):
        return subprocess.check_output(
            [
                'ffmpeg',
                '-v',
                'error',
                '-i',
                str(path),
                '-map',
                '0:a',
                '-c',
                'copy',
                '-f',
                'adts',
                '-',
            ]
        )

    assert audio_bytes(source) == audio_bytes(output)
    assert source.read_bytes() == before
    assert sorted(p.name for p in folder.iterdir()) == ['burned.mp4', 'source.mp4']


def test_failed_burn_preserves_output(tmp_path, monkeypatch):
    source = Path(__file__).parent / 'fixtures/composer/shapes.mp4'
    output = tmp_path / 'saved.mp4'
    output.write_bytes(b'keep')

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(subprocess, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        burn_subtitles(source, [SubtitleCue(0, 1, 'Hi')], output)
    assert output.read_bytes() == b'keep'
    assert list(tmp_path.iterdir()) == [output]
    with pytest.raises(ValueError):
        burn_subtitles(source, [SubtitleCue(0, 1, 'Hi')], source)
