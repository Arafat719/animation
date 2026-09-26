"""Replay a trusted local render manifest: python -m scripts.replay_render MANIFEST DESTINATION."""

import argparse
import json
from pathlib import Path

from animation_studio.media.export import _digest, export_bundle
from animation_studio.media.subtitles import SubtitleCue


def replay(manifest_path: Path, destination: Path) -> str:
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['schema_version'] != 1 or manifest['pipeline_version'] != 'local-composer-1':
        raise ValueError('Unsupported manifest version')
    sources = {'clip': [], 'dialogue': [], 'background': []}
    for record in manifest['inputs']:
        path = Path(record['path'])
        if not path.is_absolute():
            path = manifest_path.resolve().parent / path
        if _digest(path) != record['sha256']:
            raise ValueError('Source hash mismatch; replay refused')
        sources[record['role']].append(path)
    if len(sources['dialogue']) > 1 or len(sources['background']) > 1:
        raise ValueError('At most one dialogue/background input is supported')
    settings = dict(manifest['settings'])
    if settings['cues'] is not None:
        settings['cues'] = [SubtitleCue(**cue) for cue in settings['cues']]
    result = export_bundle(
        sources['clip'],
        destination,
        dialogue=next(iter(sources['dialogue']), None),
        background=next(iter(sources['background']), None),
        **settings,
    )
    actual = json.loads((Path(result) / 'render_manifest.json').read_text())
    if actual['tools'] != manifest['tools'] or actual['outputs'] != manifest['outputs']:
        raise ValueError(
            'Replay differs from recorded toolchain/output hashes; inspect destination'
        )
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(replay(args.manifest, args.destination))
