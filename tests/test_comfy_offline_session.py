import json
import socket

import httpx
import pytest
from pydantic import SecretStr
from test_comfy_http import PROMPT_ID, Server
from test_comfy_http import graph as graph_fixture

from animation_studio.providers.comfy_admission import (
    REQUIRED_CAPABILITIES,
    ComfyAdmissionObservation,
    admission_policy_sha256,
)
from animation_studio.providers.comfy_config import ComfyEndpointConfig
from animation_studio.providers.comfy_http import ComfyExecutionError
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_image import ComfyImageProvider
from animation_studio.providers.comfy_journal import _fingerprint
from animation_studio.providers.comfy_offline_session import (
    OfflineComfyAdmission,
    OfflineDurableComfySession,
)
from animation_studio.providers.comfy_resource_guard import ComfyResourceSample
from animation_studio.providers.comfy_supervision import ComfySupervisionPolicy
from animation_studio.providers.comfy_workflow import validate_image_workflow
from animation_studio.providers.image import ImageProviderError

graph = graph_fixture


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Offline composition must not open sockets or resolve DNS')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


@pytest.fixture
def setup(tmp_path, graph):
    tmp_path.chmod(0o700)
    config = ComfyEndpointConfig(
        origin='https://selected.invalid', token=SecretStr('synthetic-token')
    )
    context = ComfyExecutionContext(
        mode='mock',
        job_id=PROMPT_ID,
        graph_sha256=_fingerprint(graph),
        origin=config.origin,
        deployment_id=PROMPT_ID,
        runtime_manifest_sha256='a' * 64,
        model_manifest_sha256='b' * 64,
    )
    policy = ComfySupervisionPolicy(
        ram_limit_bytes=1024,
        host_reserve_bytes=512,
        device_index=0,
        vram_limit_bytes=1024,
        sample_interval_seconds=1.0,
        stale_after_seconds=2.0,
        overall_timeout_seconds=60.0,
        cleanup_reserve_seconds=5.0,
        reap_allowance_seconds=5.0,
    )
    admission = OfflineComfyAdmission(
        policy=policy,
        worker_id='worker-1',
        clock_session_id=PROMPT_ID,
        max_age_seconds=2.0,
        run_started_at=100.0,
        resource_sample=ComfyResourceSample(
            context=context,
            worker_id='worker-1',
            device_index=0,
            sampled_at=100.0,
            rss_bytes=100,
            available_ram_bytes=1024,
            used_vram_bytes=100,
        ),
        observations=tuple(
            ComfyAdmissionObservation(
                capability=capability,
                status='passed',
                context=context,
                worker_id='worker-1',
                device_index=0,
                policy_sha256=admission_policy_sha256(policy),
                source='fixture',
                clock_session_id=PROMPT_ID,
                checked_at=100.0,
                evidence_sha256='c' * 64,
            )
            for capability in REQUIRED_CAPABILITIES
        ),
    )
    server = Server(graph)
    sessions = []

    def make(**options):
        session = OfflineDurableComfySession(
            config,
            tmp_path,
            options.pop('context', context),
            transport=options.pop('transport', httpx.MockTransport(server)),
            max_polls=1,
            admission=options.pop('admission', admission),
            clock=options.pop('clock', lambda: 101.0),
            **options,
        )
        sessions.append(session)
        return session

    yield server, make, context, tmp_path
    for session in sessions:
        session.close()


