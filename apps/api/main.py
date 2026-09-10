import asyncio
import sqlite3
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Path, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from animation_studio.media.artifacts import ArtifactUnavailable, load_fixture_artifact
from animation_studio.observability import emit_event, pipeline_logging
from animation_studio.persistence.db import init_db
from animation_studio.persistence.job_results import JobResultRepository, SavedOutcome, UnknownJobError
from animation_studio.pipeline.dispatcher import (
    ActiveFixtureJob, DispatchUnavailable, FixtureDispatcher, UnknownProject,
)
from animation_studio.settings import get_database_path, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()  # Fail startup on invalid configuration without creating a database.
    with pipeline_logging():
        dispatcher = FixtureDispatcher()
        app.state.fixture_dispatcher = dispatcher
        try:
            yield
        finally:
            await asyncio.to_thread(dispatcher.close)
            app.state.fixture_dispatcher = None


app = FastAPI(title='Animation Studio API', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:3000', 'http://127.0.0.1:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    master_prompt: str | None = Field(default=None)
    target_duration_seconds: int | None = Field(default=None, ge=1, le=600)
    status: str = Field(default='draft')


class Project(BaseModel):
    id: int
    title: str
    master_prompt: str | None = None
    target_duration_seconds: int | None = None
    status: str = 'draft'


class JobCreate(BaseModel):
    current_step: str | None = Field(default='queued')


class FixtureJobCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')


class RenderJob(BaseModel):
    id: int
    project_id: int
    current_step: str | None = 'queued'
    current_shot: int | None = None
    state: str = 'running'
    progress: int = 0


class CharacterCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)


class Character(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: str


class VoiceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str = Field(min_length=1, max_length=120)
    language: str | None = Field(default=None, max_length=80)
    style: str | None = Field(default=None, max_length=400)


class Voice(BaseModel):
    id: int
    name: str
    voice_type: str
    language: str | None
    style: str | None
    created_at: str


class SettingsView(BaseModel):
    database_path: str


class ArtifactQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    download: bool = False


def get_db_path() -> str:
    return get_database_path()


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/settings', response_model=SettingsView)
def read_settings():
    return SettingsView(database_path=str(get_settings().database_path.absolute()))


@app.post('/characters', response_model=Character, status_code=status.HTTP_201_CREATED)
def create_character(payload: CharacterCreate):
    conn = get_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO characters (name, description) VALUES (?, ?)',
            (payload.name, payload.description or None),
        )
        conn.commit()
        row = conn.execute('SELECT * FROM characters WHERE id = ?', (cursor.lastrowid,)).fetchone()
        return Character(**{field: row[field] for field in Character.model_fields})
    finally:
        conn.close()


@app.get('/characters', response_model=list[Character])
def list_characters():
    conn = get_connection()
    try:
        rows = conn.execute('SELECT id, name, description, created_at FROM characters ORDER BY id').fetchall()
        return [Character(**dict(row)) for row in rows]
    finally:
        conn.close()


@app.post('/voices', response_model=Voice, status_code=status.HTTP_201_CREATED)
def create_voice(payload: VoiceCreate):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO voices (name, voice_type, language, style) VALUES (?, 'built_in', ?, ?)",
            (payload.name, payload.language or None, payload.style or None),
        )
        conn.commit()
        row = conn.execute(
            'SELECT id, name, voice_type, language, style, created_at FROM voices WHERE id = ?',
            (cursor.lastrowid,),
        ).fetchone()
        return Voice(**dict(row))
    finally:
        conn.close()


@app.get('/voices', response_model=list[Voice])
def list_voices():
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT id, name, voice_type, language, style, created_at FROM voices ORDER BY id'
        ).fetchall()
        return [Voice(**dict(row)) for row in rows]
    finally:
        conn.close()


@app.post('/projects', response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate):
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Title is required')

    conn = get_connection()
    try:
        cursor = conn.execute(
            '''
            INSERT INTO projects (title, master_prompt, target_duration_seconds, status, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''',
            (payload.title.strip(), payload.master_prompt, payload.target_duration_seconds, payload.status),
        )
        conn.commit()
        project_id = cursor.lastrowid
        row = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
        return Project(
            id=row['id'],
            title=row['title'],
            master_prompt=row['master_prompt'],
            target_duration_seconds=row['target_duration_seconds'],
            status=row['status'],
        )
    finally:
        conn.close()


