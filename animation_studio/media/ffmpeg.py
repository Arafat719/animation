import json
import shutil
import subprocess
import tempfile
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
        [
            ffprobe_path(),
            '-v',
            'error',
            '-show_entries',
            'format=duration',
            '-of',
            'json',
            media_path,
        ],
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


def normalize_video(
    input_path: str | Path,
    output_path: str | Path,
    width: int = 64,
    height: int = 64,
    fps: int = 12,
) -> str:
    """Normalize the first video/audio streams to H.264/AAC MP4.

    Audio is stereo 48 kHz; missing/short audio is padded with silence to the
    video end. Existing audio is preserved, not mixed. Output replaces its
    destination only after successful encoding; input and output must differ.
    """
    source = Path(input_path).resolve()
    target = Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(f'Video input not found: {source}')
    if source == target.resolve() or (target.exists() and source.samefile(target)):
        raise ValueError('Input and output must be different files')
    if any(type(value) is not int or value <= 0 for value in (width, height, fps)):
        raise ValueError('width, height and fps must be positive integers')
    if width % 2 or height % 2:
        raise ValueError('width and height must be even for yuv420p')
    if target.suffix.lower() != '.mp4':
        raise ValueError('Normalized output must be an .mp4 file')
    ffmpeg_binary = shutil.which('ffmpeg')
    if not ffmpeg_binary:
        raise FileNotFoundError('ffmpeg is not installed or not on PATH')
    info = json.loads(
        subprocess.check_output(
            [
                ffprobe_path(),
                '-v',
                'error',
                '-show_streams',
                '-of',
                'json',
                str(source),
            ]
        )
    )
    if not any(stream['codec_type'] == 'video' for stream in info['streams']):
        raise ValueError('Input must contain a video stream')
    has_audio = any(stream['codec_type'] == 'audio' for stream in info['streams'])
    inputs = ['-i', str(source)]
    if not has_audio:
        inputs += ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000']
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.mp4', delete=False) as file:
        temporary = Path(file.name)
    try:
        subprocess.run(
            [
                ffmpeg_binary,
                '-nostdin',
                '-v',
                'error',
                '-y',
                *inputs,
                '-map',
                '0:v:0',
                '-map',
                '0:a:0' if has_audio else '1:a:0',
                '-vf',
                f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}',
                '-pix_fmt',
                'yuv420p',
                '-c:v',
                'libx264',
                '-preset',
                'ultrafast',
                '-af',
                'aresample=48000,apad',
                '-c:a',
                'aac',
                '-ar',
                '48000',
                '-ac',
                '2',
                '-b:a',
                '128k',
                '-shortest',
                '-movflags',
                '+faststart',
                str(temporary),
            ],
            check=True,
            capture_output=True,
        )
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return str(target)


def concatenate_videos(input_paths: list[str | Path], output_path: str | Path) -> str:
    """Stream-copy compatible clips in order; normalize differing inputs first."""
    if not input_paths:
        raise ValueError('At least one video path is required')
    sources = [Path(path).resolve() for path in input_paths]
    target = Path(output_path)
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(f'Video input not found: {source}')
        if any(character in str(source) for character in ('\n', '\r', '\0')):
            raise ValueError('Input paths cannot contain line breaks or NUL')
        if source == target.resolve() or (target.exists() and source.samefile(target)):
            raise ValueError('Input and output must be different files')
    if not target.suffix:
        raise ValueError('Output must have a media file extension')
    ffmpeg_binary = shutil.which('ffmpeg')
    if not ffmpeg_binary:
        raise FileNotFoundError('ffmpeg is not installed or not on PATH')
    target.parent.mkdir(parents=True, exist_ok=True)
    # Each call owns its list and partial output. Keep the output on the same
    # filesystem as the destination so successful replacement is atomic.
    with tempfile.TemporaryDirectory(prefix='.concat-', dir=target.parent) as directory:
        workspace = Path(directory)
        file_list = workspace / 'inputs.ffconcat'
        lines = []
        for source in sources:
            # ffconcat uses its own quoting, not shell quoting. End the quoted
            # token, escape the apostrophe, then resume the quoted token.
            escaped = str(source).replace("'", "'\\''")
            lines.append("file '" + escaped + "'\n")
        file_list.write_text('ffconcat version 1.0\n' + ''.join(lines), encoding='utf-8')
        temporary = workspace / ('output' + target.suffix)
        subprocess.run(
            [
                ffmpeg_binary,
                '-nostdin',
                '-v',
                'error',
                '-y',
                '-f',
                'concat',
                '-safe',
                '0',
                '-i',
                str(file_list),
                '-c',
                'copy',
                str(temporary),
            ],
            check=True,
            capture_output=True,
        )
        temporary.replace(target)
    return str(target)
