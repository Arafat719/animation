import errno
import io
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from animation_studio.media import errors
from apps.api import composer
from apps.api.main import app

FIXTURE = Path(__file__).parent / 'fixtures/composer/shapes.mp4'


def test_real_missing_and_corrupt_media(tmp_path):
    with pytest.raises(errors.ComposerError) as failure:
        errors.checked_export([tmp_path / 'missing.mp4'], tmp_path / 'out')
    assert failure.value.code == 'media_missing'
    bad = tmp_path / 'bad.mp4'
    bad.write_bytes(b'corrupt')
    with pytest.raises(errors.ComposerError) as failure:
        errors.checked_export([bad], tmp_path / 'out')
    assert failure.value.code == 'media_invalid'
    assert not (tmp_path / 'out').exists()
    assert not list(tmp_path.glob('.export-*'))


def test_disk_preflight_and_midrun_failures(tmp_path, monkeypatch):
    original = shutil.disk_usage
    monkeypatch.setattr(errors.shutil, 'disk_usage', lambda _: original(tmp_path)._replace(free=0))
    with pytest.raises(errors.ComposerError) as failure:
        errors.checked_export([FIXTURE], tmp_path / 'out')
    assert failure.value.status == 507
    monkeypatch.setattr(errors.shutil, 'disk_usage', original)
    for error in (
        OSError(errno.ENOSPC, 'private path'),
        subprocess.CalledProcessError(
            1, ['ffmpeg'], stderr=b'private path: No space left on device'
        ),
    ):

        def fail(*args, **kwargs):
            raise error

        monkeypatch.setattr(errors, 'export_bundle', fail)
        with pytest.raises(errors.ComposerError) as failure:
            errors.checked_export([FIXTURE], tmp_path / 'out')
        assert failure.value.code == 'disk_full'
        assert 'private' not in failure.value.message


@pytest.mark.parametrize(
    'code,status', [('media_missing', 422), ('media_invalid', 422), ('disk_full', 507)]
)
def test_api_errors_safe_and_retryable(tmp_path, monkeypatch, code, status):
    monkeypatch.setenv('ANIMATION_DB_PATH', str(tmp_path / 'unused.db'))
    original = composer.checked_export

    def fail(*args, **kwargs):
        raise errors.ComposerError(code, 'বাংলা error', status)

    monkeypatch.setattr(composer, 'checked_export', fail)
    with TestClient(app) as client:
        response = client.post('/composer/sample-export')
        assert response.status_code == status
        assert response.json() == {'detail': {'code': code, 'message': 'বাংলা error'}}
    assert not composer.LOCK.locked()
    monkeypatch.setattr(composer, 'checked_export', original)
    assert not (tmp_path / 'unused.db').exists()


def test_real_zip_export_and_busy(tmp_path, monkeypatch):
    monkeypatch.setenv('ANIMATION_DB_PATH', str(tmp_path / 'unused.db'))
    with TestClient(app) as client:
        composer.LOCK.acquire()
        try:
            assert client.post('/composer/sample-export').status_code == 409
        finally:
            composer.LOCK.release()
        response = client.post('/composer/sample-export')
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert set(archive.namelist()) == {
                'video.mp4',
                'thumbnail.png',
                'subtitles.srt',
                'render_manifest.json',
            }
            manifest = json.loads(archive.read('render_manifest.json'))
            assert all('/' not in record['path'] for record in manifest['inputs'])
    assert not (tmp_path / 'unused.db').exists()
