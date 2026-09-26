import hashlib
import io
import json
import tarfile

import pytest

from scripts.verify_gpu_image_archive import verify


def archive(path, *, corrupt=False, duplicate=False):
    entries = {}

    def blob(data):
        digest = hashlib.sha256(data).hexdigest()
        entries['blobs/sha256/' + digest] = data
        return {'digest': 'sha256:' + digest, 'size': len(data)}

    config = blob(
        json.dumps(
            {'os': 'linux', 'architecture': 'amd64', 'config': {'User': '65532:65532'}}
        ).encode()
    )
    layer = blob(b'layer-fixture')
    manifest = blob(json.dumps({'schemaVersion': 2, 'config': config, 'layers': [layer]}).encode())
    entries['oci-layout'] = b'{"imageLayoutVersion":"1.0.0"}'
    entries['index.json'] = json.dumps({'schemaVersion': 2, 'manifests': [manifest]}).encode()
    if corrupt:
        entries['blobs/sha256/' + layer['digest'][7:]] = b'layer-corrupt'
    with tarfile.open(path, 'w') as tar:
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        if duplicate:
            tar.addfile(info, io.BytesIO(data))
    return config['digest'][7:]


def test_valid_archive(tmp_path):
    path = tmp_path / 'image.tar'
    identity = archive(path)
    result = verify(path, identity)
    assert result['layer_count'] == 1
    assert result['archive_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize('option', ['corrupt', 'duplicate'])
def test_tampering_rejected(tmp_path, option):
    path = tmp_path / 'image.tar'
    identity = archive(path, **{option: True})
    with pytest.raises(ValueError):
        verify(path, identity)


def test_wrong_image_rejected(tmp_path):
    path = tmp_path / 'image.tar'
    archive(path)
    with pytest.raises(ValueError, match='tested image'):
        verify(path, '0' * 64)
