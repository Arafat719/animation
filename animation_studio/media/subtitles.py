"""Timed plain-text SRT export and optional subtitle burn-in."""

import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SubtitleCue:
    start: float
    end: float
    text: str


def render_srt(cues: list[SubtitleCue]) -> str:
    """Produce ordered, non-overlapping millisecond cues with literal text."""
    blocks = []
    previous_end = 0
    for index, cue in enumerate(cues, 1):
        for value in (cue.start, cue.end):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
                or value >= 360000
            ):
                raise ValueError('Cue times must be finite seconds between 0 and 360000')
        start, end = round(cue.start * 1000), round(cue.end * 1000)
        if end <= start or start < previous_end:
            raise ValueError(
                'Cues must be ordered, non-overlapping and at least one millisecond long'
            )
        if not isinstance(cue.text, str):
            raise ValueError('Subtitle text must be a string')
        text = cue.text.replace('\r\n', '\n').replace('\r', '\n').strip()
        if (
            not text
            or any(not line.strip() for line in text.split('\n'))
            or any(ord(c) < 32 and c != '\n' for c in text)
        ):
            raise ValueError(
                'Subtitle text cannot be blank or contain empty lines/control characters'
            )
        # libass/Subtitle decoders interpret markup and ASS overrides. Restrict
        # this plain-text contract instead of permitting styling instructions.
        if any(c in text for c in '<>{}\\'):
            raise ValueError('Subtitle markup and escape sequences are unsupported')

        def stamp(ms):
            seconds, millis = divmod(ms, 1000)
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'

        blocks.append(f'{index}\n{stamp(start)} --> {stamp(end)}\n{text}\n')
        previous_end = end
    return '\n'.join(blocks) + ('\n' if blocks else '')


def write_srt(cues: list[SubtitleCue], output_path: str | Path) -> str:
    content = render_srt(cues)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.subtitle-', dir=target.parent) as directory:
        temporary = Path(directory) / 'captions.srt'
        temporary.write_text(content, encoding='utf-8')
        temporary.replace(target)
    return str(target)


def burn_subtitles(video_path: str | Path, cues: list[SubtitleCue], output_path: str | Path) -> str:
    """Burn validated cues using libass; preserve existing audio by stream copy.

    Font coverage depends on installed system fonts. Exporting SRT alone never
    invokes FFmpeg or changes the source video.
    """
    content = render_srt(cues)
    if not content:
        raise ValueError('At least one cue is required for burn-in')
    source = Path(video_path).resolve()
    target = Path(output_path).absolute()
    if not source.is_file():
        raise FileNotFoundError(f'Video input not found: {source}')
    if source == target.resolve() or (target.exists() and source.samefile(target)):
        raise ValueError('Input and output must differ')
    if target.suffix.lower() != '.mp4':
        raise ValueError('Output must be MP4')
    binary = shutil.which('ffmpeg')
    if not binary:
        raise FileNotFoundError('ffmpeg is required')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.subtitle-', dir=target.parent) as directory:
        workspace = Path(directory)
        (workspace / 'captions.srt').write_text(content, encoding='utf-8')
        temporary = workspace / 'output.mp4'
        # Fixed relative filter filename avoids FFmpeg filter-expression escaping
        # of caller-provided paths. Source/destination are separate arguments.
        subprocess.run(
            [
                binary,
                '-nostdin',
                '-v',
                'error',
                '-y',
                '-i',
                str(source),
                '-vf',
                'subtitles=filename=captions.srt',
                '-map',
                '0:v:0',
                '-map',
                '0:a:0?',
                '-c:v',
                'libx264',
                '-pix_fmt',
                'yuv420p',
                '-c:a',
                'copy',
                '-movflags',
                '+faststart',
                str(temporary),
            ],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
        temporary.replace(target)
    return str(output_path)
