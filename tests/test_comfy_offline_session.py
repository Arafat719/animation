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
        if stage == 'after' and len(server.calls) < 6:
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

    session = make()
    original = session._check_admission

    def check():
        assert not (root / f'{context.job_id}.json').exists()
        with pytest.raises(BlockingIOError), other._durable.store.locked():
            pass
        calls.append(len(server.calls))
        return original()

    session._check_admission = check
    assert session.execute(graph) == server.png
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
    session = make()
    checks = []
    original = session._check_admission

    def check():
        checks.append(True)
        return original()

    session._check_admission = check
    server.override = lambda request: httpx.Response(403)
    with pytest.raises(ImageProviderError):
        session.execute(graph)
    assert checks == [True] and len(server.calls) == 1
    assert not (root / f'{context.job_id}.json').exists()


def test_cancellation_during_final_admission_prevents_intent(setup, graph):
    from threading import Event

    server, make, context, root = setup
    cancel = Event()
    session = make()
    original = session._check_admission

    def check():
        original()
        if len(server.calls) == 6:
            cancel.set()

    session._check_admission = check
    with pytest.raises(ImageProviderError) as caught:
        session.execute(graph, cancel=cancel)
    assert caught.value.code == 'cancelled'
    assert len(server.calls) == 6 and all(r.method == 'GET' for r in server.calls)
    assert not (root / f'{context.job_id}.json').exists()


@pytest.mark.parametrize('stage', ['before', 'after'])
@pytest.mark.parametrize(
    'failure,reason',
    [
        ('missing', 'telemetry_missing'),
        ('stale', 'telemetry_stale'),
        ('future', 'telemetry_invalid'),
        ('prestart', 'telemetry_invalid'),
        ('worker', 'telemetry_invalid'),
        ('device', 'telemetry_invalid'),
        ('context', 'telemetry_invalid'),
        ('ram', 'ram_limit'),
        ('reserve', 'host_reserve'),
        ('vram', 'vram_limit'),
        ('deadline', 'run_deadline'),
        ('start_missing', 'resource_input_invalid'),
        ('start_nan', 'resource_input_invalid'),
        ('start_future', 'resource_input_invalid'),
        ('type', 'resource_input_invalid'),
        ('bytes', 'resource_input_invalid'),
        ('extra', 'resource_input_invalid'),
        ('context_extra', 'resource_input_invalid'),
    ],
)
def test_resource_rejection_before_intent(setup, graph, stage, failure, reason):
    from dataclasses import replace

    server, make, context, root = setup
    session = make()
    snapshot = session._admission
    sample = snapshot.resource_sample
    changes = {
        'stale': {'sampled_at': 98.0},
        'future': {'sampled_at': 102.0},
        'prestart': {'sampled_at': 99.0},
        'worker': {'worker_id': 'other'},
        'device': {'device_index': 1},
        'context': {'context': context.model_copy(update={'model_manifest_sha256': 'd' * 64})},
        'ram': {'rss_bytes': 1024},
        'reserve': {'available_ram_bytes': 512},
        'vram': {'used_vram_bytes': 1024},
        'bytes': {'rss_bytes': True},
        'extra': {'private_extra': 'synthetic-private'},
        'context_extra': {
            'context': context.model_copy(update={'private_extra': 'synthetic-private'})
        },
    }
    updates = {}
    if failure in changes:
        updates['resource_sample'] = sample.model_copy(update=changes[failure])
    if failure == 'stale':
        updates['run_started_at'] = 97.0
    if failure == 'missing':
        updates['resource_sample'] = None
    if failure == 'type':
        updates['resource_sample'] = sample.model_dump()
    if failure == 'deadline':
        updates['run_started_at'] = 51.0
    if failure.startswith('start_'):
        updates['run_started_at'] = {
            'start_missing': None,
            'start_nan': float('nan'),
            'start_future': 102.0,
        }[failure]
    rejected = replace(snapshot, **updates)
    if stage == 'before':
        session._admission = rejected
    else:

        def change_during_inventory(request):
            session._admission = rejected

        server.override = change_during_inventory
    with pytest.raises(ImageProviderError) as caught:
        session.execute(graph)
    assert caught.value.resource_reasons == (reason,)
    assert 'synthetic-private' not in str(caught.value)
    assert not (root / f'{context.job_id}.json').exists()
    assert len(server.calls) == (0 if stage == 'before' else 6)
    assert all(r.method == 'GET' for r in server.calls)


def test_resource_sample_ages_during_preflight_without_refresh(setup, graph):
    from dataclasses import replace

    server, make, context, root = setup
    session = make(clock=lambda: 101.0 if len(server.calls) < 6 else 103.0)
    session._admission = replace(session._admission, max_age_seconds=10.0)
    snapshot = session._admission
    with pytest.raises(ImageProviderError) as caught:
        session.execute(graph)
    assert caught.value.resource_reasons == ('telemetry_stale',)
    assert session._admission is snapshot and snapshot.resource_sample.sampled_at == 100.0
    assert len(server.calls) == 6 and all(r.method == 'GET' for r in server.calls)
    assert not (root / f'{context.job_id}.json').exists()


