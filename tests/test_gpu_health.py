import subprocess

import pytest
from fastapi.testclient import TestClient

from animation_studio.workers import gpu_health

VALID = 'GPU-ab12, NVIDIA RTX A5000, 24564, 550.54.15\n'


def probe(monkeypatch, text, code=0):
    def run(command, **kwargs):
        assert command == [
            'nvidia-smi',
            '--query-gpu=uuid,name,memory.total,driver_version',
            '--format=csv,noheader,nounits',
        ]
        assert kwargs['timeout'] == 5 and not kwargs['check']
        return subprocess.CompletedProcess(command, code, text, 'private stderr')

    monkeypatch.setattr(gpu_health.subprocess, 'run', run)


def test_device_parsing(monkeypatch):
    probe(monkeypatch, VALID)
    result = gpu_health.discover_gpus()
    assert result.error_code is None
    assert result.devices[0].memory_mib == 24564
    assert result.devices[0].name == 'NVIDIA RTX A5000'


@pytest.mark.parametrize(
    'text,error',
    [
        ('', 'no_gpu'),
        ('garbage', 'invalid_output'),
        (VALID + VALID, 'invalid_output'),
        (VALID.replace('24564', 'N/A'), 'invalid_output'),
        (VALID.replace('24564', '0'), 'invalid_output'),
        ('x' * 65537, 'invalid_output'),
    ],
)
def test_bad_output(monkeypatch, text, error):
    probe(monkeypatch, text)
    result = gpu_health.discover_gpus()
    assert result.error_code == error and not result.devices


@pytest.mark.parametrize(
    'exception,error',
    [
        (FileNotFoundError(), 'tool_missing'),
        (subprocess.TimeoutExpired('nvidia-smi', 5), 'probe_timeout'),
        (PermissionError(), 'probe_failed'),
    ],
)
def test_probe_errors(monkeypatch, exception, error):
    def fail(*args, **kwargs):
        raise exception

    monkeypatch.setattr(gpu_health.subprocess, 'run', fail)
    assert gpu_health.discover_gpus().error_code == error


def test_nonzero_exit(monkeypatch):
    probe(monkeypatch, VALID, 1)
    assert gpu_health.discover_gpus().error_code == 'probe_failed'


def test_auth_and_capability_honesty(monkeypatch):
    monkeypatch.setenv('ANIMATION_GPU_TOKEN', 'health-fixture-token')
    probe(monkeypatch, VALID)
    with TestClient(gpu_health.create_app()) as client:
        for path in ['/health', '/devices', '/capabilities']:
            assert client.get(path).status_code == 401
        client.headers['Authorization'] = 'Bearer health-fixture-token'
        assert client.get('/health').json()['healthy']
        assert client.get('/devices').json()['devices'][0]['uuid'] == 'GPU-ab12'
        assert client.get('/capabilities').json() == {'operations': []}
        assert client.post('/jobs', json={}).status_code == 404
        probe(monkeypatch, '')
        assert not client.get('/health').json()['healthy']
        assert client.get('/devices').json()['error_code'] == 'no_gpu'
