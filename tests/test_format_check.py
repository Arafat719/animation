"""The legacy allowance must never exempt new or edited source files."""

import hashlib
import json
import subprocess

import pytest

from scripts import check_format


def test_baseline_only_exempts_exact_existing_content(tmp_path):
    original = b'x=1\n'
    (tmp_path / 'old.py').write_bytes(original)
    (tmp_path / 'new.py').write_bytes(original)
    baseline = {'old.py': hashlib.sha256(original).hexdigest()}
    files = ['old.py', 'new.py']
    assert check_format.pending_files(tmp_path, files, baseline) == ['new.py']

    (tmp_path / 'old.py').write_bytes(b'x=2\n')
    assert check_format.pending_files(tmp_path, files, baseline) == files


def test_discovery_includes_untracked_and_handles_deleted_ignored_and_spaces(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    (tmp_path / '.gitignore').write_text('ignored.py\n')
    for name in ['tracked.py', 'deleted.py']:
        (tmp_path / name).write_text('x = 1\n')
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    (tmp_path / 'deleted.py').unlink()
    for name in ['new file.py', 'ignored.py']:
        (tmp_path / name).write_text('x = 1\n')
    web = tmp_path / 'apps/web'
    web.mkdir(parents=True)
    for name in ['app.tsx', 'style.css', 'index.html', 'package.json', 'package-lock.json']:
        (web / name).write_text('')
    (web / 'dist').mkdir()
    (web / 'dist/bundle.js').write_text('')
    (web / 'public/schemas/v1').mkdir(parents=True)
    (web / 'public/schemas/v1/project.record.schema.json').write_text('{}')

    assert check_format.source_files(tmp_path, 'backend') == ['new file.py', 'tracked.py']
    assert check_format.source_files(tmp_path, 'frontend') == [
        'apps/web/app.tsx',
        'apps/web/index.html',
        'apps/web/package.json',
        'apps/web/style.css',
    ]


@pytest.mark.parametrize('scope', ['backend', 'frontend'])
@pytest.mark.parametrize('exit_code', [0, 1, 2])
def test_check_passes_file_as_single_argument_and_preserves_exit_code(
    tmp_path, monkeypatch, scope, exit_code
):
    name = 'file with spaces.py' if scope == 'backend' else 'file with spaces.tsx'
    (tmp_path / name).write_text('')
    (tmp_path / '.format-baseline.json').write_text(json.dumps({scope: {}}))
    monkeypatch.setattr(check_format, 'source_files', lambda *_: [name])
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs['cwd'] == tmp_path
        assert '--check' in command
        assert '--write' not in command
        return subprocess.CompletedProcess(command, exit_code)

    monkeypatch.setattr(check_format.subprocess, 'run', run)
    assert check_format.check(tmp_path, scope) == exit_code
    assert calls[0][-1] == name


def test_all_includes_unchanged_debt(tmp_path, monkeypatch):
    original = b'x=1\n'
    (tmp_path / 'old.py').write_bytes(original)
    (tmp_path / '.format-baseline.json').write_text(
        json.dumps({'backend': {'old.py': hashlib.sha256(original).hexdigest()}})
    )
    monkeypatch.setattr(check_format, 'source_files', lambda *_: ['old.py'])
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(check_format.subprocess, 'run', run)
    assert check_format.check(tmp_path, 'backend') == 0
    assert not calls
    assert check_format.check(tmp_path, 'backend', strict=True) == 1
    assert calls[0][-1] == 'old.py'


@pytest.mark.parametrize('content', ['not json', '{}'])
def test_broken_baseline_fails_closed(tmp_path, monkeypatch, content):
    (tmp_path / '.format-baseline.json').write_text(content)
    monkeypatch.setattr(check_format, 'ROOT', tmp_path)
    monkeypatch.setattr(check_format, 'source_files', lambda *_: ['old.py'])
    monkeypatch.setattr(check_format.sys, 'argv', ['check_format.py', 'backend'])
    assert check_format.main() == 2
