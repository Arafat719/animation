"""Local process ownership, failure cleanup and port-conflict regression checks."""

import signal
import socket
import subprocess
import sys
import threading
import time

import pytest

from scripts import dev

pytestmark = pytest.mark.skipif(sys.platform != 'linux', reason='Linux development launcher')


def service(tmp_path, name, code='import time; time.sleep(60)'):
    return dev.Service(name, [sys.executable, '-u', '-c', code], tmp_path, 'http://127.0.0.1/')


@pytest.fixture
def children(monkeypatch):
    processes = []
    original = subprocess.Popen

    def start(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(dev.subprocess, 'Popen', start)
    yield processes
    # A failed assertion must not leave the test's processes running.
    for process in processes:
        dev.signal_group(process, signal.SIGKILL)
        process.wait(timeout=5)


def test_conflicting_port_is_reported_without_closing_existing_listener():
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((dev.HOST, 0))
        listener.listen()
        port = listener.getsockname()[1]
        with pytest.raises(dev.StartupError, match=f'{port} port ব্যস্ত'):
            dev.check_port(port)
        assert listener.getsockname()[1] == port
        with socket.create_connection((dev.HOST, port), timeout=1):
            connection, _ = listener.accept()
            connection.close()
    dev.check_port(port)


def test_missing_virtual_environment_has_setup_instruction(tmp_path):
    with pytest.raises(dev.StartupError, match='Local backend setup'):
        dev.services(tmp_path)


def test_missing_frontend_dependencies_has_install_instruction(tmp_path, monkeypatch):
    python = tmp_path / '.venv/bin/python'
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setattr(dev.shutil, 'which', lambda _: '/node')
    with pytest.raises(dev.StartupError, match='npm --prefix apps/web ci'):
        dev.services(tmp_path)


def test_stop_closes_both_processes_without_touching_unrelated_process(
    tmp_path, monkeypatch, children
):
    stop = threading.Event()
    monkeypatch.setattr(dev, 'ready', lambda _: True)
    # Launch the unrelated process separately; it is never registered with the supervisor.
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    timer = threading.Timer(0.4, stop.set)
    timer.start()
    try:
        assert dev.supervise([service(tmp_path, 'API'), service(tmp_path, 'Web')], stop) == 0
        assert len(children) == 3
        assert all(process.poll() is not None for process in children[1:])
        assert unrelated.poll() is None
    finally:
        timer.cancel()
        unrelated.terminate()
        unrelated.wait(timeout=5)


@pytest.mark.parametrize('exit_code', [0, 7])
def test_unexpected_service_exit_stops_sibling(tmp_path, monkeypatch, children, exit_code):
    monkeypatch.setattr(dev, 'ready', lambda _: True)
    selected = [
        service(tmp_path, 'API', f'raise SystemExit({exit_code})'),
        service(tmp_path, 'Web'),
    ]
    assert dev.supervise(selected, threading.Event(), startup_timeout=2) == 1
    assert len(children) == 2
    assert all(process.poll() is not None for process in children)


def test_second_spawn_failure_cleans_up_first_child(tmp_path, children):
    selected = [
        service(tmp_path, 'API'),
        dev.Service('Web', ['/no-such-animation-command'], tmp_path, 'http://127.0.0.1/'),
    ]
    assert dev.supervise(selected, threading.Event()) == 1
    assert len(children) == 1
    assert children[0].poll() is not None


def test_readiness_timeout_cleans_up_both_children(tmp_path, monkeypatch, children):
    monkeypatch.setattr(dev, 'ready', lambda _: False)
    assert (
        dev.supervise(
            [service(tmp_path, 'API'), service(tmp_path, 'Web')],
            threading.Event(),
            startup_timeout=0.2,
        )
        == 1
    )
    assert len(children) == 2
    assert all(process.poll() is not None for process in children)


def test_stop_requested_before_launch_starts_no_children(tmp_path, children):
    stop = threading.Event()
    stop.set()
    assert dev.supervise([service(tmp_path, 'API')], stop) == 0
    assert children == []


def test_stubborn_child_is_killed_after_shutdown_deadline(tmp_path, monkeypatch, children):
    marker = tmp_path / 'ready'
    code = (
        'import signal, time; from pathlib import Path; '
        'signal.signal(signal.SIGTERM, signal.SIG_IGN); '
        f'Path({str(marker)!r}).touch(); time.sleep(60)'
    )
    stop = threading.Event()

    def ready(_):
        if marker.exists():
            stop.set()
        return marker.exists()

    monkeypatch.setattr(dev, 'ready', ready)
    assert (
        dev.supervise(
            [service(tmp_path, 'API', code)], stop, startup_timeout=2, shutdown_timeout=0.1
        )
        == 0
    )
    assert children[0].returncode == -signal.SIGKILL


def test_cleanup_reaches_descendant_after_parent_exits(tmp_path, children):
    marker = tmp_path / 'descendant-stopped'
    child_code = (
        'import signal, time; from pathlib import Path; '
        f'signal.signal(signal.SIGTERM, lambda *_: (Path({str(marker)!r}).touch(), exit(0))); '
        'print("ready", flush=True); time.sleep(60)'
    )
    parent_code = (
        'import subprocess, sys; '
        f'p = subprocess.Popen([sys.executable, "-u", "-c", {child_code!r}], '
        'stdout=subprocess.PIPE); p.stdout.readline()'
    )
    parent = subprocess.Popen(
        [sys.executable, '-c', parent_code], start_new_session=True, cwd=tmp_path
    )
    parent.wait(timeout=5)
    dev.signal_group(parent, signal.SIGTERM)
    deadline = time.monotonic() + 2
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert marker.exists()


def test_main_checks_both_ports_before_spawning(monkeypatch):
    checked = []

    def check(port):
        checked.append(port)
        if port == dev.WEB_PORT:
            raise dev.StartupError('occupied')

    monkeypatch.setattr(dev, 'check_port', check)
    monkeypatch.setattr(dev.sys, 'argv', ['dev.py'])
    monkeypatch.setattr(dev, 'services', lambda *_: pytest.fail('must not launch'))
    assert dev.main() == 1
    assert checked == [dev.API_PORT, dev.WEB_PORT]
