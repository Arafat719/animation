import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path
from threading import Event

import httpx
import pytest
from PIL import Image
from pydantic import ValidationError
from test_comfy_http import Server

from animation_studio.providers.comfy_durable_image import DurableComfyImageProvider
from animation_studio.providers.comfy_http import ComfyHTTPExecutor
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_journal import DurableComfyExecutor, _fingerprint
from animation_studio.providers.comfy_v2_executor import DurableComfyExecutorV2
from animation_studio.providers.comfy_workflow import (
    MODEL_NAME,
    MODEL_VERSION,
    build_image_workflow,
)
from animation_studio.providers.image import ImageProviderError, ImageRequest, ImageResult


@pytest.fixture(params=['v1', 'v2'])
def setup(tmp_path, request):
    version = request.param
    request = ImageRequest(
        prompt='নদীর পাশে বাড়ি', model_name=MODEL_NAME, model_version=MODEL_VERSION, seed=42
    )
    server = Server(build_image_workflow(request))
    client = ComfyHTTPExecutor(transport=httpx.MockTransport(server), max_polls=1)
    if version == 'v1':
        executor = DurableComfyExecutor(client, tmp_path / 'job.json')
    else:
        tmp_path.chmod(0o700)
        context = ComfyExecutionContext(
            mode='mock',
            job_id='12345678-1234-4234-8234-123456789abc',
            graph_sha256=_fingerprint(build_image_workflow(request)),
            origin='https://comfy.invalid:443/',
            deployment_id='12345678-1234-4234-8234-123456789abc',
            runtime_manifest_sha256='a' * 64,
            model_manifest_sha256='b' * 64,
        )
        executor = DurableComfyExecutorV2(client, tmp_path, context)
    provider = DurableComfyImageProvider(executor, tmp_path / 'output')
    yield server, executor, provider, request
    client.close()


def journal_path(executor):
    return executor.store.path if type(executor) is DurableComfyExecutorV2 else executor.path


def verify(result, request, content):
    assert result.is_mock and result.provider_name == 'comfy-image'
    assert (result.model_name, result.model_version, result.seed) == (
        request.model_name,
        request.model_version,
        request.seed,
    )
    assert result.path.is_absolute() and result.path.read_bytes() == content
    assert result.sha256 == hashlib.sha256(content).hexdigest()
    with Image.open(result.path) as image:
        image.load()
        assert image.format == 'PNG' and image.size == (512, 512)
    assert (result.width, result.height) == (512, 512)
    assert ImageResult.model_validate_json(result.model_dump_json()) == result


