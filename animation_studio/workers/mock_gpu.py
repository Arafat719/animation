"""Authenticated fake GPU HTTP service; no inference, database, or cloud calls."""

from secrets import compare_digest
from threading import Lock
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import Field

from animation_studio.providers.gpu import (
    Contract,
    GPUCapabilities,
    GPUHealth,
    GPUJob,
    GPUJobRequest,
    GPUProviderError,
    MockGPUProvider,
)


class CancelRequest(Contract):
    job_id: str = Field(min_length=1, max_length=4000)


def create_app(*, token: str, provider: MockGPUProvider | None = None) -> FastAPI:
    """Create an isolated mock worker. Bind the ASGI server to 127.0.0.1.

    The caller supplies a token; deployment secret loading is a later step.
    advance() remains a Python test control, never a remotely exposed endpoint.
    Polling does not advance jobs. Process restart discards all mock state.
    """
    if not isinstance(token, str) or not token.strip():
        raise ValueError('A non-empty worker token is required')
    expected = f'Bearer {token}'.encode()
    worker = provider if provider is not None else MockGPUProvider()

    submissions: dict[str, tuple[GPUJobRequest, str]] = {}
    submission_lock = Lock()

    def authenticate(authorization: Annotated[str | None, Header()] = None):
        if authorization is None or not compare_digest(authorization.encode(), expected):
            raise HTTPException(
                status_code=401,
                detail={'code': 'unauthorized'},
                headers={'WWW-Authenticate': 'Bearer'},
            )

    app = FastAPI(
        title='Local mock GPU worker',
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(authenticate)],
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _error: RequestValidationError):
        # Do not echo prompts, credentials or arbitrary invalid input.
        return JSONResponse(status_code=422, content={'detail': {'code': 'invalid_input'}})

    @app.exception_handler(GPUProviderError)
    async def provider_error(_request: Request, error: GPUProviderError):
        statuses = {
            'invalid_input': 422,
            'not_found': 404,
            'unsupported': 422,
            'timeout': 504,
            'unavailable': 503,
        }
        return JSONResponse(
            status_code=statuses[error.code], content={'detail': {'code': error.code}}
        )

    @app.get('/health', response_model=GPUHealth)
    def health():
        return worker.health_check()

    @app.get('/capabilities', response_model=GPUCapabilities)
    def capabilities():
        return worker.capabilities()

    @app.post('/jobs', response_model=GPUJob, status_code=202)
    def submit(
        body: GPUJobRequest,
        idempotency_key: Annotated[
            str | None, Header(min_length=1, max_length=128, pattern=r'^[A-Za-z0-9._-]+$')
        ] = None,
    ):
        if idempotency_key is None:
            return worker.submit(body)
        # Atomic with creation: concurrent/replayed requests cannot create two jobs.
        with submission_lock:
            existing = submissions.get(idempotency_key)
            if existing is not None:
                original, job_id = existing
                if original != body:
                    raise HTTPException(409, detail={'code': 'idempotency_conflict'})
                return worker.status(job_id)
            job = worker.submit(body)
            submissions[idempotency_key] = (body, job.job_id)
            return job

    @app.get('/jobs/{job_id}', response_model=GPUJob)
    def status(job_id: str):
        return worker.status(job_id)

    @app.post('/cancel', response_model=GPUJob)
    def cancel(body: CancelRequest):
        return worker.cancel(body.job_id)

    return app


def create_app_from_env() -> FastAPI:
    """Uvicorn factory: load secrets after the server configures its log handlers."""
    from animation_studio.providers.gpu_secrets import configure_gpu_logging, load_gpu_token

    secret = load_gpu_token()
    configure_gpu_logging(secret)
    return create_app(token=secret.get_secret_value())
