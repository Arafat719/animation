"""Run the local API and Vite together: python3 scripts/dev.py (Linux)."""

import argparse
import errno
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
HOST = '127.0.0.1'
API_PORT = 8000
WEB_PORT = 5173


class StartupError(Exception):
    pass


@dataclass(frozen=True)
class Service:
    name: str
    command: list[str]
    cwd: Path
    url: str


def check_port(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((HOST, port))
        except OSError as error:
            if error.errno == errno.EADDRINUSE:
                raise StartupError(
                    f'{HOST}:{port} port ব্যস্ত। ওই server বন্ধ করে আবার চালান।'
                ) from error
            raise StartupError(f'{HOST}:{port} port ব্যবহার করা যাচ্ছে না: {error}') from error


def services(root: Path) -> list[Service]:
    python = root / '.venv/bin/python'
    vite = root / 'apps/web/node_modules/vite/bin/vite.js'
    if not python.is_file():
        raise StartupError('প্রজেক্টের .venv নেই। README-এর Local backend setup অনুসরণ করুন।')
    node = shutil.which('node')
    if node is None:
        raise StartupError('Node.js পাওয়া যায়নি। Node.js 22.12+ install করুন।')
    if not vite.is_file():
        raise StartupError('Frontend dependencies নেই। চালান: npm --prefix apps/web ci')
    try:
        version = subprocess.run(
            [node, '--version'], capture_output=True, text=True, check=True, timeout=10
        ).stdout.strip()
        major, minor, *_ = map(int, version.lstrip('v').split('.'))
        if (major, minor) < (22, 12):
            raise StartupError(f'Node.js 22.12+ প্রয়োজন; পাওয়া গেছে {version}।')
        subprocess.run(
            [
                str(python),
                '-c',
                'import uvicorn; from apps.api.main import app; '
                'from animation_studio.settings import get_settings; get_settings()',
            ],
            cwd=root,
            capture_output=True,
            check=True,
            timeout=10,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise StartupError(
            'Dependencies/settings যাচাই ব্যর্থ। README অনুযায়ী dependencies install '
            'ও ANIMATION_DB_PATH যাচাই করুন।'
        ) from error
    return [
        Service(
            'API',
            [
                str(python),
                '-m',
                'uvicorn',
                'apps.api.main:app',
                '--host',
                HOST,
                '--port',
                str(API_PORT),
                '--workers',
                '1',
                '--lifespan',
                'on',
                '--no-access-log',
            ],
            root,
            f'http://{HOST}:{API_PORT}/health',
        ),
        Service(
            'Web',
            [
                node,
                str(vite),
                '--host',
                HOST,
                '--port',
                str(WEB_PORT),
                '--strictPort',
                '--clearScreen',
                'false',
            ],
            root / 'apps/web',
            f'http://{HOST}:{WEB_PORT}/',
        ),
    ]


def ready(url: str) -> bool:
    # Local readiness must not depend on a user's HTTP proxy configuration.
    try:
        with build_opener(ProxyHandler({})).open(url, timeout=0.3) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def signal_group(process: subprocess.Popen, signum: int) -> None:
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        pass


def stop_children(children: list[tuple[Service, subprocess.Popen]], timeout: float) -> None:
    # Signal our own sessions, including descendants if a service leader exited.
    for _, process in children:
        signal_group(process, signal.SIGTERM)
    deadline = time.monotonic() + timeout
    for _, process in children:
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    for _, process in children:
        signal_group(process, signal.SIGKILL)
        process.wait()


def supervise(
    selected: list[Service],
    stop: threading.Event,
    *,
    startup_timeout: float = 30,
    shutdown_timeout: float = 5,
) -> int:
    children: list[tuple[Service, subprocess.Popen]] = []
    try:
        for service in selected:
            if stop.is_set():
                return 0
            process = subprocess.Popen(service.command, cwd=service.cwd, start_new_session=True)
            children.append((service, process))
        deadline = time.monotonic() + startup_timeout
        announced = False
        while not stop.is_set():
            for service, process in children:
                if process.poll() is not None:
                    raise StartupError(
                        f'{service.name} বন্ধ হয়েছে (exit {process.returncode})। '
                        'উপরের server log দেখুন; দুটো server বন্ধ করা হচ্ছে।'
                    )
            if not announced:
                if all(ready(service.url) for service, _ in children):
                    # Detect children that exited while the HTTP probes were running.
                    if any(process.poll() is not None for _, process in children):
                        continue
                    print(
                        f'প্রস্তুত: http://{HOST}:{WEB_PORT}\n'
                        f'API: http://{HOST}:{API_PORT}\n'
                        'বন্ধ করতে Ctrl+C চাপুন।',
                        flush=True,
                    )
                    announced = True
                elif time.monotonic() >= deadline:
                    raise StartupError(
                        f'{startup_timeout:g} সেকেন্ডে API/web প্রস্তুত হয়নি। উপরের server log দেখুন।'
                    )
            stop.wait(0.1)
        return 0
    except (StartupError, OSError) as error:
        print(f'চালু রাখা যায়নি: {error}', file=sys.stderr, flush=True)
        return 1
    finally:
        if children:
            stop_children(children, shutdown_timeout)
            print('এই launcher-এর API/web process বন্ধ হয়েছে।', flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    if sys.platform != 'linux':
        print('এই launcher Linux-এর জন্য। অন্য platform-এ README-এর আলাদা commands ব্যবহার করুন।')
        return 1
    stop = threading.Event()
    previous = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        previous[signum] = signal.signal(signum, lambda *_: stop.set())
    try:
        # Check both ports before starting either server; Vite must never auto-increment.
        check_port(API_PORT)
        check_port(WEB_PORT)
        selected = services(ROOT)
        return supervise(selected, stop)
    except (StartupError, OSError) as error:
        print(f'চালু করা যায়নি: {error}', file=sys.stderr, flush=True)
        return 1
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == '__main__':
    raise SystemExit(main())
