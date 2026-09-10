import errno
import json
import os
import shutil
import sqlite3
import stat
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from animation_studio.media import artifacts
from animation_studio.persistence.job_results import JobResultRepository
from animation_studio.providers.fake import FakeConfig, FakeProvider, FakeRequest


MEDIA = (
    ('image', 'sample_image.png', 'image/png', 'png'),
    ('audio', 'silent_audio.wav', 'audio/wav', 'wav'),
    ('video', 'sample_video.mp4', 'video/mp4', 'mp4'),
)


@pytest.fixture(scope='module')
def generated_result(tmp_path_factory):
    root = tmp_path_factory.mktemp('artifact-provider')
    source = FakeConfig().fixture_dir
    original = {name: (source / name).read_bytes() for _, name, _, _ in MEDIA}
    for name, content in original.items():
        (root / name).write_bytes(content)
    result = FakeProvider(FakeConfig(fixture_dir=root, delay_seconds=0)).generate(
        FakeRequest(prompt='রাতের শহর', seed=42),
    )
    yield result
    assert {name: (source / name).read_bytes() for name in original} == original


@pytest.fixture
def setup(tmp_path, monkeypatch, generated_result):
    root = tmp_path / 'fixtures'
    root.mkdir()
    payload = generated_result.model_dump(mode='json')
    for kind, name, _, _ in MEDIA:
        shutil.copy2(getattr(generated_result, kind).path, root / name)
        payload[kind]['path'] = str(root / name)
    database = str(tmp_path / 'artifacts.db')
    store = JobResultRepository(database)
    monkeypatch.setenv('ANIMATION_DB_PATH', database)
    monkeypatch.setattr(artifacts, 'FIXTURE_ROOT', root)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("INSERT INTO projects (id, title) VALUES (1, 'Scene')")
        connection.executemany(
            'INSERT INTO render_jobs (id, project_id, state, progress) VALUES (?, 1, ?, ?)',
            [(1, 'completed', 100), (2, 'queued', 0), (3, 'failed', 30)],
        )
        connection.commit()
    store.save_success(1, payload)
    store.save_error(3, {'code': 'timeout', 'message': f'Private provider error: {root}'})

    def forbidden_generation(*args, **kwargs):
        pytest.fail('Reading an artifact must not execute the provider')

    monkeypatch.setattr(FakeProvider, 'generate', forbidden_generation)
    return database, root


def snapshot(setup):
    database, root = setup
    with closing(sqlite3.connect(database)) as connection:
        rows = tuple(connection.iterdump())
    files = {}
    for path in root.rglob('*'):
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            content = path.read_bytes()
        elif stat.S_ISLNK(mode):
            content = str(path.readlink())
        else:
            content = None
        files[str(path.relative_to(root))] = (mode, content)
    return rows, files


def get_unchanged(setup, url):
    before = snapshot(setup)
    with TestClient(app) as client:
        response = client.get(url)
    assert snapshot(setup) == before
    return response


def assert_private_error(response, setup, status):
    assert response.status_code == status, response.text
    assert response.headers['cache-control'] == 'private, no-store'
    assert isinstance(response.json()['detail'], str)
    assert str(Path(setup[0]).parent) not in response.text
    assert 'sample_image.png' not in response.text


def change_saved_image_path(setup, path):
    with closing(sqlite3.connect(setup[0])) as connection:
        payload = json.loads(connection.execute(
            'SELECT result_json FROM job_results WHERE job_id = 1',
        ).fetchone()[0])
        payload['image']['path'] = str(path)
        connection.execute('UPDATE job_results SET result_json = ? WHERE job_id = 1',
                           (json.dumps(payload),))
        connection.commit()


def test_saved_bytes_headers_and_download_survive_client_reopen(setup):
    before = snapshot(setup)
    for _ in range(2):
        with TestClient(app) as client:
            for kind, name, mime, extension in MEDIA:
                for query, disposition in (('', 'inline'), ('?download=false', 'inline'),
                                           ('?download=true', 'attachment')):
                    response = client.get(f'/jobs/1/artifacts/{kind}{query}')
                    assert response.status_code == 200
                    assert response.content == (setup[1] / name).read_bytes()
                    assert response.headers['content-type'] == mime
                    assert response.headers['content-disposition'] == (
                        f'{disposition}; filename="job-1-{kind}.{extension}"'
                    )
                    assert response.headers['x-content-type-options'] == 'nosniff'
                    assert response.headers['cache-control'] == 'private, no-store'
    assert snapshot(setup) == before


