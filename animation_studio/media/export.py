"""Reproducible local composer export bundle: MP4, thumbnail, SRT and manifest."""

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from animation_studio.media.audio import mix_audio
from animation_studio.media.ffmpeg import (
    concatenate_videos,
    ffmpeg_version,
    ffprobe_path,
    normalize_video,
)
from animation_studio.media.subtitles import SubtitleCue, burn_subtitles, write_srt


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def export_bundle(
    clips: list[str | Path],
    destination: str | Path,
    *,
    dialogue: str | Path | None = None,
    background: str | Path | None = None,
    cues: list[SubtitleCue] | None = None,
    burn_in: bool = False,
    width: int = 64,
    height: int = 64,
    fps: int = 12,
    background_gain: float = 0.2,
    fade_seconds: float = 0.2,
) -> str:
    """Compose into a new directory, publishing only a complete successful bundle.

    Re-run with the recorded inputs/settings; hashes identify changed inputs.
    Bit identity is tested on the same toolchain, not promised across versions.
    """
    target = Path(destination).absolute()
    if target.exists():
        raise FileExistsError(f'Export destination already exists: {target}')
    if not clips:
        raise ValueError('At least one clip is required')
    if background is not None and dialogue is None:
        raise ValueError('Background mixing requires a dialogue track')
    if burn_in and not cues:
        raise ValueError('Burn-in requires subtitle cues')
    inputs = [('clip', Path(p).resolve()) for p in clips]
    if dialogue is not None:
        inputs.append(('dialogue', Path(dialogue).resolve()))
    if background is not None:
        inputs.append(('background', Path(background).resolve()))
    input_records = [
        {'role': role, 'path': str(path), 'sha256': _digest(path)} for role, path in inputs
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.export-', dir=target.parent) as temporary:
        workspace = Path(temporary)
        bundle = workspace / 'bundle'
        bundle.mkdir()
        normalized = []
        for index, clip in enumerate(clips):
            normalized.append(
                normalize_video(clip, workspace / f'clip-{index}.mp4', width, height, fps)
            )
        current = Path(concatenate_videos(normalized, workspace / 'joined.mp4'))
        if dialogue is not None:
            current = Path(
                mix_audio(
                    current,
                    dialogue,
                    workspace / 'mixed.mp4',
                    background_path=background,
                    background_gain=background_gain,
                    fade_seconds=fade_seconds,
                )
            )
        if cues is not None:
            write_srt(cues, bundle / 'subtitles.srt')
        if burn_in:
            current = Path(burn_subtitles(current, cues, workspace / 'burned.mp4'))
        shutil.copyfile(current, bundle / 'video.mp4')
        binary = shutil.which('ffmpeg')
        subprocess.run(
            [
                binary,
                '-nostdin',
                '-v',
                'error',
                '-i',
                str(current),
                '-frames:v',
                '1',
                str(bundle / 'thumbnail.png'),
            ],
            check=True,
            capture_output=True,
        )
        metadata = json.loads(
            subprocess.check_output(
                [
                    ffprobe_path(),
                    '-v',
                    'error',
                    '-show_entries',
                    'format=duration:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels',
                    '-of',
                    'json',
                    str(bundle / 'video.mp4'),
                ]
            )
        )
        # Do not label a render reproducible if a source changed while rendering.
        for record in input_records:
            if _digest(Path(record['path'])) != record['sha256']:
                raise RuntimeError('An input changed during export')
        manifest = {
            'schema_version': 1,
            'pipeline_version': 'local-composer-1',
            'tools': {
                'ffmpeg': ffmpeg_version(),
                'ffprobe': subprocess.check_output(
                    [ffprobe_path(), '-version'], text=True
                ).splitlines()[0],
            },
            'inputs': input_records,
            'settings': {
                'width': width,
                'height': height,
                'fps': fps,
                'burn_in': burn_in,
                'background_gain': background_gain,
                'fade_seconds': fade_seconds,
                'cues': None
                if cues is None
                else [dict(start=c.start, end=c.end, text=c.text) for c in cues],
            },
            'media': metadata,
            'outputs': {
                p.name: {'sha256': _digest(p), 'bytes': p.stat().st_size}
                for p in sorted(bundle.iterdir())
            },
        }
        (bundle / 'render_manifest.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
            encoding='utf-8',
        )
        if target.exists():
            raise FileExistsError(f'Export destination already exists: {target}')
        bundle.rename(target)
    return str(target)
