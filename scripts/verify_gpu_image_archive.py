"""Verify a single-image OCI archive without extracting it or contacting a registry."""

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path


def verify(path: Path, expected_image_id: str) -> dict:
    if not re.fullmatch(r'[a-f0-9]{64}', expected_image_id):
        raise ValueError('Expected a full image config SHA256')
    with tarfile.open(path, 'r:') as archive:
        members = archive.getmembers()
        if len({m.name for m in members}) != len(members):
            raise ValueError('Duplicate archive entries')

        def read_json(name):
            member = archive.getmember(name)
            if not member.isfile() or member.size > 4 * 1024 * 1024:
                raise ValueError('Invalid metadata entry')
            return json.load(archive.extractfile(member))

        def check_blob(descriptor):
            digest = descriptor['digest']
            if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
                raise ValueError('Unsupported digest')
            member = archive.getmember('blobs/sha256/' + digest[7:])
            if not member.isfile() or member.size != descriptor['size']:
                raise ValueError('Blob size mismatch')
            checksum = hashlib.sha256()
            with archive.extractfile(member) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    checksum.update(chunk)
            if checksum.hexdigest() != digest[7:]:
                raise ValueError('Blob checksum mismatch')
            return member.name

        if read_json('oci-layout') != {'imageLayoutVersion': '1.0.0'}:
            raise ValueError('Unsupported OCI layout')
        index = read_json('index.json')
        if index.get('schemaVersion') != 2 or len(index.get('manifests', [])) != 1:
            raise ValueError('Expected a single image')
        manifest_ref = index['manifests'][0]
        manifest = read_json(check_blob(manifest_ref))
        if manifest.get('schemaVersion') != 2:
            raise ValueError('Unsupported manifest')
        config = read_json(check_blob(manifest['config']))
        if manifest['config']['digest'] != 'sha256:' + expected_image_id:
            raise ValueError('Archive does not match tested image ID')
        for layer in manifest['layers']:
            check_blob(layer)
        if config.get('os') != 'linux' or config.get('architecture') != 'amd64':
            raise ValueError('Expected linux/amd64 image')
        if config.get('config', {}).get('User') != '65532:65532':
            raise ValueError('Unexpected image user')
    with path.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {
        'archive_sha256': checksum,
        'archive_bytes': path.stat().st_size,
        'manifest_digest': manifest_ref['digest'],
        'image_id': expected_image_id,
        'layer_count': len(manifest['layers']),
        'platform': 'linux/amd64',
        'verified': 'manifest/config/all layer descriptor sizes and SHA256',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--image-id', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.image_id), indent=2))
