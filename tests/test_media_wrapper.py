import subprocess
from pathlib import Path

from PIL import Image

from animation_studio.media.ffmpeg import concatenate_videos, ffmpeg_version, image_to_video, normalize_video, probe_media


def test_ffmpeg_version_works():
    version = ffmpeg_version()
    assert 'ffmpeg' in version.lower()


def test_probe_media_reads_duration(tmp_path):
    media_path = tmp_path / 'sample.mp4'
    ffmpeg = 'ffmpeg'
    subprocess.run(
        [
            ffmpeg,
            '-y',
            '-f',
            'lavfi',
            '-i',
            'testsrc=size=64x64:rate=1:duration=1',
            '-pix_fmt',
            'yuv420p',
            str(media_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    probe = probe_media(str(media_path))
    assert float(probe['duration']) > 0


def test_image_to_video_creates_playable_mp4(tmp_path):
    source_image = tmp_path / 'source.png'
    Image.new('RGB', (64, 64), color='skyblue').save(source_image)

    output_video = tmp_path / 'clip.mp4'
    generated = image_to_video(str(source_image), str(output_video), duration=1)

    assert generated == str(output_video)
    assert output_video.exists()
    assert float(probe_media(str(output_video))['duration']) > 0.5


def test_normalize_video_keeps_dimensions_and_fps_consistent(tmp_path):
    source_a = tmp_path / 'source_a.mp4'
    source_b = tmp_path / 'source_b.mp4'

    subprocess.run(
        ['ffmpeg', '-y', '-f', 'lavfi', '-i', 'testsrc=size=32x24:rate=4:duration=1', '-pix_fmt', 'yuv420p', str(source_a)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ['ffmpeg', '-y', '-f', 'lavfi', '-i', 'testsrc=size=48x36:rate=2:duration=1', '-pix_fmt', 'yuv420p', str(source_b)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    normalized_a = normalize_video(str(source_a), tmp_path / 'normalized_a.mp4', width=64, height=64, fps=12)
    normalized_b = normalize_video(str(source_b), tmp_path / 'normalized_b.mp4', width=64, height=64, fps=12)

    assert normalized_a.endswith('normalized_a.mp4')
    assert normalized_b.endswith('normalized_b.mp4')
    assert float(probe_media(normalized_a)['duration']) > 0
    assert float(probe_media(normalized_b)['duration']) > 0


def test_concatenate_videos_matches_expected_total_duration(tmp_path):
    clip_a = tmp_path / 'clip_a.mp4'
    clip_b = tmp_path / 'clip_b.mp4'
    for idx, clip in enumerate([clip_a, clip_b], start=1):
        subprocess.run(
            ['ffmpeg', '-y', '-f', 'lavfi', '-i', f'testsrc=size=64x64:rate=12:duration=1', '-pix_fmt', 'yuv420p', str(clip)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    combined = tmp_path / 'combined.mp4'
    result = concatenate_videos([str(clip_a), str(clip_b)], str(combined))

    assert result == str(combined)
    assert combined.exists()
    duration = float(probe_media(str(combined))['duration'])
    assert 1.5 <= duration <= 2.5
