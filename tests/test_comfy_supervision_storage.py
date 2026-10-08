import os
import stat
from concurrent.futures import ThreadPoolExecutor

import pytest

from animation_studio.providers import comfy_supervision_storage as module
from animation_studio.providers.comfy_identity import ComfyExecutionContext
from animation_studio.providers.comfy_storage import ComfyJournalStore, LiveComfyJournalStore
from animation_studio.providers.comfy_supervision import (
    ComfySupervisionObservation,
    LiveComfySupervisionObservation,
)
from animation_studio.providers.comfy_supervision_storage import (
    ComfySupervisionStore,
    LiveComfySupervisionStore,
)


@pytest.fixture(params=['mock', 'live'])
def context(request):
    return ComfyExecutionContext(
        mode=request.param,
        job_id='12345678-1234-4234-8234-123456789abc',
        graph_sha256='a' * 64,
        origin='https://selected.invalid:443/',
        deployment_id='12345678-1234-4234-8234-123456789abc',
        runtime_manifest_sha256='b' * 64,
        model_manifest_sha256='c' * 64,
    )


@pytest.fixture
def record(context):
    return {
        'schema_version': 1 if context.mode == 'mock' else 2,
        'context': context,
        'primary_outcome': 'unknown',
        'cleanup_phase': 'not_requested',
        'attempt_count': 0,
        'created_at': 100,
        'updated_at': 100,
        'source': 'none',
    }


@pytest.fixture
def setup(tmp_path, context, record):
    tmp_path.chmod(0o700)
    if context.mode == 'mock':
        journal = ComfyJournalStore(tmp_path, context)
        return journal, ComfySupervisionStore(journal), ComfySupervisionObservation(**record)
    journal = LiveComfyJournalStore(tmp_path, context)
    return journal, LiveComfySupervisionStore(journal), LiveComfySupervisionObservation(**record)


@pytest.mark.parametrize('legacy', [False, True])
def test_absent_roundtrip_restart_preserves_generation(setup, context, legacy):
    journal, sidecar, observation = setup
    with journal.locked():
        if legacy:
            journal.path.write_bytes(
                b'{"schema_version":1,"mode":"mock","state":"intent","graph_sha256":"'
                + b'a' * 64
                + b'"}'
            )
        else:
            journal.create_intent()
            journal.accept(context.job_id)
        saved = journal.path.read_bytes()
        assert sidecar.read() is None
        assert sidecar.create(observation) == observation
        assert sidecar.read() == observation
        assert journal.path.read_bytes() == saved
    restarted = type(journal)(journal.path.parent, context)
    with restarted.locked():
        other = type(sidecar)(restarted)
        assert other.read() == observation
        with pytest.raises(ValueError):
            other.create(observation)
    assert stat.S_IMODE(sidecar.path.stat().st_mode) == 0o600
    assert sidecar.path.name == f'{context.job_id}.supervision.json'
    assert len(list(journal.path.parent.glob('*.lock'))) == 1


def test_shared_lock_thread_and_competing_instance(setup, context):
    journal, sidecar, observation = setup
    with pytest.raises(RuntimeError):
        sidecar.read()
    with pytest.raises(RuntimeError):
        sidecar.create(observation)
    other = type(journal)(journal.path.parent, context)
    with journal.locked(), ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(BlockingIOError), other.locked():
            pass
        with pytest.raises(RuntimeError):
            pool.submit(sidecar.create, observation).result(timeout=5)
        assert sidecar.read() is None


@pytest.mark.parametrize('kind', ['corrupt', 'oversize', 'symlink', 'dangling', 'fifo', 'mismatch'])
def test_existing_invalid_never_missing_or_overwritten(setup, kind):
    journal, sidecar, observation = setup
    target = sidecar.path.parent / 'untouched'
    target.write_bytes(b'original')
    if kind == 'symlink':
        sidecar.path.symlink_to(target)
    elif kind == 'dangling':
        sidecar.path.symlink_to(target.parent / 'missing')
    elif kind == 'fifo':
        os.mkfifo(sidecar.path)
    elif kind == 'mismatch':
        content = observation.model_dump_json().replace('selected.invalid', 'different.invalid')
        sidecar.path.write_text(content)
    else:
        sidecar.path.write_bytes(b'x' * (4097 if kind == 'oversize' else 1))
    with journal.locked():
        with pytest.raises((OSError, ValueError)):
            sidecar.read()
        with pytest.raises(ValueError):
            sidecar.create(observation)
    assert target.read_bytes() == b'original'


