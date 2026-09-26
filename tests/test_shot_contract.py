"""Persisted Shot publication and backward reads without planning assumptions."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from pydantic import ValidationError

from animation_studio.domain.v1.shot import ShotRecord
from animation_studio.persistence import db
from scripts import export_schemas


def test_shot_schema_publication_and_drift(tmp_path):
    assert export_schemas.export(export_schemas.OUTPUT, check=True) == 0
    schema = json.loads((export_schemas.OUTPUT / 'shot.record.schema.json').read_text())
    assert schema.pop('$id') == 'urn:animation-studio:contracts:v1:shot.record'
    assert schema.pop('$schema') == 'https://json-schema.org/draft/2020-12/schema'
    assert schema == ShotRecord.model_json_schema(mode='validation')
    assert set(schema['required']) == set(ShotRecord.model_fields)
    assert schema['additionalProperties'] is False
    export_schemas.export(tmp_path, check=False)
    target = tmp_path / 'shot.record.schema.json'
    target.unlink()
    assert export_schemas.export(tmp_path, check=True) == 1
    assert not target.exists()
    target.write_text('{}\n')
    assert export_schemas.export(tmp_path, check=True) == 1
    assert target.read_text() == '{}\n'


@pytest.mark.parametrize(
    'revision', ['legacy', '0001_initial', '0002_job_results', '0003_fixture_jobs']
)
def test_all_migration_entry_points_preserve_shots(tmp_path, monkeypatch, revision):
    target = str(tmp_path / 'shots.db')
    if revision == 'legacy':
        with closing(sqlite3.connect(target)) as connection:
            connection.executescript(
                (Path(__file__).parent / 'fixtures/legacy_schema.sql').read_text()
            )
    else:
        upgrade = db.command.upgrade
        with monkeypatch.context() as patch:
            patch.setattr(db.command, 'upgrade', lambda config, _: upgrade(config, revision))
            db.init_db(target)
    rows = [
        (0, 999, -1, 0.0, '', None),
        (2, 999, 0, -2.5, '  বাংলা\nkeep spaces  ', '  unknown  '),
        (3, 999, 0, 1.125, 'x' * 10000, ''),
        (4, -1, 100, 10000.0, 'Saved', 'pending'),
    ]
    with closing(sqlite3.connect(target)) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.executemany('INSERT INTO shots VALUES (?, ?, ?, ?, ?, ?)', rows)
        connection.commit()
    for _ in range(2):
        db.init_db(target)
        with closing(sqlite3.connect(target)) as connection:
            connection.row_factory = sqlite3.Row
            stored = [dict(row) for row in connection.execute('SELECT * FROM shots ORDER BY id')]
            assert [tuple(row.values()) for row in stored] == rows
            assert set(ShotRecord.model_fields) == {
                row['name'] for row in connection.execute('PRAGMA table_info(shots)')
            }
            assert (
                connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]
                == '0003_fixture_jobs'
            )
            assert connection.execute('PRAGMA foreign_key_list(shots)').fetchall() == []
            assert connection.execute('SELECT COUNT(*) FROM projects').fetchone()[0] == 0
        for row in stored:
            record = ShotRecord.model_validate(row)
            assert record.model_dump() == row
            assert json.loads(record.model_dump_json()) == row


def test_sql_defaults_and_required_record_fields(tmp_path):
    target = str(tmp_path / 'defaults.db')
    db.init_db(target)
    with closing(sqlite3.connect(target)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute(
            "INSERT INTO shots (project_id, order_index, duration_seconds, prompt) VALUES (1, 0, 5, 'Shot')"
        )
        connection.commit()
        row = dict(connection.execute('SELECT * FROM shots').fetchone())
        assert row['status'] == 'pending'
        assert type(row['duration_seconds']) is float
    record = ShotRecord.model_validate(row)
    assert record.model_dump() == row
    for key in row:
        with pytest.raises(ValidationError):
            ShotRecord.model_validate({k: v for k, v in row.items() if k != key})
    with pytest.raises(ValidationError):
        record.prompt = 'Changed'


@pytest.mark.parametrize(
    'patch',
    [
        {'id': '1'},
        {'project_id': True},
        {'order_index': 1.5},
        {'duration_seconds': '1.5'},
        {'duration_seconds': True},
        {'duration_seconds': float('inf')},
        {'duration_seconds': float('nan')},
        {'prompt': b'bytes'},
        {'prompt': None},
        {'status': 1},
        {'artifacts': []},
    ],
)
def test_record_rejects_coercion_and_non_json_numbers(patch):
    row = dict(id=1, project_id=1, order_index=0, duration_seconds=1.5, prompt='', status=None)
    with pytest.raises(ValidationError):
        ShotRecord.model_validate({**row, **patch})
