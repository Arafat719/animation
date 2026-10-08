"""Test-only fixed mock child substitution; production launcher stays dummy-only."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from animation_studio.providers.comfy_dummy_supervisor import _DUMMY, supervise_dummy
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_journal import _fingerprint
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy
from animation_studio.providers.comfy_workflow import (
    MODEL_NAME,
    MODEL_VERSION,
    build_image_workflow,
)
from animation_studio.providers.image import ImageRequest

SCRIPT = r"""
import json, os, signal, socket, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'tests'))
import httpx
from test_comfy_http import Server, PROMPT_ID
from animation_studio.providers.comfy_http import ComfyHTTPExecutor, ComfyReceipt
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_journal import _fingerprint
from animation_studio.providers.comfy_v2_executor import DurableComfyExecutorV2
from animation_studio.providers.comfy_workflow import build_image_workflow, MODEL_NAME, MODEL_VERSION
from animation_studio.providers.image import ImageRequest, ImageProviderError

def forbidden(*a, **kw):
    raise AssertionError('Network forbidden')
socket.socket = socket.getaddrinfo = forbidden
root, phase, action = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
graph = build_image_workflow(ImageRequest(prompt='A house', model_name=MODEL_NAME,
                                        model_version=MODEL_VERSION, seed=42))
server = Server(graph)

def hang():
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    os.write(1, b'R')
    while True:
        signal.pause()

def handler(request):
    with (root / 'requests.jsonl').open('ab') as f:
        f.write((json.dumps([request.method, request.url.path]) + '\n').encode())
        f.flush()
        os.fsync(f.fileno())
    response = server(request)
    if action == 'execute' and phase == 'submitted' and request.url.path == '/prompt':
        hang()
    return response

client = ComfyHTTPExecutor(transport=httpx.MockTransport(handler), max_polls=1)
context = ComfyExecutionContext(mode='mock', job_id=PROMPT_ID, graph_sha256=_fingerprint(graph),
    origin=client.origin, deployment_id=PROMPT_ID,
    runtime_manifest_sha256='a'*64, model_manifest_sha256='b'*64)
executor = DurableComfyExecutorV2(client, root, context)
if action == 'execute':
    server.pending = 1
    create, accept, transition = executor.store.create_intent, executor.store.accept, executor.supervision.transition
    def create_hook():
        create()
        if phase == 'intent': hang()
    def accept_hook(receipt):
        accept(receipt)
        if phase == 'accepted': hang()
    def transition_hook(record):
        transition(record)
        if phase == 'cancelled' and record.cleanup_phase == 'observed': hang()
    executor.store.create_intent = create_hook
    executor.store.accept = accept_hook
    executor.supervision.transition = transition_hook
    executor.execute(graph)
    raise AssertionError('Boundary not reached')
else:
    original = executor.store.path.read_bytes()
    sidecar = executor.supervision.path
    original_sidecar = sidecar.read_bytes() if sidecar.exists() else None
    try:
        executor.execute(graph)
    except ImageProviderError as error:
        assert error.code == 'execution_failed'
    else:
        raise AssertionError('Duplicate submit allowed')
    if phase in ('intent', 'submitted'):
        try:
            executor.recover(graph)
        except ImageProviderError as error:
            assert error.code == 'execution_failed'
        else:
            raise AssertionError('Intent-only recovery allowed')
    else:
        assert executor.recover(graph) == server.png
    if phase == 'cancelled':
        with executor.store.locked():
            result = executor._cancel_durably(ComfyReceipt(PROMPT_ID),
                ImageProviderError('timeout', 'fixture'))
            assert result.dispatched is None and result.error_code == 'io_error'
            assert executor.supervision.read().compute_status == 'unknown'
    assert executor.store.path.read_bytes() == original
    assert (sidecar.read_bytes() if sidecar.exists() else None) == original_sidecar
    client.close()
