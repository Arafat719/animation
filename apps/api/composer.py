"""Bounded fixed-sample composer download; no caller-supplied filesystem paths."""

import io
import tempfile
import threading
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

from animation_studio.media.errors import ComposerError, checked_export, storage_error
from animation_studio.media.subtitles import SubtitleCue

router = APIRouter()
FIXTURES = Path(__file__).resolve().parents[2] / 'tests/fixtures/composer'
LOCK = threading.Lock()


@router.post('/composer/sample-export')
def sample_export():
    if not LOCK.acquire(blocking=False):
        raise HTTPException(
            409,
            detail={'code': 'busy', 'message': 'একটি sample export চলছে। একটু পরে আবার চেষ্টা করুন।'},
        )
    try:
        with tempfile.TemporaryDirectory(prefix='composer-download-') as directory:
            bundle = Path(directory) / 'bundle'
            checked_export(
                [FIXTURES / 'shapes.mp4'] * 2,
                bundle,
                dialogue=FIXTURES / 'tone.wav',
                cues=[SubtitleCue(0, 1, 'Sample')],
            )
            # Local bundle records absolute source paths; omit them from downloads.
            import json

            manifest_path = bundle / 'render_manifest.json'
            manifest = json.loads(manifest_path.read_text())
            for record in manifest['inputs']:
                record['path'] = Path(record['path']).name
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
            content = io.BytesIO()
            with zipfile.ZipFile(content, 'w', zipfile.ZIP_DEFLATED) as archive:
                for path in bundle.iterdir():
                    archive.write(path, path.name)
            return Response(
                content.getvalue(),
                media_type='application/zip',
                headers={
                    'Content-Disposition': 'attachment; filename="composer-sample.zip"',
                    'Cache-Control': 'no-store',
                    'X-Content-Type-Options': 'nosniff',
                },
            )
    except ComposerError as error:
        raise HTTPException(
            error.status, detail={'code': error.code, 'message': error.message}
        ) from error
    except OSError as error:
        failure = storage_error(error)
        raise HTTPException(
            failure.status, detail={'code': failure.code, 'message': failure.message}
        ) from error
    finally:
        LOCK.release()
