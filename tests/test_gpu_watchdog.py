import os
import select
import subprocess
import sys
import time

import pytest

from animation_studio.providers.gpu_journal import MockSessionJournal, SessionRecord

MODULE = 'animation_studio.providers.gpu_watchdog'


def paths(tmp_path, duration=30):
    journal = tmp_path / 'journal.json'
    fixture = tmp_path / 'record.json'
    now = time.time()
    fixture.write_text(
        SessionRecord(
            session_id='fixture', pod_id='owned', created_at_utc=now, deadline_at_utc=now + duration
        ).model_dump_json()
    )
    return journal, fixture


def launch(journal, fixture=None, scenario=None):
    args = [sys.executable, '-m', MODULE, str(journal)]
    if scenario:
        args += ['--mock-rest-scenario', scenario]
    if fixture:
        args += ['--arm-record', str(fixture)]
    return subprocess.Popen(
        args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def ready(process):
    assert select.select([process.stdout], [], [], 5)[0], 'No readiness acknowledgement'
    assert process.stdout.readline() == b'READY\n'


def stop(process):
    if process.poll() is None:
        process.kill()
    process.communicate(timeout=5)


def test_explicit_completion_and_no_deadline_reset_on_restart(tmp_path):
    journal, fixture = paths(tmp_path)
    process = launch(journal, fixture)
    try:
        ready(process)
        assert not MockSessionJournal(journal)._read().cleanup_requested
        out, err = process.communicate(b'finished', timeout=5)
        assert process.returncode == 2 and not err
        assert out == b'needs_manual_cleanup\n'
        before = journal.read_bytes()
        restarted = launch(journal)
        try:
            restarted.communicate(timeout=5)
            assert restarted.returncode == 2
            assert journal.read_bytes() == before
        finally:
            stop(restarted)
    finally:
        stop(process)


def test_deadline_works_while_parent_pipe_remains_open(tmp_path):
    journal, fixture = paths(tmp_path, duration=1.0)
    process = launch(journal, fixture)
    try:
        ready(process)
        process.wait(timeout=5)
        assert process.returncode == 2
        assert MockSessionJournal(journal)._read().last_compute == 'absent'
    finally:
        stop(process)


def test_runner_crash_then_restart_recovers_unfinished_session(tmp_path):
    journal, fixture = paths(tmp_path)
    process = launch(journal, fixture)
    try:
        ready(process)
        process.kill()
        process.wait(timeout=5)
        restarted = launch(journal)
        try:
            restarted.wait(timeout=5)
            assert restarted.returncode == 2
            result = MockSessionJournal(journal)._read()
            assert result.cleanup_requested and result.attempt_count == 1
        finally:
            stop(restarted)
    finally:
        stop(process)


def test_second_runner_cannot_take_over_armed_session(tmp_path):
    journal, fixture = paths(tmp_path)
    first = launch(journal, fixture)
    try:
        ready(first)
        second = launch(journal)
        try:
            out, err = second.communicate(timeout=5)
            assert second.returncode == 1 and not out and err == b'watchdog_failed\n'
            assert not MockSessionJournal(journal)._read().cleanup_requested
        finally:
            stop(second)
    finally:
        stop(first)


@pytest.mark.parametrize('scenario', ['memory', 'success'])
def test_actual_parent_death_triggers_independent_child(tmp_path, scenario):
    journal, fixture = paths(tmp_path)
    output = tmp_path / 'child.log'
    # Child has its own process session and holds only the read side of the pipe.
    script = """import subprocess,sys,time
with open(sys.argv[3], 'wb') as out:
 p=subprocess.Popen([sys.executable,'-m',sys.argv[4],sys.argv[1],
 '--arm-record',sys.argv[2]] + ([] if sys.argv[5]=='memory' else
 ['--mock-rest-scenario',sys.argv[5]]),stdin=subprocess.PIPE,stdout=out,stderr=out,
 start_new_session=True)
 print(p.pid,flush=True)
 time.sleep(30)
"""
    parent = subprocess.Popen(
        [sys.executable, '-c', script, str(journal), str(fixture), str(output), MODULE, scenario],
        stdout=subprocess.PIPE,
    )
    child_pid = None
    try:
        assert select.select([parent.stdout], [], [], 5)[0]
        child_pid = int(parent.stdout.readline())
        until = time.monotonic() + 5
        while time.monotonic() < until:
            if output.exists() and b'READY' in output.read_bytes():
                break
            time.sleep(0.02)
        assert b'READY' in output.read_bytes()
        parent.kill()
        parent.wait(timeout=5)
        until = time.monotonic() + 5
        while time.monotonic() < until:
            if b'needs_manual_cleanup' in output.read_bytes():
                break
            time.sleep(0.02)
        assert b'needs_manual_cleanup' in output.read_bytes()
        assert MockSessionJournal(journal)._read().last_compute == 'absent'
    finally:
        stop(parent)
        if child_pid is not None and b'needs_manual_cleanup' not in output.read_bytes():
            try:
                os.kill(child_pid, 9)
            except ProcessLookupError:
                pass


def test_invalid_record_never_acknowledges_ready(tmp_path):
    journal, fixture = paths(tmp_path)
    fixture.write_text('{"secret":"do-not-echo"}')
    process = launch(journal, fixture)
    try:
        out, err = process.communicate(timeout=5)
        assert process.returncode == 1 and not out and err == b'watchdog_failed\n'
        assert not journal.exists()
    finally:
        stop(process)
