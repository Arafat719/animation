# Prompt Image Generator Starter

**Agent entry:** [short resume](docs/RESUME.md) → current phase only.
See [reading index](docs/plan/INDEX.md); do not load the full master plan for routine work.

**Current milestone:** Local Phase 1 and Phase 2 / 2.10 PASS (2026-09-16).
See the [Phase 2 gate report](docs/phase-2-final-gate-2026-09-16.md).
See the [final gate report](docs/phase-1-final-gate-2026-09-15.md) and
[current work ledger](docs/current-build-status.md). Real AI generation and the
prompt planner remain future work.


This project creates a stylized image from a text prompt using Python and Pillow.

## Start the local Studio

After the backend setup below and `npm --prefix apps/web ci`, start both servers:

```bash
python3 scripts/dev.py
```

Open **http://127.0.0.1:5173** after the ready message. **Ctrl+C** stops both
the API and web server. Busy ports produce a clear error. This Linux launcher
uses the existing `.venv` and frontend dependencies; see the
[startup guide](docs/local-development.md) for settings and troubleshooting.

## Local backend setup

Use Python 3.11 or 3.12 on Linux. Runtime and test dependencies are pinned
separately; this setup does not install AI models or GPU libraries.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip check
```

For runtime only, install `requirements.txt`. Media tests also require system
`ffmpeg` and `ffprobe` on PATH. Run the test suite with:

```bash
DISABLE_REAL_PIPE=1 .venv/bin/python -m pytest -q
```

To run the API separately, use:

```bash
.venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

The combined launcher, this separate API command and the legacy `web_app.py`
server use port 8000; run one of them at a time. The React client is in `apps/web`.

### Versioned contracts

Versioned Project, Character, Voice, persisted Shot and RenderJob baseline schemas are available under the web app's
`/schemas/v1/` path. Check generated contracts with
`.venv/bin/python -m scripts.export_schemas --check`; see the
[Project contract](docs/contracts/project-v1.md) and
[Character contract](docs/contracts/character-v1.md) and
[Voice contract](docs/contracts/voice-v1.md) and
[Shot contract](docs/contracts/shot-v1.md) and
[RenderJob contract](docs/contracts/render-job-v1.md) for fields and compatibility limits.

### Formatting

Read-only formatter checks run separately from lint and tests:

```bash
.venv/bin/python scripts/check_format.py backend
npm --prefix apps/web run format:check
```

New and edited files must pass Ruff/Prettier. Exact existing formatting debt is
recorded so adoption does not rewrite unrelated source. See
[formatting commands and baseline limits](docs/formatting.md), including strict
checks that also report legacy debt.

### Studio sample media

The React Studio submits background fixture jobs and reads their saved progress
and results. Completed samples can be opened or downloaded from the FastAPI API:
`GET /jobs/{job_id}/artifacts/{image|audio|video}`, with `?download=true` for an
attachment. These are fixed sample files. See the
[artifact API contract](docs/artifact-serving.md) for errors and examples, and the
[current build ledger](docs/current-build-status.md) for the remaining work.
Completed samples also show image, video and silent-audio previews in the Studio,
with per-file download and retry controls. See the
[web usage notes](apps/web/README.md#sample-generation-and-media).

### Pipeline logs

The FastAPI app emits JSON lifecycle events to stderr with job, project, shot
and step context. Events describe committed progress/outcomes; cancellation
requests and worker/storage failures are distinguished. Prompt/media details,
tokens and raw exceptions are omitted from these events. No log directory or
new setting is required. See the [logging contract](docs/pipeline-logging.md)
for event names, embedded-runner setup and diagnostic limits.

### Database migrations

The API's existing `init_db` path now upgrades SQLite to the latest Alembic
revision before opening a project/job connection. A new database gets the five
initial tables and an `alembic_version` record. A compatible unversioned database
keeps its rows; incompatible column definitions cause the transaction to roll
back instead of silently accepting the schema.

Migration and recovery details are in [docs/migrations.md](docs/migrations.md).

### Backend settings

`animation_studio/settings.py` validates backend configuration using the already
installed Pydantic dependency. Both the API and database initialization use it.

| Setting | Default | Behavior |
| --- | --- | --- |
| `ANIMATION_DB_PATH` | `<repository>/data/animation.db` | Explicit absolute paths are used directly; explicit relative paths remain relative to the process working directory for compatibility. |

The default stays the same when launching from another directory. If a previous
launch created a database elsewhere through the old working-directory default,
set `ANIMATION_DB_PATH` to that database's absolute path to keep using its data;
databases are not moved automatically.

Empty paths, null bytes, existing directories, `:memory:` and `file:` SQLite
URIs are rejected. This application uses persistent file databases. Environment
settings are checked during API startup and read on demand. `init_db(path)`
takes precedence over the environment for explicit callers. Reading settings or
checking `/health` creates no database. `.env` files are not loaded implicitly.

## Run

```bash
python3 app.py --prompt "anime girl in neon city at sunset"
```

The generated image will be saved inside the `output/` folder.

## What this is

This is a working starter for an image-generation workflow. It is intentionally lightweight so it runs immediately in a standard Python environment. It can be upgraded later into a real AI image/video animation pipeline.

## Next upgrades

- Real diffusion model integration
- Character consistency
- Pose/expression controls
- Short video generation
- Storyboard / animation timeline
- LoRA-based character training

## HTTP API (local)

The project includes a tiny HTTP server (`web_app.py`) exposing a few helpful endpoints for programmatic use. Start the server and call the endpoints locally:

Start server:

```bash
python3 web_app.py
# Opens at http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

List saved characters:

```bash
curl http://localhost:8000/characters
curl http://localhost:8000/api/v1/characters
```

Generate a single image (form-encoded):

```bash
curl -X POST http://localhost:8000/generate \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-d "prompt=anime+girl+in+neon+city&character_name=Airi&character_style=anime"
```

Generate a storyboard (JSON):

```bash
curl -X POST http://localhost:8000/storyboard \
	-H "Content-Type: application/json" \
	-d '{"character_name":"Airi","character_style":"anime","pose":"front","scenes":["neon street","rooftop"]}'
```

Create an animation (GIF) from scenes (JSON):

```bash
curl -X POST http://localhost:8000/animate \
	-H "Content-Type: application/json" \
	-d '{"character_name":"Airi","character_style":"anime","pose":"front","scenes":["neon street","rooftop","close-up"]}'
```

Notes:
- Generated images and GIFs are saved under the `output/` folder and returned as paths (e.g. `/output/2026...png`).
- MP4 export is not enabled by default; to convert GIF→MP4 install `ffmpeg` and run locally:

```bash
ffmpeg -y -i output/<name>.gif -movflags +faststart -pix_fmt yuv420p output/<name>.mp4
```

Dependencies:

```bash
python3 -m pip install -r requirements.txt
```