def test_order_provenance_and_restart_get_only(setup, graph):
    server, make, context, root = setup
    session = make()
    journal = root / f'{context.job_id}.json'
    assert not list(root.iterdir()) and not server.calls

    def inspect(request):
        if request.url.path.startswith('/object_info/'):
            assert not journal.exists()
        else:
            assert json.loads(journal.read_bytes())['state'] == (
                'intent' if request.url.path == '/prompt' else 'accepted'
            )

    server.override = inspect
    result = ComfyImageProvider(session, root / 'images').generate(validate_image_workflow(graph))
    assert result.is_mock and result.path.read_bytes() == server.png
    with pytest.raises(AttributeError):
        session.is_mock = False
    saved = journal.read_bytes()
    session.close()
    server.calls.clear()
    with make() as restarted:
        with pytest.raises(ImageProviderError):
            restarted.execute(graph)
        assert restarted.recover(graph) == server.png
    assert [r.url.path for r in server.calls] == [f'/history/{PROMPT_ID}', '/view']
    assert all(r.method == 'GET' for r in server.calls)
    assert journal.read_bytes() == saved


@pytest.mark.parametrize('failure', ['preflight', 'lost_receipt', 'bad_receipt', 'receipt_write'])
def test_failure_boundaries_no_resubmit(setup, graph, monkeypatch, failure):
    server, make, context, root = setup
    session = make()

    def respond(request):
        if failure == 'preflight':
            return httpx.Response(403)
        if request.url.path == '/prompt':
            if failure == 'lost_receipt':
                raise httpx.ReadError('synthetic-private')
            if failure == 'bad_receipt':
                return httpx.Response(200, json={'prompt_id': 'bad'})

    server.override = respond
    if failure == 'receipt_write':

        def fail(*args):
            raise OSError('synthetic-private')

        monkeypatch.setattr(session._durable.store, 'accept', fail)
    with pytest.raises(ImageProviderError) as caught:
        session.execute(graph)
    assert 'synthetic-private' not in str(caught.value)
    journal = root / f'{context.job_id}.json'
    assert journal.exists() == (failure != 'preflight')
    if failure != 'preflight':
        assert json.loads(journal.read_bytes())['state'] == 'intent'
        server.calls.clear()
        restarted = make()
        for operation in (restarted.execute, restarted.recover):
            with pytest.raises(ImageProviderError):
                operation(graph)
        assert not server.calls
    else:
        assert not any(r.method == 'POST' for r in server.calls)


@pytest.mark.parametrize('ack', [True, False, None])
def test_cancel_durable_and_recovery_never_repeats_cleanup(setup, graph, ack):
    server, make, context, root = setup
    session = make()
    server.pending = 1
    sidecar = root / f'{context.job_id}.supervision.json'

    def inspect(request):
        if request.url.path.endswith('/cancel'):
            assert json.loads(sidecar.read_bytes())['cleanup_phase'] == 'intent'
            return (
                httpx.Response(403) if ack is None else httpx.Response(200, json={'cancelled': ack})
            )

    server.override = inspect
    with pytest.raises(ComfyExecutionError) as caught:
        session.execute(graph)
    assert caught.value.code == 'timeout' and caught.value.cancellation.dispatched is ack
    assert sum(r.url.path.endswith('/cancel') for r in server.calls) == 1
    data = json.loads(sidecar.read_bytes())
    assert data['source'] == ('none' if ack is None else 'mock')
    assert data['compute_status'] == 'unknown'
    saved = sidecar.read_bytes()
    server.calls.clear()
    assert make().recover(graph) == server.png
    assert all(r.method == 'GET' for r in server.calls)
    assert sidecar.read_bytes() == saved


@pytest.mark.parametrize('kind', ['live', 'origin', 'invalid', 'transport'])
def test_invalid_admission_no_files_or_dispatch(setup, kind):
    server, make, context, root = setup
    options = {}
    if kind == 'transport':
        options['transport'] = object()
    else:
        updates = {
            'live': {'mode': 'live'},
            'origin': {'origin': 'https://other.invalid:443/'},
            'invalid': {'job_id': 'bad'},
        }
        options['context'] = context.model_copy(update=updates[kind])
    with pytest.raises((ValueError, TypeError)):
        make(**options)
    assert not server.calls and not list(root.iterdir())


