import json
import shutil
import subprocess
from pathlib import Path


def ffmpeg_version() -> str:
    ffmpeg_path = shutil.which('ffmpeg')
    if not ffmpeg_path:
        raise FileNotFoundError('ffmpeg is not installed or not on PATH')

    completed = subprocess.run(
        [ffmpeg_path, '-version'],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.splitlines()[0].strip()


def ffprobe_path() -> str:
    probe_path = shutil.which('ffprobe')
    if not probe_path:
        raise FileNotFoundError('ffprobe is not installed or not on PATH')
    return probe_path


def probe_media(path: str | Path) -> dict:
    media_path = str(path)
    probe = subprocess.run(
        [ffprobe_path(), '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', media_path],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(probe.stdout)
    return {'duration': data.get('format', {}).get('duration', '0')}


def image_to_video(image_path: str | Path, output_path: str | Path, duration: float = 1.0) -> str:
    source_image = Path(image_path)
    target_video = Path(output_path)

    if not source_image.exists():
        raise FileNotFoundError(f'Image input not found: {source_image}')

    if duration <= 0:
        raise ValueError('duration must be greater than zero')

    target_video.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_binary = shutil.which('ffmpeg')
    if not ffmpeg_binary:
        raise FileNotFoundError('ffmpeg is not installed or not on PATH')

    subprocess.run(
        [
            ffmpeg_binary,
            '-y',
            '-loop',
            '1',
            '-i',
            str(source_image),
            '-t',
            str(duration),
            '-pix_fmt',
            'yuv420p',
            '-vf',
            'scale=64:64:force_original_aspect_ratio=decrease,pad=64:64:(ow-iw)/2:(oh-ih)/2',
            '-r',
            '12',
            '-an',
            str(target_video),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return str(target_video)


def normalize_video(input_path: str | Path, output_path: str | Path, width: int = 64, height: int = 64, fps: int = 12) -> str:
    source = Path(input_path)
    target = Path(output_path)

    if not source.exists():
        raise FileNotFoundError(f'Video input not found: {source}')
    if width <= 0 or height <= 0:
        raise ValueError('width and height must be positive')
    if fps <= 0:
        raise ValueError('fps must be positive')

    ffmpeg_binary = shutil.which('ffmpeg')
    if not ffmpeg_binary:
        raise FileNotFoundError('ffmpeg is not installed or not on PATH')

    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg_binary,
            '-y',
            '-i',
            str(source),
            '-vf',
            f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps}',
            '-pix_fmt',
            'yuv420p',
            '-c:v',
            'libx264',
            '-preset',
            'ultrafast',
            '-an',
            str(target),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return str(target)


def concatenate_videos(input_paths: list[str | Path], output_path: str | Path) -> str:
    if not input_paths:
        raise ValueError('At least one video path is required')

    resolved_inputs = [str(Path(p)) for p in input_paths]
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_binary = shutil.which('ffmpeg')
    if not ffmpeg_binary:
        raise FileNotFoundError('ffmpeg is not installed or not on PATH')

    file_list = target.parent / 'concat_input.txt'
    with open(file_list, 'w', encoding='utf-8') as handle:
        for item in resolved_inputs:
            handle.write(f"file '{item}'\n")

    subprocess.run(
        [
            ffmpeg_binary,
            '-y',
            '-f',
            'concat',
            '-safe',
            '0',
            '-i',
            str(file_list),
            '-c',
            'copy',
            str(target),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return str(target)
