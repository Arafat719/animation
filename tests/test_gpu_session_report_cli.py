import subprocess
import sys
from pathlib import Path

import pytest
from test_gpu_durable_session import open_session

from animation_studio.providers.gpu_attempts import LocalAttemptLedger
from animation_studio.providers.gpu_lifecycle import ResourceState
from scripts.report_gpu_session import main


@pytest.mark.parametrize(
    'storage,label', [('none', 'নেই'), ('retained', 'রয়ে গেছে'), ('unknown', 'অজানা')]
)
def test_saved_report_command_is_historical_and_read_only(tmp_path, storage, label):
    path = tmp_path / 'ledger.json'
    LocalAttemptLedger(path).initialize()
    session, _, backend = open_session(path)
    backend.state = ResourceState('owned', 'running', storage)
    session.finish()
    # Read while the owner lease is still held.
    before = path.read_bytes(), set(tmp_path.iterdir())
    try:
        result = subprocess.run(
            [
                sys.executable,
                '-m',
                'scripts.report_gpu_session',
                '--ledger',
                str(path),
                '--render-id',
                'render',
            ],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0 and not result.stderr
        assert 'বর্তমান GPU বা billing যাচাই হয়নি' in result.stdout
        assert f'Storage: {label}' in result.stdout
        assert 'Compute: অনুপস্থিত' in result.stdout
        assert ('billing বন্ধ ধরে নেবেন না' in result.stdout) == (storage != 'none')
        assert (path.read_bytes(), set(tmp_path.iterdir())) == before
    finally:
        session.release()


@pytest.mark.parametrize('mode,code', [('missing', 2), ('corrupt', 2), ('empty', 1), ('active', 0)])
def test_empty_unknown_and_errors(tmp_path, capsys, mode, code):
    path = tmp_path / 'ledger.json'
    session = None
    if mode != 'missing':
        LocalAttemptLedger(path).initialize()
    if mode == 'corrupt':
        path.write_text('{"secret": "must-not-print"}')
    if mode == 'active':
        session, _, _ = open_session(path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    try:
        assert main(['--ledger', str(path), '--render-id', 'render']) == code
        output = capsys.readouterr()
        assert 'must-not-print' not in output.out + output.err
        assert bool(output.err) == (code == 2)
        if mode == 'active':
            assert 'Compute: অজানা' in output.out and 'Storage: অজানা' in output.out
            assert 'সংরক্ষিত cleanup সম্পূর্ণ: না' in output.out
        assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    finally:
        if session is not None:
            session.release()