def test_closed_and_changed_provenance_fail_before_intent(setup, graph):
    server, make, _, root = setup
    session = make()
    session._transport._is_mock = False
    with pytest.raises(TypeError):
        session.execute(graph)
    session.close()
    session.close()
    for operation in (session.execute, session.recover):
        with pytest.raises(ImageProviderError):
            operation(graph)
    assert not server.calls and not list(root.iterdir())


def test_construction_failure_closes_owned_transport(setup):
    _, make, _, root = setup
    transport = httpx.MockTransport(lambda r: None)
    closed = []
    transport.close = lambda: closed.append(True)
    with pytest.raises(ValueError):
        make(transport=transport, timeout_seconds=0)
    assert closed == [True] and not list(root.iterdir())


def test_context_manager_retains_primary_and_cleanup_handle(setup):
    _, make, _, _ = setup
    transport = httpx.MockTransport(lambda r: None)

    def broken():
        raise OSError('synthetic-private')

    transport.close = broken
    session = make(transport=transport)
    primary = RuntimeError('primary')
    with pytest.raises(RuntimeError) as caught, session:
        raise primary
    assert caught.value is primary and primary.cleanup_handle is session._transport
    transport.close = lambda: None
    primary.cleanup_handle.close()


def test_constructor_failure_retains_failed_cleanup_resource(setup):
    _, make, _, root = setup
    transport = httpx.MockTransport(lambda r: None)

    def broken():
        raise OSError('synthetic-private')

    transport.close = broken
    with pytest.raises(ValueError) as caught:
        make(transport=transport, timeout_seconds=0)
    assert 'synthetic-private' not in str(caught.value)
    transport.close = lambda: None
    caught.value.cleanup_handle.close()
    assert not list(root.iterdir())


def test_clean_context_exit_reports_cleanup_failure(setup):
    _, make, _, _ = setup
    transport = httpx.MockTransport(lambda r: None)

    def broken():
        raise OSError('synthetic-private')

    transport.close = broken
    session = make(transport=transport)
    with pytest.raises(ImageProviderError) as caught, session:
        pass
    assert caught.value.cleanup_handle is session._transport
    assert 'synthetic-private' not in str(caught.value)
    transport.close = lambda: None
    session.close()


@pytest.mark.parametrize(
    'field,value', [('mode', 'live'), ('deployment_id', '22345678-1234-4234-8234-123456789abc')]
)
def test_restart_mismatched_record_blocks_network(setup, graph, field, value):
    server, make, context, root = setup
    make().execute(graph)
    path = root / f'{context.job_id}.json'
    record = json.loads(path.read_bytes())
    record[field] = value
    path.write_text(json.dumps(record))
    saved = path.read_bytes()
    server.calls.clear()
    with pytest.raises(ImageProviderError):
        make().recover(graph)
    assert not server.calls and path.read_bytes() == saved


@pytest.mark.parametrize('snapshot', [None, object()])
def test_missing_admission_zero_dispatch_and_no_intent(setup, graph, snapshot):
    server, make, context, root = setup
    with pytest.raises(ImageProviderError, match='snapshot required'):
        make(admission=snapshot).execute(graph)
    assert not server.calls and not (root / f'{context.job_id}.json').exists()


@pytest.mark.parametrize('stage', ['before', 'after'])
@pytest.mark.parametrize('failure', ['stale', 'future', 'nan', 'clock_error', 'reversed'])
def test_admission_time_failure_before_intent(setup, graph, stage, failure):
    server, make, context, root = setup
    count = 0

    def clock():
        nonlocal count
        count += 1
        if stage == 'after' and count == 1:
            return 101.0
        if failure == 'clock_error':
            raise RuntimeError('synthetic-private-clock')
        return {'stale': 103.0, 'future': 99.0, 'nan': float('nan'), 'reversed': 100.5}[failure]

    session = make(clock=clock)
    if failure == 'reversed' and stage == 'before':
        session._last_admission_time = 101.0
    with pytest.raises(ImageProviderError) as caught:
        session.execute(graph)
    assert 'synthetic-private' not in str(caught.value)
    assert not (root / f'{context.job_id}.json').exists()
    assert not any(r.method == 'POST' for r in server.calls)
    assert len(server.calls) == (0 if stage == 'before' else 6)


