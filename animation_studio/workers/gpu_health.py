"""Authenticated device discovery only; no inference/job execution capability."""

import csv
import io
import subprocess
from secrets import compare_digest
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import Field, ValidationError

from animation_studio.providers.gpu import Contract, GPUCapabilities, GPUHealth
from animation_studio.providers.gpu_secrets import configure_gpu_logging, load_gpu_token


class Device(Contract):
    uuid: str = Field(pattern=r'^GPU-[a-zA-Z0-9-]+$')
    name: str = Field(min_length=1, max_length=200)
    memory_mib: int = Field(gt=0, strict=True)
    driver_version: str = Field(pattern=r'^\d+(\.\d+)+$')


class Discovery(Contract):
    devices: tuple[Device, ...] = ()
    error_code: (
        Literal['tool_missing', 'probe_timeout', 'probe_failed', 'invalid_output', 'no_gpu'] | None
    ) = None


def discover_gpus() -> Discovery:
    """Bounded NVIDIA utility query; output never includes stderr or environment."""
    try:
        result = subprocess.run(
            [
                'nvidia-smi',
                '--query-gpu=uuid,name,memory.total,driver_version',
                '--format=csv,noheader,nounits',
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except FileNotFoundError:
        return Discovery(error_code='tool_missing')
    except subprocess.TimeoutExpired:
        return Discovery(error_code='probe_timeout')
    except (OSError, UnicodeError):
        return Discovery(error_code='probe_failed')
    if result.returncode:
        return Discovery(error_code='probe_failed')
    if len(result.stdout) > 65536:
        return Discovery(error_code='invalid_output')
    try:
        devices = []
        for row in csv.reader(io.StringIO(result.stdout), skipinitialspace=True, strict=True):
            if len(row) != 4:
                raise ValueError('Invalid columns')
            uuid, name, memory, driver = (item.strip() for item in row)
            if not memory.isascii() or not memory.isdigit():
                raise ValueError('Invalid memory')
            devices.append(
                Device(uuid=uuid, name=name, memory_mib=int(memory), driver_version=driver)
            )
        if len({device.uuid for device in devices}) != len(devices):
            raise ValueError('Duplicate device')
        return Discovery(devices=tuple(devices), error_code=None if devices else 'no_gpu')
    except (ValueError, csv.Error, ValidationError):
        return Discovery(error_code='invalid_output')


def create_app() -> FastAPI:
    secret = load_gpu_token()
    configure_gpu_logging(secret)
    expected = ('Bearer ' + secret.get_secret_value()).encode()

    def authenticate(authorization: Annotated[str | None, Header()] = None):
        if authorization is None or not compare_digest(authorization.encode(), expected):
            raise HTTPException(
                401, detail={'code': 'unauthorized'}, headers={'WWW-Authenticate': 'Bearer'}
            )

    app = FastAPI(
        title='GPU device health worker',
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(authenticate)],
    )

    @app.get('/health', response_model=GPUHealth)
    def health():
        result = discover_gpus()
        return GPUHealth(
            healthy=bool(result.devices) and result.error_code is None,
            provider_name='nvidia-device-health',
            provider_version='1',
        )

    @app.get('/devices', response_model=Discovery)
    def devices():
        return discover_gpus()

    @app.get('/capabilities', response_model=GPUCapabilities)
    def capabilities():
        return GPUCapabilities(operations=())

    return app
