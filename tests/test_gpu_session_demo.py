import socket
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from animation_studio.providers.gpu_attempts import LocalAttemptLedger
from scripts import demo_gpu_session


def track_directories(monkeypatch, tmp_path):
    paths = []

    def temporary(**kwargs):
        directory = TemporaryDirectory(dir=tmp_path, **kwargs)
        paths.append(Path(directory.name))
        return directory

    monkeypatch.setattr(demo_gpu_session, 'TemporaryDirectory', temporary)
    return paths


def test_demo_without_network_cleans_up_and_preserves_user_files(monkeypatch, tmp_path, capsys):
    paths = track_directories(monkeypatch, tmp_path)
    user_file = tmp_path / 'existing-ledger.json'
    user_file.write_text('leave unchanged')

    def no_network(*args, **kwargs):
        raise AssertionError('Network forbidden')

    monkeypatch.setattr(socket, 'socket', no_network)
    for _ in range(2):
        assert demo_gpu_session.main([]) == 0
        output = capsys.readouterr()
        assert not output.err
        assert 'Compute: অজানা' in output.out
        assert 'Compute: অনুপস্থিত' in output.out
        assert 'Storage: রয়ে গেছে' in output.out
        assert 'সংরক্ষিত cleanup সম্পূর্ণ: হ্যাঁ' not in output.out
        assert 'Mock submit status: queued' in output.out
        assert 'অস্থায়ী demo files সরানো হয়েছে' in output.out
    assert len(paths) == 2 and all(not path.exists() for path in paths)
    assert list(tmp_path.iterdir()) == [user_file]
    assert user_file.read_text() == 'leave unchanged'


def test_failed_demo_is_nonzero_and_removes_temporary_files(monkeypatch, tmp_path, capsys):
    paths = track_directories(monkeypatch, tmp_path)

    def failure(*args):
        raise OSError('sensitive fixture details')

    monkeypatch.setattr(LocalAttemptLedger, '_write', failure)
    assert demo_gpu_session.main([]) == 1
    output = capsys.readouterr()
    assert 'ব্যর্থ' in output.err
    assert 'sensitive' not in output.err
    assert 'অস্থায়ী demo files সরানো হয়েছে' not in output.out
    assert paths and all(not path.exists() for path in paths)


def test_demo_module_entrypoint():
    result = subprocess.run(
        [sys.executable, '-m', 'scripts.demo_gpu_session'],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0 and not result.stderr
    assert 'real GPU, model বা animation তৈরি হচ্ছে না' in result.stdout
    assert 'অস্থায়ী demo files সরানো হয়েছে' in result.stdout