@app.get('/projects', response_model=list[Project])
def list_projects():
    conn = get_connection()
    try:
        rows = conn.execute('SELECT * FROM projects ORDER BY id ASC').fetchall()
        return [
            Project(
                id=row['id'],
                title=row['title'],
                master_prompt=row['master_prompt'],
                target_duration_seconds=row['target_duration_seconds'],
                status=row['status'],
            )
            for row in rows
        ]
    finally:
        conn.close()


@app.get('/projects/{project_id}', response_model=Project)
def get_project(project_id: int):
    conn = get_connection()
    try:
        row = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')
        return Project(
            id=row['id'],
            title=row['title'],
            master_prompt=row['master_prompt'],
            target_duration_seconds=row['target_duration_seconds'],
            status=row['status'],
        )
    finally:
        conn.close()


@app.post('/projects/{project_id}/jobs', response_model=RenderJob, status_code=status.HTTP_201_CREATED)
def create_job(project_id: int, payload: JobCreate):
    conn = get_connection()
    try:
        project_row = conn.execute('SELECT id FROM projects WHERE id = ?', (project_id,)).fetchone()
        if project_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

        cursor = conn.execute(
            '''
            INSERT INTO render_jobs (project_id, current_step, current_shot, state, progress, updated_at)
            VALUES (?, ?, ?, 'running', 5, CURRENT_TIMESTAMP)
            ''',
            (project_id, payload.current_step or 'queued', None),
        )
        conn.commit()
        job_id = cursor.lastrowid
        row = conn.execute('SELECT * FROM render_jobs WHERE id = ?', (job_id,)).fetchone()
        return RenderJob(
            id=row['id'],
            project_id=row['project_id'],
            current_step=row['current_step'],
            current_shot=row['current_shot'],
            state=row['state'],
            progress=row['progress'],
        )
    finally:
        conn.close()


@app.get('/jobs', response_model=list[RenderJob])
def list_jobs():
    conn = get_connection()
    try:
        rows = conn.execute('SELECT * FROM render_jobs ORDER BY id ASC').fetchall()
        return [
            RenderJob(
                id=row['id'],
                project_id=row['project_id'],
                current_step=row['current_step'],
                current_shot=row['current_shot'],
                state=row['state'],
                progress=row['progress'],
            )
            for row in rows
        ]
    finally:
        conn.close()


@app.post('/projects/{project_id}/fixture-jobs', response_model=RenderJob, status_code=202)
def create_fixture_job(project_id: Annotated[int, Path(gt=0)], payload: FixtureJobCreate, request: Request):
    dispatcher = getattr(request.app.state, 'fixture_dispatcher', None)
    if dispatcher is None:
        raise HTTPException(status_code=503, detail='Job worker প্রস্তুত নয়।')
    try:
        return dispatcher.create(get_db_path(), project_id)
    except UnknownProject as error:
        raise HTTPException(status_code=404, detail='Project not found') from error
    except ValidationError as error:
        raise HTTPException(status_code=422, detail='Project-এ ১–৪০০০ অক্ষরের prompt প্রয়োজন।') from error
    except ActiveFixtureJob as error:
        raise HTTPException(status_code=409, detail='এই project-এর একটি job ইতিমধ্যে চলছে।') from error
    except DispatchUnavailable as error:
        raise HTTPException(status_code=503, detail='Job queue এখন পূর্ণ বা বন্ধ। পরে চেষ্টা করুন।') from error