@pytest.mark.parametrize('change', ['source', 'policy', 'context', 'missing', 'clock_session'])
def test_snapshot_rechecked_after_preflight(setup, graph, change):
    from dataclasses import replace

    server, make, context, root = setup
    session = make()
    snapshot = session._admission
    first, *rest = snapshot.observations
    changes = {
        'source': {'observations': (first.model_copy(update={'source': 'target'}), *rest)},
        'policy': {'policy': snapshot.policy.model_copy(update={'ram_limit_bytes': 2048})},
        'context': {
            'observations': (
                first.model_copy(
                    update={
                        'context': context.model_copy(
                            update={'deployment_id': '22345678-1234-4234-8234-123456789abc'}
                        )
                    }
                ),
                *rest,
            )
        },
        'missing': {'observations': ()},
        'clock_session': {'clock_session_id': '22345678-1234-4234-8234-123456789abc'},
    }

    def change_during_inventory(request):
        session._admission = replace(snapshot, **changes[change])

    server.override = change_during_inventory
    with pytest.raises(ImageProviderError, match='admission rejected') as caught:
        session.execute(graph)
    assert caught.value.admission_reasons
    assert len(server.calls) == 6 and all(r.method == 'GET' for r in server.calls)
    assert not (root / f'{context.job_id}.json').exists()


def test_both_admission_checks_hold_generation_lock_and_precede_intent(setup, graph):
    server, make, context, root = setup
    other = make()
    calls = []

    def clock():
        assert not (root / f'{context.job_id}.json').exists()
        with pytest.raises(BlockingIOError), other._durable.store.locked():
            pass
        calls.append(len(server.calls))
        return 101.0

    assert make(clock=clock).execute(graph) == server.png
    assert calls == [0, 6]


def test_recovery_ignores_admission_and_clock_and_does_not_submit(setup, graph):
    server, make, context, root = setup
    make().execute(graph)
    saved = (root / f'{context.job_id}.json').read_bytes()
    server.calls.clear()

    def forbidden():
        pytest.fail('Recovery must not invoke admission clock')

    recovered = make(admission=None, clock=forbidden)
    assert recovered.recover(graph) == server.png
    assert all(r.method == 'GET' for r in server.calls)
    assert (root / f'{context.job_id}.json').read_bytes() == saved
    server.calls.clear()
    with pytest.raises(ImageProviderError, match='Journal exists'):
        recovered.execute(graph)
    assert not server.calls


def test_invalid_clock_rejected_before_transport_ownership(setup):
    server, make, _, root = setup
    with pytest.raises(TypeError, match='admission clock'):
        make(clock=None)
    assert not server.calls and not list(root.iterdir())


def test_failed_preflight_does_not_refresh_or_recheck_admission(setup, graph):
    server, make, context, root = setup
    ticks = []

    def clock():
        ticks.append(101.0)
        return 101.0

    server.override = lambda request: httpx.Response(403)
    with pytest.raises(ImageProviderError):
        make(clock=clock).execute(graph)
    assert ticks == [101.0] and len(server.calls) == 1
    assert not (root / f'{context.job_id}.json').exists()


def test_cancellation_during_final_admission_prevents_intent(setup, graph):
    from threading import Event

    server, make, context, root = setup
    cancel = Event()
    count = 0

    def clock():
        nonlocal count
        count += 1
        if count == 2:
            cancel.set()
        return 101.0

    with pytest.raises(ImageProviderError) as caught:
        make(clock=clock).execute(graph, cancel=cancel)
    assert caught.value.code == 'cancelled'
    assert len(server.calls) == 6 and all(r.method == 'GET' for r in server.calls)
    assert not (root / f'{context.job_id}.json').exists()
