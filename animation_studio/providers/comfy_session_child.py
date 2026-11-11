"""Fixed offline-only executable child. Synthetic inventory, telemetry and PNG."""

import io
import json
import os
import socket
import stat
import sys
import time
from pathlib import Path
from threading import Event, Thread

import httpx
from PIL import Image
from pydantic import SecretStr

from animation_studio.providers.comfy_admission import (
    REQUIRED_CAPABILITIES,
    ComfyAdmissionObservation,
    admission_policy_sha256,
)
from animation_studio.providers.comfy_config import ComfyEndpointConfig
from animation_studio.providers.comfy_image import ComfyImageProvider
from animation_studio.providers.comfy_journal import _fingerprint
from animation_studio.providers.comfy_offline_session import (
    OfflineComfyAdmission,
    OfflineDurableComfySession,
)
from animation_studio.providers.comfy_preflight import COMBOS, OUTPUTS
from animation_studio.providers.comfy_resource_guard import ComfyResourceSample
from animation_studio.providers.comfy_session_supervisor import (
    MAX_IPC_BYTES,
    FixtureLaunch,
    FixtureTerminal,
    decode_message,
)
from animation_studio.providers.comfy_workflow import validate_image_workflow
from animation_studio.providers.image import ImageProviderError


def _hang():
    Event().wait()


def fixture_session(launch: FixtureLaunch, cancel: Event):
    """Explicit synthetic session; usable for caller-directed GET-only fixture recovery."""
    launch = FixtureLaunch.model_validate(launch.model_dump())
    graph, context, policy = launch.graph, launch.context, launch.policy
    validate_image_workflow(graph)
    if context.mode != 'mock' or context.graph_sha256 != _fingerprint(graph):
        raise ValueError('Expected matching fixture context')
    root = Path(launch.root)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Expected owned private fixture root')
    prompt_id = context.job_id
    image = io.BytesIO()
    Image.new('RGB', (512, 512), (32, 64, 96)).save(image, format='PNG')
    reference = {'filename': 'animation_sdxl_turbo_00001_.png', 'subfolder': '', 'type': 'output'}
    history = {
        prompt_id: {
            'prompt': [0, prompt_id, graph, {}, ['7']],
            'status': {'status_str': 'success', 'completed': True, 'messages': []},
            'outputs': {'7': {'images': [reference]}},
        }
    }
    # This inventory describes the fixture graph, not a discovered server capability.
    inventory = {}
    for node in graph.values():
        required = {}
        for name, value in node['inputs'].items():
            declaration = (
                [value]
                if name in COMBOS
                else OUTPUTS[graph[value[0]]['class_type']][value[1]]
                if isinstance(value, list)
                else {str: 'STRING', int: 'INT', float: 'FLOAT'}[type(value)]
            )
            required[name] = [declaration]
        kind = node['class_type']
        inventory[kind] = {
            'input': {'required': required},
            'output': OUTPUTS[kind],
            'output_node': kind == 'SaveImage',
            'is_input_list': False,
            'output_is_list': [False] * len(OUTPUTS[kind]),
        }
    ledger = root / f'{launch.session_id}.requests.jsonl'
    fd = os.open(ledger, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)

    def handler(request):
        with ledger.open('ab') as stream:
            stream.write(json.dumps([request.method, request.url.path]).encode() + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        path = request.url.path
        if path.startswith('/object_info/'):
            if launch.scenario == 'inventory_hang':
                _hang()
            kind = path.rsplit('/', 1)[1]
            return httpx.Response(200, json={kind: inventory[kind]})
        if path == '/prompt':
            return httpx.Response(200, json={'prompt_id': prompt_id, 'node_errors': {}})
        if path.startswith('/history/'):
            if launch.scenario == 'history_hang':
                _hang()
            if launch.scenario in ('cooperate', 'cancel_hang'):
                cancel.wait()
                return httpx.Response(200, json={})
            return httpx.Response(200, json=history)
        if path.endswith('/cancel'):
            if launch.scenario == 'cancel_hang':
                _hang()
            return httpx.Response(200, json={'cancelled': True})
        if path == '/view':
            return httpx.Response(
                200, headers={'content-type': 'image/png'}, content=image.getvalue()
            )
        raise ValueError('Unexpected fixture request')

    now = time.monotonic()
    admission = OfflineComfyAdmission(
        policy=policy,
        worker_id='fixture-child',
        clock_session_id=launch.session_id,
        max_age_seconds=policy.stale_after_seconds,
        run_started_at=launch.start,
        resource_sample=ComfyResourceSample(
            context=context,
            worker_id='fixture-child',
            device_index=policy.device_index,
            sampled_at=now,
            rss_bytes=0,
            available_ram_bytes=policy.host_reserve_bytes + 1,
            used_vram_bytes=0,
        ),
        observations=tuple(
            ComfyAdmissionObservation(
                capability=capability,
                status='passed',
                context=context,
                worker_id='fixture-child',
                device_index=policy.device_index,
                policy_sha256=admission_policy_sha256(policy),
                source='fixture',
                clock_session_id=launch.session_id,
                checked_at=now,
                evidence_sha256='c' * 64,
            )
            for capability in REQUIRED_CAPABILITIES
        ),
    )
    session = OfflineDurableComfySession(
        ComfyEndpointConfig(origin=context.origin, token=SecretStr('synthetic-child-token')),
        root,
        context,
        transport=httpx.MockTransport(handler),
        admission=admission,
        timeout_seconds=policy.overall_timeout_seconds,
        poll_interval=0.01,
        max_polls=1000,
    )
    if launch.scenario == 'intent_hang':
        original = session._durable.store.create_intent

        def intent():
            original()
            _hang()

        session._durable.store.create_intent = intent
    return session


def main():
    def forbidden(*args, **kwargs):
        raise RuntimeError('Fixture network forbidden')

    socket.socket = socket.getaddrinfo = forbidden
    # Read exactly through the startup delimiter; do not buffer a later stop byte.
    data = bytearray()
    while len(data) <= MAX_IPC_BYTES:
        byte = os.read(0, 1)
        if not byte:
            raise ValueError('Missing fixture startup')
        data.extend(byte)
        if byte == b'\n':
            break
    launch = FixtureLaunch.model_validate(decode_message(bytes(data)))
    cancel = Event()
    watcher_done = Event()
    os.set_blocking(0, False)

    def watch():
        while not watcher_done.wait(0.01):
            try:
                value = os.read(0, 1)
            except BlockingIOError:
                continue
            if value in (b'S', b''):
                cancel.set()
                return
            cancel.set()
            return

    watcher = Thread(target=watch, daemon=True)
    watcher.start()
    outcome, code = 'failed', 'execution_failed'
    try:
        if launch.scenario == 'startup_hang':
            _hang()
        with fixture_session(launch, cancel) as session:
            result = ComfyImageProvider(session, Path(launch.root) / 'fixture-images').generate(
                validate_image_workflow(launch.graph), cancel=cancel
            )
            if result.is_mock:
                outcome, code = 'fixture_verified', None
    except ImageProviderError as error:
        code = error.code
    except Exception:  # noqa: BLE001 — bounded child failure; no raw exception IPC.
        code = 'execution_failed'
    finally:
        watcher_done.set()
        watcher.join(timeout=0.1)
    terminal = FixtureTerminal(
        session_id=launch.session_id, job_id=launch.context.job_id, outcome=outcome, code=code
    )
    sys.stdout.buffer.write(terminal.model_dump_json().encode() + b'\n')
    sys.stdout.buffer.flush()


if __name__ == '__main__':
    main()
