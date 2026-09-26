import asyncio

import httpx
import pytest

from animation_studio.providers.gpu import GPUJob, MockGPUProvider
from animation_studio.workers.mock_gpu import create_app

TOKEN = 'test-only-worker-token'
PAYLOAD = {
    'operation': 'mock.noop',
    'prompt': 'শান্ত নদী',
    'model_name': 'mock-worker',
    'model_version': '1',
    'seed': 42,
}


def run(scenario, *, provider=None):
    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(token=TOKEN, provider=provider)),
            base_url='http://worker',
            headers={'Authorization': f'Bearer {TOKEN}'},
        ) as client:
            await scenario(client)

    asyncio.run(exercise())


def test_http_lifecycle():
    worker = MockGPUProvider()

    async def scenario(client):
        assert (await client.get('/health')).json()['provider_name'] == 'mock-gpu'
        assert (await client.get('/capabilities')).json()['operations'] == ['mock.noop']
        response = await client.post('/jobs', json=PAYLOAD)
        assert response.status_code == 202
        queued = GPUJob.model_validate(response.json())
        assert queued.status == 'queued' and queued.request.seed == 42
        url = f'/jobs/{queued.job_id}'
        assert (await client.get(url)).json() == response.json()
        worker.advance(queued.job_id)
        assert (await client.get(url)).json()['progress'] == 50
        cancelled = await client.post('/cancel', json={'job_id': queued.job_id})
        assert cancelled.json()['status'] == 'cancelled'
        assert (
            await client.post('/cancel', json={'job_id': queued.job_id})
        ).json() == cancelled.json()
        assert (await client.get(url)).json() == cancelled.json()
        second = (await client.post('/jobs', json=PAYLOAD)).json()
        assert second['job_id'] != queued.job_id
        worker.advance(second['job_id'])
        worker.advance(second['job_id'])
        assert (await client.get(f'/jobs/{second["job_id"]}')).json()['status'] == 'succeeded'
        assert (await client.post('/cancel', json={'job_id': second['job_id']})).json()[
            'status'
        ] == 'succeeded'

    run(scenario, provider=worker)


@pytest.mark.parametrize(
    'method,path',
    [
        ('GET', '/health'),
        ('GET', '/capabilities'),
        ('POST', '/jobs'),
        ('GET', '/jobs/unknown'),
        ('POST', '/cancel'),
    ],
)
@pytest.mark.parametrize('authorization', [None, 'Bearer wrong', 'Basic wrong'])
def test_authentication(method, path, authorization):
    async def scenario(client):
        client.headers.pop('Authorization')
        headers = {} if authorization is None else {'Authorization': authorization}
        response = await client.request(method, path, headers=headers, json=PAYLOAD)
        assert response.status_code == 401
        assert response.headers['www-authenticate'] == 'Bearer'
        assert TOKEN not in response.text

    run(scenario)


@pytest.mark.parametrize(
    'method,path,payload,status,code',
    [
        ('POST', '/jobs', {}, 422, 'invalid_input'),
        ('POST', '/jobs', {**PAYLOAD, 'seed': True}, 422, 'invalid_input'),
        ('POST', '/jobs', {**PAYLOAD, 'operation': 'real.image'}, 422, 'unsupported'),
        ('GET', '/jobs/missing', None, 404, 'not_found'),
        ('POST', '/cancel', {'job_id': 'missing'}, 404, 'not_found'),
        ('POST', '/cancel', {'job_id': ' '}, 422, 'invalid_input'),
    ],
)
def test_errors(method, path, payload, status, code):
    async def scenario(client):
        response = await client.request(method, path, json=payload)
        assert response.status_code == status
        assert response.json() == {'detail': {'code': code}}
        assert (await client.post('/jobs', json=PAYLOAD)).json()['job_id'] == 'mock-gpu-1'

    run(scenario)


def test_no_remote_test_controls_or_schema():
    async def scenario(client):
        for path in ['/advance', '/docs', '/openapi.json']:
            assert (await client.get(path)).status_code == 404
        response = await client.post(
            '/jobs', content='{"secret":', headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 422 and 'secret' not in response.text

    run(scenario)


def test_app_state_isolation():
    async def first(client):
        await client.post('/jobs', json=PAYLOAD)

    async def second(client):
        assert (await client.get('/jobs/mock-gpu-1')).status_code == 404

    run(first)
    run(second)


@pytest.mark.parametrize('token', ['', ' ', None])
def test_requires_token(token):
    with pytest.raises(ValueError):
        create_app(token=token)
