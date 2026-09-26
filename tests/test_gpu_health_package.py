import json
import tarfile

import pytest

from scripts.package_gpu_health import FILES, package

# Deliberately synthetic pin; never a proposed deployable image.
PIN = 'python@sha256:' + 'a' * 64


def test_reproducible_allowlisted_context(tmp_path):
    first, second = tmp_path / 'one.tar', tmp_path / 'two.tar'
    assert package(first, PIN) == package(second, PIN)
    with tarfile.open(first) as archive:
        assert set(archive.getnames()) == set(FILES) | {'manifest.json'}
        dockerfile = archive.extractfile('Dockerfile').read().decode()
        assert f'FROM {PIN}\n' in dockerfile
        assert 'FROM ${' not in dockerfile
        manifest = json.load(archive.extractfile('manifest.json'))
        assert manifest['base_image'] == PIN
    with pytest.raises(FileExistsError):
        package(first, PIN)


@pytest.mark.parametrize('image', ['python:latest', 'python:3.12', 'x@sha256:bad', 'x\nRUN evil'])
def test_unpinned_base_rejected(tmp_path, image):
    with pytest.raises(ValueError):
        package(tmp_path / 'out.tar', image)
    assert not (tmp_path / 'out.tar').exists()