"""


@pytest.mark.parametrize(
    'phase,submits,cancels',
    [
        ('intent', 0, 0),
        ('submitted', 1, 0),
        ('accepted', 1, 0),
        ('cancelled', 1, 1),
    ],
)
def test_supervised_kill_preserves_recovery(tmp_path, monkeypatch, phase, submits, cancels):
    tmp_path.chmod(0o700)
    cwd = Path(__file__).resolve().parents[1]
    context = ComfyExecutionContext(
        mode='mock',
        job_id='12345678-1234-4234-8234-123456789abc',
        deployment_id='12345678-1234-4234-8234-123456789abc',
        origin='https://comfy.invalid:443/',
        graph_sha256=_fingerprint(
            build_image_workflow(
                ImageRequest(
                    prompt='A house', model_name=MODEL_NAME, model_version=MODEL_VERSION, seed=42
                )
            )
        ),
        runtime_manifest_sha256='a' * 64,
        model_manifest_sha256='b' * 64,
    )
    policy = ComfySupervisionPolicy(
        ram_limit_bytes=100,
        host_reserve_bytes=20,
        vram_limit_bytes=80,
        device_index=0,
        sample_interval_seconds=0.01,
        stale_after_seconds=0.1,
        overall_timeout_seconds=3,
        cleanup_reserve_seconds=0.4,
        reap_allowance_seconds=0.4,
    )
    real_spawn = subprocess.Popen
    children = []

    def fixed_mock_child(argv, **kwargs):
        assert argv == [sys.executable, '-I', '-S', '-c', _DUMMY, 'ignore_stop']
        child = real_spawn(
            [sys.executable, '-c', SCRIPT, str(tmp_path), phase, 'execute'], cwd=cwd, **kwargs
        )
        children.append(child)
        return child

    with monkeypatch.context() as patch:
        patch.setattr(subprocess, 'Popen', fixed_mock_child)
        result = supervise_dummy(
            policy=policy, context=context, mode='ignore_stop', telemetry='missing_when_ready'
        )
    assert len(children) == 1
    assert result.ready and result.stop_requested and result.kill_requested
    assert result.outcome == 'aborted' and result.reasons == ('telemetry_missing',)
    assert result.returncode == -signal.SIGKILL and result.worker_status == 'exited'
    assert result.job_status == result.compute_status == result.storage_status == 'unknown'
    with pytest.raises(ChildProcessError):
        os.waitpid(result.child_pid, os.WNOHANG)
    ledger = tmp_path / 'requests.jsonl'
    before = ledger.read_bytes().splitlines()
    calls = [json.loads(line) for line in before]
    assert sum(method == 'POST' and path == '/prompt' for method, path in calls) == submits
    assert sum(path.endswith('/cancel') for _, path in calls) == cancels
    records = {p.name: p.read_bytes() for p in tmp_path.glob('*.json')}
    generation = [
        json.loads(data) for name, data in records.items() if not name.endswith('.supervision.json')
    ]
    assert len(generation) == 1
    assert generation[0]['state'] == ('intent' if phase in ('intent', 'submitted') else 'accepted')
    for key, value in context.model_dump().items():
        assert generation[0][key] == value
    sidecars = [
        json.loads(data) for name, data in records.items() if name.endswith('.supervision.json')
    ]
    assert len(sidecars) == (1 if phase == 'cancelled' else 0)
    if sidecars:
        assert sidecars[0]['cleanup_phase'] == 'observed'
        assert sidecars[0]['attempt_count'] == 1
    for _ in range(2):
        recovered = subprocess.run(
            [sys.executable, '-c', SCRIPT, str(tmp_path), phase, 'recover'],
            cwd=cwd,
            timeout=10,
            capture_output=True,
            check=False,
        )
        assert recovered.returncode == 0, recovered.stderr.decode()
        assert {p.name: p.read_bytes() for p in tmp_path.glob('*.json')} == records
    after = ledger.read_bytes().splitlines()
    assert after[: len(before)] == before
    recovery = [json.loads(line) for line in after[len(before) :]]
    if phase in ('intent', 'submitted'):
        assert recovery == []
    else:
        assert len(recovery) == 4
        assert all(method == 'GET' for method, _ in recovery)
        assert [path.split('/')[1] for _, path in recovery] == ['history', 'view'] * 2