@app.get('/jobs/{job_id}', response_model=RenderJob)
def get_job(job_id: Annotated[int, Path(gt=0)]):
    conn = get_connection()
    try:
        row = conn.execute('SELECT * FROM render_jobs WHERE id = ?', (job_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail='Job not found')
        return dict(row)
    finally:
        conn.close()


@app.get('/jobs/{job_id}/result', response_model=SavedOutcome | None)
def get_job_result(job_id: Annotated[int, Path(gt=0)]):
    repository = JobResultRepository(get_db_path())
    try:
        return repository.get(job_id)
    except UnknownJobError as error:
        raise HTTPException(status_code=404, detail='Job not found') from error
    except ValidationError as error:
        # Stored data is invalid, not a bad request or an unfinished render.
        raise HTTPException(status_code=500, detail='সংরক্ষিত job result পড়া যাচ্ছে না।') from error


@app.get('/jobs/{job_id}/artifacts/{kind}', response_class=Response)
def get_job_artifact(
    job_id: Annotated[int, Path(gt=0, le=2**63 - 1)],
    kind: Literal['image', 'audio', 'video'],
    query: Annotated[ArtifactQuery, Query()],
):
    headers = {'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, no-store'}
    try:
        outcome = get_job_result(job_id)
        if outcome is None or outcome.result is None:
            raise HTTPException(status_code=404, detail='এই job-এর সংরক্ষিত media নেই।')
        content = load_fixture_artifact(getattr(outcome.result, kind))
    except HTTPException as error:
        error.headers = {**(error.headers or {}), **headers}
        raise
    except ArtifactUnavailable as error:
        raise HTTPException(status_code=error.status_code, detail=error.message, headers=headers) from error
    disposition = 'attachment' if query.download else 'inline'
    return Response(
        content=content.body,
        media_type=content.media_type,
        headers={
            **headers,
            'Content-Disposition': f'{disposition}; filename="job-{job_id}-{kind}.{content.extension}"',
        },
    )


@app.post('/jobs/{job_id}/tick', response_model=RenderJob)
def tick_job(job_id: int):
    conn = get_connection()
    try:
        row = conn.execute('SELECT * FROM render_jobs WHERE id = ?', (job_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Job not found')
        if row['state'] == 'cancelled':
            return RenderJob(
                id=row['id'],
                project_id=row['project_id'],
                current_step=row['current_step'],
                current_shot=row['current_shot'],
                state=row['state'],
                progress=row['progress'],
            )

        conn.execute(
            '''
            UPDATE render_jobs
            SET progress = MIN(100, progress + 15),
                state = CASE WHEN progress + 15 >= 100 THEN 'completed' ELSE 'running' END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND state = 'running'
                AND NOT EXISTS (SELECT 1 FROM fixture_jobs WHERE job_id = render_jobs.id)
            ''',
            (job_id,),
        )
        conn.commit()
        updated = conn.execute('SELECT * FROM render_jobs WHERE id = ?', (job_id,)).fetchone()
        return RenderJob(
            id=updated['id'],
            project_id=updated['project_id'],
            current_step=updated['current_step'],
            current_shot=updated['current_shot'],
            state=updated['state'],
            progress=updated['progress'],
        )
    finally:
        conn.close()


@app.post('/jobs/{job_id}/cancel', response_model=RenderJob)
def cancel_job(job_id: int, request: Request):
    conn = get_connection()
    try:
        row = conn.execute('SELECT * FROM render_jobs WHERE id = ?', (job_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Job not found')

        cancellation = conn.execute(
            '''
            UPDATE render_jobs
            SET state = 'cancelled', updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND state IN ('queued', 'running', 'waiting_for_gpu')
            ''',
            (job_id,),
        )
        conn.commit()
        updated = conn.execute('SELECT * FROM render_jobs WHERE id = ?', (job_id,)).fetchone()
        dispatcher = getattr(request.app.state, 'fixture_dispatcher', None)
        if cancellation.rowcount:
            emit_event('job_cancel_requested', job_id=job_id, project_id=updated['project_id'],
                       shot_id=updated['current_shot'], step='cancelled', state='cancelled',
                       progress=updated['progress'])
        if updated['state'] == 'cancelled' and dispatcher is not None:
            dispatcher.cancel(get_db_path(), job_id)
        return RenderJob(
            id=updated['id'],
            project_id=updated['project_id'],
            current_step=updated['current_step'],
            current_shot=updated['current_shot'],
            state=updated['state'],
            progress=updated['progress'],
        )
    finally:
        conn.close()
