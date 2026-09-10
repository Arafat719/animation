import hashlib
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path
from threading import Event, Timer

import pytest
from pydantic import ValidationError

from animation_studio.providers.fake import (
    Artifact, FakeConfig, FakeProvider, FakeRequest, FakeResult, ProgressEvent, ProviderError,
)

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture
def provider():
    return FakeProvider(FakeConfig(delay_seconds=0))


def test_repeatable_result_valid_media_metadata_and_progress(provider, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    progress = []
    request = FakeRequest(prompt='  A quiet rooftop  ', seed=42)
    result = provider.generate(request, on_progress=progress.append)
    assert provider.generate(request) == result
    assert FakeResult.model_validate_json(result.model_dump_json()) == result
    assert result.provider_name == 'fake'
    assert result.provider_version == '1'
    assert result.model_name == 'fixture-media'
    assert result.model_version == '1'
    assert result.seed == 42
    assert [(e.step, e.progress) for e in progress] == [
        ('started', 0), ('image', 30), ('audio', 60), ('video', 90), ('completed', 100),
    ]
    for artifact in (result.image, result.audio, result.video):
        assert artifact.path.is_absolute()
        assert artifact.sha256 == hashlib.sha256(artifact.path.read_bytes()).hexdigest()
    assert result.audio.duration_seconds == 1
    assert result.video.duration_seconds > 0
    with wave.open(str(result.audio.path), 'rb') as audio:
        assert audio.getframerate() == 16000
        assert audio.readframes(audio.getnframes()) == b'\0' * 32000
    assert list(tmp_path.iterdir()) == []
    assert provider.health_check().healthy


@pytest.mark.parametrize('payload', [
    {}, {'prompt': '  '}, {'prompt': 'x' * 4001}, {'prompt': 'x', 'seed': -1},
    {'prompt': 'x', 'seed': True}, {'prompt': 'x', 'seed': 2**32},
    {'prompt': 'x', 'timeout_seconds': 0}, {'prompt': 'x', 'timeout_seconds': float('nan')},
    {'prompt': 'x', 'extra': 'not allowed'},
])
def test_invalid_input_has_normalized_error(provider, payload):
    with pytest.raises(ProviderError) as error:
        provider.generate(payload)
    assert error.value.code == 'invalid_input'


def test_output_and_configuration_validation():
    with pytest.raises(ValidationError):
        ProgressEvent(step='completed', progress=101)
    with pytest.raises(ValidationError):
        Artifact(kind='audio', path=Path('/tmp/sample'), sha256='invalid', duration_seconds=-1)
    with pytest.raises(ValidationError):
        FakeConfig(delay_seconds=-1)


@pytest.mark.parametrize('filename', ['sample_image.png', 'silent_audio.wav', 'sample_video.mp4'])
@pytest.mark.parametrize('missing', [True, False])
def test_missing_and_corrupt_fixtures_report_failure(tmp_path, filename, missing):
    for name in ('sample_image.png', 'silent_audio.wav', 'sample_video.mp4'):
        shutil.copy2(FIXTURES / name, tmp_path / name)
    if missing:
        (tmp_path / filename).unlink()
    else:
        (tmp_path / filename).write_bytes(b'not valid media')
    provider = FakeProvider(FakeConfig(fixture_dir=tmp_path, delay_seconds=0))
    progress = []
    with pytest.raises(ProviderError) as error:
        provider.generate(FakeRequest(prompt='demo'), on_progress=progress.append)
    code = 'fixture_missing' if missing else 'fixture_invalid'
    assert error.value.code == code
    assert all(event.progress < 100 for event in progress)
    health = provider.health_check()
    assert not health.healthy
    assert health.error_code == code


def test_non_silent_audio_is_rejected(tmp_path):
    shutil.copy2(FIXTURES / 'sample_image.png', tmp_path / 'sample_image.png')
    shutil.copy2(FIXTURES / 'sample_audio.wav', tmp_path / 'silent_audio.wav')
    health = FakeProvider(FakeConfig(fixture_dir=tmp_path, delay_seconds=0)).health_check()
    assert not health.healthy
    assert health.error_code == 'fixture_invalid'


def test_timeout_during_predictable_delay():
    progress = []
    provider = FakeProvider(FakeConfig(delay_seconds=0.1))
    with pytest.raises(ProviderError) as error:
        provider.generate(FakeRequest(prompt='demo', timeout_seconds=0.02), on_progress=progress.append)
    assert error.value.code == 'timeout'
    assert [e.step for e in progress] == ['started']


def test_delay_is_applied_per_artifact():
    provider = FakeProvider(FakeConfig(delay_seconds=0.02))
    started = time.monotonic()
    provider.generate(FakeRequest(prompt='demo'))
    assert time.monotonic() - started >= 0.06


@pytest.mark.parametrize('pre_cancelled', [True, False])
def test_cancel_before_start_or_during_delay(pre_cancelled):
    cancel = Event()
    progress = []
    timer = Timer(0.02, cancel.set)
    if pre_cancelled:
        cancel.set()
    else:
        timer.start()
    try:
        with pytest.raises(ProviderError) as error:
            FakeProvider(FakeConfig(delay_seconds=0.2)).generate(
                FakeRequest(prompt='demo'), cancel=cancel, on_progress=progress.append,
            )
        assert error.value.code == 'cancelled'
        assert all(e.progress == 0 for e in progress)
    finally:
        if not pre_cancelled:
            timer.join()


def test_cancellation_does_not_poison_next_call(provider):
    cancel = Event()

    def on_progress(event):
        if event.step == 'audio':
            cancel.set()

    with pytest.raises(ProviderError) as error:
        provider.generate(FakeRequest(prompt='demo'), cancel=cancel, on_progress=on_progress)
    assert error.value.code == 'cancelled'
    assert provider.generate(FakeRequest(prompt='next')).video.path.exists()


@pytest.mark.parametrize('missing', ['ffprobe', 'ffmpeg'])
def test_missing_dependency_is_reported(provider, monkeypatch, missing):
    original_which = shutil.which
    monkeypatch.setattr(shutil, 'which', lambda name: None if name == missing else original_which(name))
    assert provider.health_check().error_code == 'dependency_missing'


def test_unreadable_fixture_reports_io_error(provider, monkeypatch):
    def denied(_):
        raise PermissionError('Test read denied')

    monkeypatch.setattr(Path, 'read_bytes', denied)
    assert provider.health_check().error_code == 'io_error'


def test_progress_callback_failure_is_not_hidden(provider):
    def failed_callback(_):
        raise RuntimeError('Caller callback failed')

    with pytest.raises(RuntimeError, match='Caller callback failed'):
        provider.generate(FakeRequest(prompt='demo'), on_progress=failed_callback)


@pytest.mark.parametrize('cancelled', [False, True])
def test_hung_media_process_is_stopped(provider, monkeypatch, cancelled):
    original_popen = subprocess.Popen
    children = []
    cancel = Event()

    def hung_process(*args, **kwargs):
        child = original_popen([sys.executable, '-c', 'import time; time.sleep(30)'], **kwargs)
        children.append(child)
        if cancelled:
            cancel.set()
        return child

    monkeypatch.setattr(subprocess, 'Popen', hung_process)
    with pytest.raises(ProviderError) as error:
        provider.generate(FakeRequest(prompt='demo', timeout_seconds=0.3), cancel=cancel)
    assert error.value.code == ('cancelled' if cancelled else 'timeout')
    assert len(children) == 1
    assert children[0].poll() is not None
