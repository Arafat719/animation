from pathlib import Path

from animation_studio.media.ffmpeg import probe_media

FIXTURE_DIR = Path(__file__).parent / 'fixtures'


def test_fixture_files_exist_and_are_readable():
    image = FIXTURE_DIR / 'sample_image.png'
    video = FIXTURE_DIR / 'sample_video.mp4'
    audio = FIXTURE_DIR / 'sample_audio.wav'

    assert image.exists()
    assert video.exists()
    assert audio.exists()

    assert image.stat().st_size > 0
    assert video.stat().st_size > 0
    assert audio.stat().st_size > 0

    assert float(probe_media(str(video))['duration']) > 0
    assert float(probe_media(str(audio))['duration']) > 0
