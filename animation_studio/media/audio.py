"""Local composer dialogue/background mixing; no speech synthesis."""

import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from animation_studio.media.ffmpeg import ffprobe_path


def mix_audio(
    video_path: str | Path,
    dialogue_path: str | Path,
    output_path: str | Path,
    *,
    background_path: str | Path | None = None,
    background_gain: float = 0.2,
    fade_seconds: float = 0.2,
) -> str:
    """Replace video audio with dialogue plus optional background, limited to video duration.

    Short tracks are padded, long tracks trimmed; background is not looped. Fade
    applies to the background only. Gains are linear; final mix is peak-limited.
    """
    video, dialogue = Path(video_path).resolve(), Path(dialogue_path).resolve()
    background = Path(background_path).resolve() if background_path is not None else None
    target = Path(output_path)
    sources = [video, dialogue] + ([background] if background is not None else [])
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(f'Media input not found: {source}')
        if source == target.resolve() or (target.exists() and source.samefile(target)):
            raise ValueError('Input and output must be different files')
    if target.suffix.lower() != '.mp4':
        raise ValueError('Output must be MP4')
    for value, name, maximum in (
        (background_gain, 'background_gain', 1),
        (fade_seconds, 'fade_seconds', 60),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= maximum
        ):
            raise ValueError(f'{name} must be finite and between 0 and {maximum}')
    binary = shutil.which('ffmpeg')
    if not binary:
        raise FileNotFoundError('ffmpeg is required')
    streams = []
    for source in sources:
        info = json.loads(
            subprocess.check_output(
                [ffprobe_path(), '-v', 'error', '-show_streams', '-of', 'json', str(source)]
            )
        )
        streams.append(info['streams'])
    videos = [s for s in streams[0] if s['codec_type'] == 'video']
    if not videos or videos[0]['codec_name'] != 'h264':
        raise ValueError('Normalize video to H.264 before mixing')
    duration = float(videos[0].get('duration', 'nan'))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Video must have a finite positive stream duration')
    if any(not any(s['codec_type'] == 'audio' for s in group) for group in streams[1:]):
        raise ValueError('Dialogue/background inputs must contain audio')
    filters = [
        f'[1:a:0]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={duration},asetpts=PTS-STARTPTS[d]'
    ]
    if background is not None:
        fade = min(fade_seconds, duration / 2)
        effect = f',afade=t=in:d={fade},afade=t=out:st={duration - fade}:d={fade}' if fade else ''
        filters += [
            f'[2:a:0]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={duration},asetpts=PTS-STARTPTS,volume={background_gain}{effect}[b]',
            '[d][b]amix=inputs=2:duration=first:normalize=0[m]',
        ]
        label = 'm'
    else:
        label = 'd'
    filters.append(f'[{label}]alimiter=limit=0.95:level=false:latency=true[out]')
    inputs = [part for source in sources for part in ('-i', str(source))]
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.audio-mix-', dir=target.parent) as temp:
        partial = Path(temp) / 'output.mp4'
        subprocess.run(
            [
                binary,
                '-nostdin',
                '-v',
                'error',
                '-y',
                *inputs,
                '-filter_complex',
                ';'.join(filters),
                '-map',
                '0:v:0',
                '-map',
                '[out]',
                '-c:v',
                'copy',
                '-c:a',
                'aac',
                '-ar',
                '48000',
                '-ac',
                '2',
                '-b:a',
                '128k',
                '-t',
                str(duration),
                '-movflags',
                '+faststart',
                str(partial),
            ],
            check=True,
            capture_output=True,
        )
        partial.replace(target)
    return str(target)