def test_resource_freshness_and_budget_success_boundaries(setup, graph):
    from dataclasses import replace

    server, make, _, _ = setup
    session = make(clock=lambda: 102.0)
    session._admission = replace(
        session._admission,
        resource_sample=session._admission.resource_sample.model_copy(
            update={
                'rss_bytes': 1023,
                'available_ram_bytes': 513,
                'used_vram_bytes': 1023,
            }
        ),
    )
    assert session.execute(graph) == server.png
    assert session.is_mock
    assert sum(r.url.path == '/prompt' for r in server.calls) == 1


def test_resource_multiple_breaches_have_stable_reasons(setup, graph):
    from dataclasses import replace

    server, make, _, _ = setup
    session = make()
    session._admission = replace(
        session._admission,
        run_started_at=51.0,
        resource_sample=session._admission.resource_sample.model_copy(
            update={
                'sampled_at': 98.0,
                'rss_bytes': 1024,
                'available_ram_bytes': 512,
                'used_vram_bytes': 1024,
            }
        ),
    )
    with pytest.raises(ImageProviderError) as caught:
        session.execute(graph)
    assert caught.value.resource_reasons == (
        'telemetry_stale',
        'ram_limit',
        'host_reserve',
        'vram_limit',
        'run_deadline',
    )
    assert not server.calls


def timed_session(setup, **options):
    """One mutable fixture clock across admission, HTTP and transport."""
    from dataclasses import replace

    _, make, _, _ = setup
    now = [101.0]
    session = make(clock=lambda: now[0], **options)
    snapshot = session._admission
    policy = snapshot.policy.model_copy(
        update={
            'overall_timeout_seconds': 10.0,
            'cleanup_reserve_seconds': 2.0,
            'reap_allowance_seconds': 2.0,
            'stale_after_seconds': 100.0,
        }
    )
    session._admission = replace(
        snapshot,
        policy=policy,
        max_age_seconds=100.0,
        observations=tuple(
            o.model_copy(
                update={
                    'policy_sha256': admission_policy_sha256(policy),
                }
            )
            for o in snapshot.observations
        ),
    )
    return session, now


def test_shared_deadline_decreases_across_inventory_submit_history_view(setup, graph):
    server, _, _, _ = setup
    session, now = timed_session(setup, timeout_seconds=3)
    budgets = []

    def consume(request):
        budgets.append(request.extensions['timeout']['read'])
        now[0] += 0.1

    server.override = consume
    assert session.execute(graph) == server.png
    assert len(budgets) == 9
    assert budgets == pytest.approx([3 - i * 0.1 for i in range(9)])
    assert [r.url.path for r in server.calls[-3:]] == [
        '/prompt',
        f'/history/{PROMPT_ID}',
        '/view',
    ]
    assert session._run_budget is None and session._http._run_budget is None


@pytest.mark.parametrize('stage', ['initial', 'inventory', 'pre_intent', 'post_intent'])
def test_shared_deadline_expiry_journal_boundary(setup, graph, stage):
    server, _, context, root = setup
    session, now = timed_session(setup)
    if stage == 'initial':
        now[0] = 106.0
    elif stage == 'inventory':

        def consume(request):
            now[0] = 106.0

        server.override = consume
    elif stage == 'pre_intent':
        original = session._check_admission

        def expire_after_recheck():
            original()
            if len(server.calls) == 6:
                now[0] = 106.0

        session._check_admission = expire_after_recheck
    else:
        original = session._durable.store.create_intent

        def expire_after_write():
            original()
            now[0] = 106.0

        session._durable.store.create_intent = expire_after_write
    with pytest.raises(ImageProviderError):
        session.execute(graph)
    assert all(r.method == 'GET' for r in server.calls)
    journal = root / f'{context.job_id}.json'
    assert journal.exists() == (stage == 'post_intent')
    if journal.exists():
        assert json.loads(journal.read_bytes())['state'] == 'intent'
        server.calls.clear()
        with pytest.raises(ImageProviderError, match='Journal exists'):
            session.execute(graph)
        with pytest.raises(ImageProviderError, match='outcome unknown'):
            session.recover(graph)
        assert not server.calls