@pytest.mark.parametrize('stage', ['file', 'replace', 'directory'])
def test_atomic_failure_and_retry_boundary(setup, monkeypatch, stage):
    journal, sidecar, observation = setup
    original = os.fsync

    def sync(fd):
        kind = 'directory' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file'
        if stage == kind:
            raise OSError('injected')
        original(fd)

    def replace(*args):
        raise OSError('injected')

    with journal.locked():
        with monkeypatch.context() as patch:
            patch.setattr(os, 'fsync', sync)
            if stage == 'replace':
                patch.setattr(os, 'replace', replace)
            with pytest.raises(OSError):
                sidecar.create(observation)
        assert sidecar.read() == (observation if stage == 'directory' else None)
        if stage == 'directory':
            with pytest.raises(ValueError):
                sidecar.create(observation)
        else:
            sidecar.create(observation)
    assert not list(sidecar.path.parent.glob('.comfy-supervision-*'))


def test_order_size_and_bypassed_validation(setup, monkeypatch):
    journal, sidecar, observation = setup
    events = []
    original_sync, original_replace = os.fsync, os.replace

    def sync(fd):
        events.append('directory' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file')
        original_sync(fd)

    def replace(*args):
        events.append('replace')
        original_replace(*args)

    monkeypatch.setattr(os, 'fsync', sync)
    monkeypatch.setattr(os, 'replace', replace)
    with journal.locked():
        with pytest.raises(ValueError):
            sidecar.create(observation.model_copy(update={'attempt_count': 9}))
        with monkeypatch.context() as patch:
            patch.setattr(module, 'MAX_OBSERVATION_BYTES', 1)
            with pytest.raises(ValueError):
                sidecar.create(observation)
        assert events == [] and sidecar.read() is None
        sidecar.create(observation)
        assert events == ['file', 'replace', 'directory']


def transition_record(observation, phase, **changes):
    values = {
        'cleanup_phase': phase,
        'attempt_count': 1,
        'updated_at': 101,
        'prompt_id': observation.context.job_id,
    }
    if phase == 'observed':
        values.update(
            source=observation.context.mode, evidence_sha256='d' * 64, cancel_dispatched=True
        )
    return observation.model_copy(update=values | changes)


@pytest.mark.parametrize('final_phase', ['observed', 'unknown'])
def test_one_attempt_and_restart_guard(setup, context, final_phase):
    journal, sidecar, observation = setup
    with journal.locked():
        journal.create_intent()
        journal.accept(context.job_id)
        saved = journal.path.read_bytes()
        sidecar.create(observation)
        intent = transition_record(observation, 'intent')
        sidecar.transition(intent)
    restarted = type(journal)(journal.path.parent, context)
    with restarted.locked():
        other = type(sidecar)(restarted)
        with pytest.raises(ValueError):
            other.transition(intent)
        final = transition_record(observation, final_phase)
        other.transition(final)
        assert other.read() == final
        assert other.read().compute_status == 'unknown'
        for candidate in (intent, final, observation):
            with pytest.raises(ValueError):
                other.transition(candidate)
    assert journal.path.read_bytes() == saved


@pytest.mark.parametrize(
    'failure',
    [
        'missing_sidecar',
        'missing_journal',
        'intent_journal',
        'wrong_receipt',
        'primary',
        'created',
        'backwards',
        'skip',
    ],
)
def test_transition_fail_closed(setup, failure):
    journal, sidecar, observation = setup
    with journal.locked():
        if failure != 'missing_journal':
            journal.create_intent()
            if failure != 'intent_journal':
                journal.accept(observation.context.job_id)
        if failure != 'missing_sidecar':
            sidecar.create(observation)
        candidate = transition_record(observation, 'intent')
        changes = {
            'wrong_receipt': {'prompt_id': '22345678-1234-4234-8234-123456789abc'},
            'primary': {'primary_outcome': 'success'},
            'created': {'created_at': 99},
            'backwards': {'updated_at': 99},
            'skip': {'cleanup_phase': 'unknown'},
        }
        candidate = candidate.model_copy(update=changes.get(failure, {}))
        saved = sidecar.path.read_bytes() if sidecar.path.exists() else None
        with pytest.raises((ValueError, OSError)):
            sidecar.transition(candidate)
        assert (sidecar.path.read_bytes() if sidecar.path.exists() else None) == saved


@pytest.mark.parametrize('stage', ['file', 'directory'])
def test_transition_fsync_failure_retains_attempt_boundary(setup, monkeypatch, stage):
    journal, sidecar, observation = setup
    with journal.locked():
        journal.create_intent()
        journal.accept(observation.context.job_id)
        sidecar.create(observation)
        sync = os.fsync

        def fail(fd):
            kind = 'directory' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file'
            if kind == stage:
                raise OSError('injected')
            sync(fd)

        intent = transition_record(observation, 'intent')
        with monkeypatch.context() as patch:
            patch.setattr(os, 'fsync', fail)
            with pytest.raises(OSError):
                sidecar.transition(intent)
        assert sidecar.read().cleanup_phase == (
            'intent' if stage == 'directory' else 'not_requested'
        )
        if stage == 'directory':
            with pytest.raises(ValueError):
                sidecar.transition(intent)
        else:
            sidecar.transition(intent)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        pytest.fail('Supervision storage must not use network')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


@pytest.mark.parametrize('phase', ['not_requested', 'intent', 'observed', 'unknown'])
def test_cross_mode_sidecar_cannot_be_migrated_or_overwritten(setup, context, phase):
    journal, sidecar, observation = setup
    if phase != 'not_requested':
        observation = transition_record(observation, phase)
    with journal.locked():
        sidecar.create(observation)
    saved = sidecar.path.read_bytes()
    opposite = context.model_copy(update={'mode': 'live' if context.mode == 'mock' else 'mock'})
    if opposite.mode == 'live':
        other_journal = LiveComfyJournalStore(journal.path.parent, opposite)
        other = LiveComfySupervisionStore(other_journal)
        candidate_type, version = LiveComfySupervisionObservation, 2
    else:
        other_journal = ComfyJournalStore(journal.path.parent, opposite)
        other = ComfySupervisionStore(other_journal)
        candidate_type, version = ComfySupervisionObservation, 1
    candidate = candidate_type(
        **(
            observation.model_dump()
            | {
                'schema_version': version,
                'context': opposite,
                'source': opposite.mode if phase == 'observed' else 'none',
            }
        )
    )
    assert other.path == sidecar.path
    with other_journal.locked():
        with pytest.raises(ValueError):
            other.read()
        with pytest.raises(ValueError):
            other.create(candidate)
        with pytest.raises(ValueError):
            other.transition(candidate)
    assert sidecar.path.read_bytes() == saved


def test_constructor_and_observation_types_do_not_cross_modes(setup):
    journal, sidecar, observation = setup
    wrong_store = (
        LiveComfySupervisionStore
        if type(sidecar) is ComfySupervisionStore
        else ComfySupervisionStore
    )
    with pytest.raises(TypeError):
        wrong_store(journal)
    wrong_type = (
        LiveComfySupervisionObservation
        if type(observation) is ComfySupervisionObservation
        else ComfySupervisionObservation
    )
    forged = wrong_type.model_construct(**observation.model_dump())
    with journal.locked():
        with pytest.raises(TypeError):
            sidecar.create(forged)
        with pytest.raises(TypeError):
            sidecar.transition(forged)
        assert sidecar.read() is None
