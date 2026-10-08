"""Real process exit at mock cancellation boundaries; no remote server claims."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = r"""
import json, os, socket, sys
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

def forbidden(*args, **kwargs):
    raise AssertionError('No sockets or DNS')
socket.socket = forbidden
socket.getaddrinfo = forbidden
root, phase, action = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
graph = build_image_workflow(ImageRequest(prompt='A house', model_name=MODEL_NAME,
                                        model_version=MODEL_VERSION, seed=42))
server = Server(graph)
ledger = root / 'requests.jsonl'
def handler(request):
    with ledger.open('ab') as stream:
        stream.write((json.dumps([request.method, request.url.path]) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    if action == 'crash' and request.url.path.endswith('/cancel'):
        assert executor.supervision.read().cleanup_phase == 'intent'
    return server(request)
client = ComfyHTTPExecutor(transport=httpx.MockTransport(handler), max_polls=1)
context = ComfyExecutionContext(mode='mock', job_id=PROMPT_ID, graph_sha256=_fingerprint(graph),
    origin=client.origin, deployment_id=PROMPT_ID,
    runtime_manifest_sha256='a'*64, model_manifest_sha256='b'*64)
executor = DurableComfyExecutorV2(client, root, context)
if action == 'crash':
    server.pending = 1
    create = executor.supervision.create
    transition = executor.supervision.transition
    cancel = client._cancel_receipt
    def crash_create(record):
        result = create(record)
        if phase == 'initial':
            os._exit(73)
        return result
    def crash_transition(record):
        result = transition(record)
        if (phase == 'intent' and record.cleanup_phase == 'intent') or (
            phase == 'observed' and record.cleanup_phase == 'observed'):
            os._exit(73)
        return result
    def crash_cancel(receipt):
        result = cancel(receipt)
        if phase == 'ack':
            os._exit(73)
        return result
    executor.supervision.create = crash_create
    executor.supervision.transition = crash_transition
    client._cancel_receipt = crash_cancel
    executor.execute(graph)
    raise AssertionError('Crash hook not reached')
else:
    saved_job = executor.store.path.read_bytes()
    saved_sidecar = executor.supervision.path.read_bytes()
    try:
        executor.execute(graph)
    except ImageProviderError:
        pass
    else:
        raise AssertionError('Duplicate generation accepted')
    # Even an explicit re-entry to the cleanup handler must not dispatch again.
    with executor.store.locked():
        result = executor._cancel_durably(ComfyReceipt(PROMPT_ID),
                                         ImageProviderError('timeout', 'fixture'))
        assert result.dispatched is None and result.error_code == 'io_error'
        assert executor.supervision.read().compute_status == 'unknown'
    assert executor.recover(graph) == server.png
    assert executor.store.path.read_bytes() == saved_job
    assert executor.supervision.path.read_bytes() == saved_sidecar
    client.close()
"""


@pytest.mark.parametrize(
    'phase,state,cancels',
    [
        ('initial', 'not_requested', 0),
        ('intent', 'intent', 0),
        ('ack', 'intent', 1),
        ('observed', 'observed', 1),
    ],
)
def test_process_crash_no_duplicate_cancel(tmp_path, phase, state, cancels):
    tmp_path.chmod(0o700)
    cwd = Path(__file__).resolve().parents[1]

    def run(action):
        return subprocess.run(
            [sys.executable, '-c', SCRIPT, str(tmp_path), phase, action],
            cwd=cwd,
            timeout=20,
            capture_output=True,
            check=False,
        )

    crashed = run('crash')
    assert crashed.returncode == 73, crashed.stderr.decode()
    sidecar = next(tmp_path.glob('*.supervision.json'))
    record = json.loads(sidecar.read_bytes())
    assert record['cleanup_phase'] == state
    assert record['attempt_count'] == (0 if phase == 'initial' else 1)
    ledger = tmp_path / 'requests.jsonl'
    before = ledger.read_bytes().splitlines()
    calls = [json.loads(line) for line in before]
    assert sum(path.endswith('/cancel') for _, path in calls) == cancels
    assert sum(method == 'POST' and path == '/prompt' for method, path in calls) == 1
    for _ in range(2):
        recovered = run('recover')
        assert recovered.returncode == 0, recovered.stderr.decode()
    after = ledger.read_bytes().splitlines()
    assert after[: len(before)] == before
    recovery_calls = [json.loads(line) for line in after[len(before) :]]
    assert len(recovery_calls) == 4
    assert all(method == 'GET' for method, _ in recovery_calls)