@pytest.mark.parametrize('expired_at,allowance', [(106.0, 2.0), (107.0, 1.0), (108.0, 0)])
def test_cleanup_uses_original_ceiling_and_recovery_stays_get_only(
    setup, graph, expired_at, allowance
):
    server, make, context, root = setup
    session, now = timed_session(setup)

    def expire_on_history(request):
        if request.url.path.startswith('/history/'):
            now[0] = expired_at

    server.override = expire_on_history
    with pytest.raises(ComfyExecutionError) as caught:
        session.execute(graph)
    assert caught.value.code == 'timeout'
    cancels = [r for r in server.calls if r.url.path.endswith('/cancel')]
    assert len(cancels) == (1 if allowance else 0)
    if cancels:
        assert cancels[0].extensions['timeout']['read'] == allowance
    else:
        assert caught.value.cancellation.dispatched is None
    sidecar = root / f'{context.job_id}.supervision.json'
    saved = sidecar.read_bytes()
    assert json.loads(saved)['attempt_count'] == 1
    assert json.loads((root / f'{context.job_id}.json').read_bytes())['state'] == 'accepted'
    server.calls.clear()
    server.override = None
    # Same session restores host-clock GET-only recovery, without stale admission.
    assert session.recover(graph) == server.png
    assert make(admission=None).recover(graph) == server.png
    assert all(r.method == 'GET' for r in server.calls)
    assert sidecar.read_bytes() == saved


@pytest.mark.parametrize('change', ['start', 'policy', 'clock_session'])
def test_recheck_cannot_replace_attempt_budget(setup, graph, change):
    from dataclasses import replace

    server, _, context, root = setup
    session, _ = timed_session(setup)
    snapshot = session._admission
    if change == 'start':
        replacement = replace(
            snapshot,
            run_started_at=100.5,
            resource_sample=snapshot.resource_sample.model_copy(update={'sampled_at': 100.5}),
        )
    elif change == 'policy':
        policy = snapshot.policy.model_copy(update={'overall_timeout_seconds': 20.0})
        replacement = replace(
            snapshot,
            policy=policy,
            observations=tuple(
                o.model_copy(update={'policy_sha256': admission_policy_sha256(policy)})
                for o in snapshot.observations
            ),
        )
    else:
        clock_id = '22345678-1234-4234-8234-123456789abc'
        replacement = replace(
            snapshot,
            clock_session_id=clock_id,
            observations=tuple(
                o.model_copy(update={'clock_session_id': clock_id}) for o in snapshot.observations
            ),
        )

    def swap(request):
        session._admission = replacement

    server.override = swap
    with pytest.raises(ImageProviderError, match='budget changed'):
        session.execute(graph)
    assert len(server.calls) == 6 and all(r.method == 'GET' for r in server.calls)
    assert not (root / f'{context.job_id}.json').exists()


@pytest.mark.parametrize('value', [float('nan'), float('inf'), True, 100.0])
def test_http_clock_corruption_closes_response_without_intent(setup, graph, value):
    server, _, context, root = setup
    session, now = timed_session(setup)

    def corrupt(request):
        now[0] = value

    server.override = corrupt
    with pytest.raises(ImageProviderError, match='clock invalid'):
        session.execute(graph)
    assert len(server.calls) == 1 and server.calls[0].method == 'GET'
    assert not (root / f'{context.job_id}.json').exists()
    assert session._http._run_budget is None


def test_poll_wait_is_clamped_to_original_run_deadline(setup, graph, monkeypatch):
    server, _, _, _ = setup
    session, now = timed_session(setup, poll_interval=2)
    session._http.max_polls = 2
    server.pending = 1
    waits = []

    class Wait:
        def wait(self, seconds):
            waits.append(seconds)
            now[0] += seconds

    monkeypatch.setattr('animation_studio.providers.comfy_http.Event', Wait)

    def consume(request):
        if request.url.path == '/prompt':
            now[0] = 105.5

    server.override = consume
    with pytest.raises(ComfyExecutionError) as caught:
        session.execute(graph)
    assert caught.value.code == 'timeout' and waits == [0.5]
    assert sum(r.url.path.startswith('/history/') for r in server.calls) == 1
    assert sum(r.url.path.endswith('/cancel') for r in server.calls) == 1


def test_stream_chunks_cannot_outlive_shared_deadline(setup, graph):
    server, _, context, root = setup
    session, now = timed_session(setup)
    closed = []

    class SlowStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b'{'
            now[0] = 106.0
            yield b'}'

        def close(self):
            closed.append(True)

    server.override = lambda request: httpx.Response(
        200, headers={'Content-Type': 'application/json'}, stream=SlowStream()
    )
    with pytest.raises(ImageProviderError) as caught:
        session.execute(graph)
    assert caught.value.code == 'timeout' and closed
    assert not session._transport._pending_streams
    assert len(server.calls) == 1 and not (root / f'{context.job_id}.json').exists()


def test_throwing_clock_is_sanitized_during_http_and_attempt_is_released(setup, graph):
    server, _, context, root = setup
    session, _ = timed_session(setup)

    def clock():
        if server.calls:
            raise RuntimeError('synthetic-private-clock')
        return 101.0

    session._clock = clock
    with pytest.raises(ImageProviderError) as caught:
        session.execute(graph)
    assert 'synthetic-private' not in str(caught.value)
    assert session._run_budget is None and session._http._run_budget is None
    assert not session._transport._pending_streams
    assert not (root / f'{context.job_id}.json').exists()