@pytest.mark.parametrize(('url', 'status'), [
    ('/jobs/999/artifacts/image', 404),
    ('/jobs/0/artifacts/image', 422),
    ('/jobs/-1/artifacts/image', 422),
    ('/jobs/abc/artifacts/image', 422),
    ('/jobs/1.5/artifacts/image', 422),
    ('/jobs/9223372036854775808/artifacts/image', 422),
    ('/jobs/1/artifacts/thumbnail', 422),
    ('/jobs/1/artifacts/IMAGE', 422),
    ('/jobs/1/artifacts/image?download=invalid', 422),
    ('/jobs/1/artifacts/image?path=/etc/passwd', 422),
    ('/jobs/1/artifacts/image?download=true&extra=1', 422),
])
def test_unknown_job_and_invalid_request_do_not_change_saved_data(setup, url, status):
    assert get_unchanged(setup, url).status_code == status


@pytest.mark.parametrize('job_id', [2, 3])
def test_missing_or_failed_outcome_has_no_artifact(setup, job_id):
    response = get_unchanged(setup, f'/jobs/{job_id}/artifacts/image')
    assert_private_error(response, setup, 404)
    assert 'Private provider error' not in response.text


@pytest.mark.parametrize('corruption', ['broken json', '{}', 'wrong-kind', 'unknown-schema'])
def test_corrupt_saved_outcome_returns_result_error_without_overwriting(setup, corruption):
    with closing(sqlite3.connect(setup[0])) as connection:
        if corruption == 'unknown-schema':
            connection.execute('PRAGMA ignore_check_constraints = ON')
            connection.execute('UPDATE job_results SET schema_version = 2 WHERE job_id = 1')
        else:
            if corruption == 'wrong-kind':
                payload = json.loads(connection.execute(
                    'SELECT result_json FROM job_results WHERE job_id = 1',
                ).fetchone()[0])
                payload['image']['kind'] = 'audio'
                corruption = json.dumps(payload)
            connection.execute('UPDATE job_results SET result_json = ? WHERE job_id = 1',
                               (corruption,))
        connection.commit()
    response = get_unchanged(setup, '/jobs/1/artifacts/image')
    assert response.status_code == 500
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.json() == {'detail': 'সংরক্ষিত job result পড়া যাচ্ছে না।'}


@pytest.mark.parametrize(('kind', 'name', 'mime', 'extension'), MEDIA)
def test_missing_fixture_is_gone_without_recreating_it(setup, kind, name, mime, extension):
    (setup[1] / name).unlink()
    response = get_unchanged(setup, f'/jobs/1/artifacts/{kind}')
    assert_private_error(response, setup, 410)


@pytest.mark.parametrize('change', ['hash-mismatch', 'empty', 'oversized', 'directory', 'fifo'])
def test_invalid_fixture_is_rejected_without_modification(setup, change):
    path = setup[1] / 'sample_image.png'
    if change in ('directory', 'fifo'):
        path.unlink()
        if change == 'directory':
            path.mkdir()
        else:
            os.mkfifo(path)
    elif change == 'oversized':
        with path.open('wb') as fixture:
            fixture.truncate(16 * 1024 * 1024 + 1)
    else:
        path.write_bytes(b'changed fixture bytes' if change == 'hash-mismatch' else b'')
    response = get_unchanged(setup, '/jobs/1/artifacts/image')
    assert_private_error(response, setup, 409)
    assert b'changed fixture bytes' not in response.content


@pytest.mark.parametrize('location', ['outside', 'traversal', 'wrong-filename', 'nul'])
def test_persisted_path_cannot_select_another_file(setup, location):
    root = setup[1]
    if location == 'outside':
        path = root.parent / 'sample_image.png'
        shutil.copy2(root / 'sample_image.png', path)
    elif location == 'traversal':
        path = root / '..' / root.name / 'sample_image.png'
    elif location == 'wrong-filename':
        path = root / 'private-image.png'
        shutil.copy2(root / 'sample_image.png', path)
    else:
        path = str(root / 'sample_image.png') + '\0'
    change_saved_image_path(setup, path)
    response = get_unchanged(setup, '/jobs/1/artifacts/image')
    assert_private_error(response, setup, 409)


@pytest.mark.parametrize('outside', [False, True])
def test_symlink_cannot_serve_its_target_even_with_matching_hash(setup, outside):
    root = setup[1]
    path = root / 'sample_image.png'
    target = (root.parent if outside else root) / 'private-image.png'
    original = path.read_bytes()
    target.write_bytes(original)
    path.unlink()
    path.symlink_to(target)
    response = get_unchanged(setup, '/jobs/1/artifacts/image')
    assert_private_error(response, setup, 409)
    assert target.read_bytes() == original


@pytest.mark.parametrize('error_number', [errno.EACCES, errno.EIO])
def test_fixture_permission_and_io_errors_are_private_and_retryable(setup, monkeypatch, error_number):
    original_open = artifacts.os.open

    def unavailable(path, *args, **kwargs):
        if path == 'sample_image.png':
            raise OSError(error_number, f'Private operating system detail: {setup[1]}', str(path))
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(artifacts.os, 'open', unavailable)
    response = get_unchanged(setup, '/jobs/1/artifacts/image')
    assert_private_error(response, setup, 503)
    assert 'Private operating system detail' not in response.text