def test_verified_generate_and_recovery(setup, monkeypatch):
    import socket

    server, executor, provider, request = setup

    def forbidden(*args, **kwargs):
        raise AssertionError('No real network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    first = provider.generate(request)
    verify(first, request, server.png)
    journal = journal_path(executor).read_bytes()
    server.calls.clear()
    restarted = DurableComfyImageProvider(executor, first.path.parent)
    recovered = restarted.recover(request)
    verify(recovered, request, server.png)
    assert first.path != recovered.path and first.path.read_bytes() == server.png
    assert journal_path(executor).read_bytes() == journal
    assert all(r.method == 'GET' for r in server.calls)
    count = len(server.calls)
    with pytest.raises(ImageProviderError, match='Journal exists'):
        restarted.generate(request)
    assert len(server.calls) == count


@pytest.mark.parametrize('kind', ['corrupt', 'jpeg', 'wrong_size', 'truncated'])
def test_bad_recovered_media_not_saved(setup, kind):
    server, executor, provider, request = setup
    first = provider.generate(request)
    original = first.path.read_bytes()
    if kind == 'corrupt':
        server.png = b'not png'
    elif kind == 'truncated':
        server.png = server.png[: len(server.png) // 2]
    else:
        stream = io.BytesIO()
        Image.new('RGB', (4, 4) if kind == 'wrong_size' else (512, 512)).save(
            stream, format='JPEG' if kind == 'jpeg' else 'PNG'
        )
        server.png = stream.getvalue()
    before = journal_path(executor).read_bytes()
    server.calls.clear()
    with pytest.raises(ImageProviderError) as caught:
        provider.recover(request)
    assert caught.value.code == 'invalid_image'
    assert list(first.path.parent.iterdir()) == [first.path]
    assert first.path.read_bytes() == original and journal_path(executor).read_bytes() == before
    assert all(r.method == 'GET' for r in server.calls)


def test_save_failure_recovery_without_resubmit(setup, tmp_path):
    server, executor, _, request = setup
    bad_output = tmp_path / 'file'
    bad_output.write_text('keep')
    with pytest.raises(ImageProviderError) as caught:
        DurableComfyImageProvider(executor, bad_output).generate(request)
    assert caught.value.code == 'io_error'
    assert json.loads(journal_path(executor).read_text())['state'] == 'accepted'
    recovered = DurableComfyImageProvider(executor, tmp_path / 'recovered').recover(request)
    verify(recovered, request, server.png)
    assert sum(r.url.path == '/prompt' for r in server.calls) == 1
    assert bad_output.read_text() == 'keep'


@pytest.mark.parametrize('stage', ['before', 'download', 'decode', 'save'])
def test_recovery_cancellation_preserves_prior_files(setup, monkeypatch, stage):
    server, executor, provider, request = setup
    first = provider.generate(request)
    journal = journal_path(executor).read_bytes()
    server.calls.clear()
    cancel = Event()
    if stage == 'before':
        cancel.set()
    elif stage == 'download':

        def hook(r):
            if r.url.path == '/view':
                cancel.set()

        server.override = hook
    elif stage == 'decode':
        original = Image.Image.load

        def load(image, *args, **kwargs):
            cancel.set()
            return original(image, *args, **kwargs)

        monkeypatch.setattr(Image.Image, 'load', load)
    else:
        original = provider._recovery._check_cancel

        def check(event):
            if len(list(first.path.parent.iterdir())) > 1:
                cancel.set()
            original(event)

        monkeypatch.setattr(provider._recovery, '_check_cancel', check)
    with pytest.raises(ImageProviderError) as caught:
        provider.recover(request, cancel=cancel)
    assert caught.value.code == 'cancelled'
    assert list(first.path.parent.iterdir()) == [first.path]
    assert first.path.read_bytes() == server.png and journal_path(executor).read_bytes() == journal
    assert all(r.method == 'GET' for r in server.calls)


@pytest.mark.parametrize('change', [{'seed': 43}, {'prompt': 'different'}])
def test_recovery_mismatch_does_no_http(setup, change):
    server, _, provider, request = setup
    provider.generate(request)
    server.calls.clear()
    with pytest.raises(ImageProviderError, match='mismatch'):
        provider.recover(request.model_copy(update=change))
    assert not server.calls


def test_recovery_revalidates_request(setup):
    server, _, provider, request = setup
    with pytest.raises(ValidationError):
        provider.recover(request.model_copy(update={'seed': True}))
    assert not server.calls


@pytest.mark.parametrize('version', ['v1', 'v2'])
def test_fresh_process_verified_result(tmp_path, version):
    tmp_path.chmod(0o700)
    script = """
import json, os, sys, socket
from pathlib import Path
sys.path.insert(0, 'tests')
import httpx
from test_comfy_http import Server
from animation_studio.providers.comfy_durable_image import DurableComfyImageProvider
from animation_studio.providers.comfy_http import ComfyHTTPExecutor
from animation_studio.providers.comfy_journal import DurableComfyExecutor, _fingerprint
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_v2_executor import DurableComfyExecutorV2
from animation_studio.providers.comfy_workflow import MODEL_NAME, MODEL_VERSION, build_image_workflow
from animation_studio.providers.image import ImageRequest
root = Path(sys.argv[1])
request = ImageRequest(prompt='A house', model_name=MODEL_NAME, model_version=MODEL_VERSION, seed=42)
server = Server(build_image_workflow(request))
def forbidden(*args, **kwargs):
    raise AssertionError('No real network')
socket.socket = forbidden
def handler(req):
    with (root / 'calls').open('a') as stream:
        stream.write(req.method + ' ' + req.url.path + '\\n')
    if sys.argv[2] == 'crash' and req.url.path == '/view':
        os._exit(7)
    return server(req)
client = ComfyHTTPExecutor(transport=httpx.MockTransport(handler))
if sys.argv[3] == 'v1':
    executor = DurableComfyExecutor(client, root / 'job.json')
else:
    context = ComfyExecutionContext(
        mode='mock', job_id='12345678-1234-4234-8234-123456789abc',
        graph_sha256=_fingerprint(build_image_workflow(request)),
        origin='https://comfy.invalid:443/', deployment_id='12345678-1234-4234-8234-123456789abc',
        runtime_manifest_sha256='a' * 64, model_manifest_sha256='b' * 64,
    )
    executor = DurableComfyExecutorV2(client, root, context)
provider = DurableComfyImageProvider(executor, root / 'output')
result = provider.generate(request) if sys.argv[2] == 'crash' else provider.recover(request)
(root / 'result.json').write_text(result.model_dump_json())
client.close()
"""
    for mode, code in [('crash', 7), ('recover', 0)]:
        child = subprocess.run(
            [sys.executable, '-c', script, str(tmp_path), mode, version],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            timeout=15,
            check=False,
        )
        assert child.returncode == code, child.stderr.decode()
    result = ImageResult.model_validate_json((tmp_path / 'result.json').read_text())
    request = ImageRequest(
        prompt='A house', model_name=MODEL_NAME, model_version=MODEL_VERSION, seed=42
    )
    verify(result, request, Server(build_image_workflow(request)).png)
    calls = (tmp_path / 'calls').read_text().splitlines()
    assert calls.count('POST /prompt') == 1
    submitted = calls.index('POST /prompt')
    assert submitted == 6
    assert all(line.startswith('GET ') for line in calls[submitted + 1 :])
