"""Phase 2 acceptance: replay from manifest and visible/audible timeline cue."""

import array
import json
import math
import subprocess
from pathlib import Path

import pytest

from animation_studio.media.export import export_bundle
from animation_studio.media.subtitles import SubtitleCue
from scripts.replay_render import replay


def ffmpeg(*args):
    return subprocess.check_output(['ffmpeg', '-v', 'error', '-y', *map(str, args)])


def test_manifest_replay_and_audio_video_synchronization(tmp_path):
    clips = []
    for color in ('red', 'blue'):
        clip = tmp_path / f'{color}.mp4'
        ffmpeg(
            '-f',
            'lavfi',
            '-i',
            f'color={color}:size=64x64:rate=12:duration=1',
            '-c:v',
            'libx264',
            clip,
        )
        clips.append(clip)
    dialogue = tmp_path / 'pulse.wav'
    ffmpeg(
        '-f',
        'lavfi',
        '-i',
        'sine=frequency=440:sample_rate=48000:duration=0.5',
        '-af',
        'adelay=1000',
        dialogue,
    )
    original, repeated = tmp_path / 'original', tmp_path / 'replayed'
    export_bundle(clips, original, dialogue=dialogue, cues=[SubtitleCue(1, 1.5, 'Cue')])
    replay(original / 'render_manifest.json', repeated)
    for name in ('video.mp4', 'thumbnail.png', 'subtitles.srt', 'render_manifest.json'):
        assert (original / name).read_bytes() == (repeated / name).read_bytes()
    output = original / 'video.mp4'
    manifest = json.loads((original / 'render_manifest.json').read_text())
    assert abs(float(manifest['media']['format']['duration']) - 2) <= 0.5
    for instant, channel in ((0.8, 0), (1.2, 2)):
        frame = ffmpeg(
            '-ss',
            instant,
            '-i',
            output,
            '-frames:v',
            '1',
            '-f',
            'rawvideo',
            '-pix_fmt',
            'rgb24',
            '-',
        )
        assert frame[(32 * 64 + 32) * 3 + channel] > 200
    pcm = array.array('h', ffmpeg('-i', output, '-ac', '1', '-f', 's16le', '-'))

    def rms(start, end):
        values = pcm[int(start * 48000) : int(end * 48000)]
        return math.sqrt(sum(v * v for v in values) / len(values))

    assert rms(0.2, 0.8) < 2
    assert rms(1.1, 1.4) > 1500
    assert rms(1.7, 1.9) < 2
    active = [i for i in range(0, len(pcm) - 480, 480) if rms(i / 48000, (i + 480) / 48000) > 500]
    assert abs(active[0] / 48000 - 1) < 0.05
    dialogue.write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash mismatch'):
        replay(original / 'render_manifest.json', tmp_path / 'refused')
    assert not (tmp_path / 'refused').exists()
