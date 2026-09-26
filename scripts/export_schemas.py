"""Publish versioned contracts: python -m scripts.export_schemas [--check]."""

import argparse
import json
from pathlib import Path

from animation_studio.domain.v1.character import Character, CharacterCreate, CharacterRecord
from animation_studio.domain.v1.project import Project, ProjectCreate, ProjectRecord
from animation_studio.domain.v1.render_job import (
    FixtureJobCreate,
    JobCreate,
    RenderJob,
    RenderJobRecord,
)
from animation_studio.domain.v1.shot import ShotRecord
from animation_studio.domain.v1.story_plan import ShotPlan, StoryPlan

from animation_studio.domain.v1.voice import Voice, VoiceCreate, VoiceRecord

from animation_studio.persistence.job_results import SavedOutcome
from animation_studio.providers.fake import FakeRequest, FakeResult

OUTPUT = Path(__file__).resolve().parents[1] / 'apps/web/public/schemas/v1'
CONTRACTS = {
    'story-plan': (StoryPlan, 'validation'),
    'shot-plan': (ShotPlan, 'validation'),
    'render-job.create': (JobCreate, 'validation'),
    'render-job.fixture-create': (FixtureJobCreate, 'validation'),
    'render-job.response': (RenderJob, 'serialization'),
    'render-job.record': (RenderJobRecord, 'validation'),
    'render-job.saved-outcome': (SavedOutcome, 'serialization'),
    'fake-provider.request': (FakeRequest, 'validation'),
    'fake-provider.result': (FakeResult, 'serialization'),
    'shot.record': (ShotRecord, 'validation'),
    'voice.create': (VoiceCreate, 'validation'),
    'voice.response': (Voice, 'serialization'),
    'voice.record': (VoiceRecord, 'validation'),
    'character.create': (CharacterCreate, 'validation'),
    'character.response': (Character, 'serialization'),
    'character.record': (CharacterRecord, 'validation'),
    'project.create': (ProjectCreate, 'validation'),
    'project.response': (Project, 'serialization'),
    'project.record': (ProjectRecord, 'validation'),
}


def documents() -> dict[str, str]:
    result = {}
    for name, (model, mode) in CONTRACTS.items():
        schema = {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': f'urn:animation-studio:contracts:v1:{name}',
            **model.model_json_schema(mode=mode),
        }
        result[f'{name}.schema.json'] = json.dumps(schema, indent=2, ensure_ascii=False) + '\n'
    return result


def export(output: Path, *, check: bool) -> int:
    expected = documents()
    if check:
        stale = [
            name
            for name, content in expected.items()
            if not (output / name).is_file() or (output / name).read_text() != content
        ]
        stale.extend(
            sorted(path.name for path in output.glob('*.schema.json') if path.name not in expected)
        )
        if stale:
            print('Schema files missing, stale or unexpected: ' + ', '.join(stale))
            print('Run: .venv/bin/python -m scripts.export_schemas')
            return 1
        print(f'{len(expected)} published contract schemas match their models.')
        return 0
    output.mkdir(parents=True, exist_ok=True)
    for name, content in expected.items():
        (output / name).write_text(content)
    print(f'Published {len(expected)} contract schemas to {output}.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--check', action='store_true', help='Fail on schema drift; do not write files'
    )
    args = parser.parse_args()
    return export(OUTPUT, check=args.check)


if __name__ == '__main__':
    raise SystemExit(main())
