<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

## 4. Technical architecture

### 4.1 Components

| Component | Responsibility | Default technology |
|---|---|---|
| Web client | Projects, character/voice selection, prompt, progress, previews | React + Vite + TypeScript |
| Local API/orchestrator | Validation, jobs, state machine, provider calls, media metadata | Python + FastAPI |
| Database | Private prototype metadata and job state | SQLite + SQLModel/Alembic |
| Job runner | Executes resumable pipeline steps | In-process worker first; Redis/Celery only later if required |
| GPU worker | Image, video, TTS and lip-sync inference | Python service and/or ComfyUI API workflows |
| GPU host | On-demand NVIDIA GPU | RunPod adapter first; vendor-neutral interface |
| Media engine | Probe, normalize, concatenate, mix audio, subtitles, export | FFmpeg/ffprobe |
| Storage | Inputs, intermediates, outputs, manifests | Local filesystem in V1; object storage adapter later |
| Desktop shell | Installable version after V1 stability | Tauri, reusing the web client |

### 4.2 Required boundaries

Create these interfaces before connecting real models:

```python
class PlannerProvider: ...
class ImageProvider: ...
class VideoProvider: ...
class TTSProvider: ...
class LipSyncProvider: ...
class GPUProvider: ...
class StorageProvider: ...
```

Every provider must expose:

- `health_check()`
- validated input/output schemas;
- timeout and cancellation support;
- normalized progress events;
- normalized error codes;
- mock implementation for tests;
- model name, version and seed in result metadata.

### 4.3 Suggested repository layout

```text
ai-animation-studio/
├── apps/
│   ├── web/                    # React/Vite/TypeScript
│   └── api/                    # FastAPI orchestrator
├── workers/
│   └── gpu-worker/             # Remote inference endpoints
├── animation_studio/
│   ├── domain/                 # schemas and state machine
│   ├── pipeline/               # step orchestration
│   ├── providers/              # mock/local/runpod/model adapters
│   ├── media/                  # FFmpeg wrapper
│   └── persistence/            # database and repositories
├── workflows/
│   └── comfyui/                # versioned API-format JSON workflows
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/
├── data/                       # gitignored runtime data
├── docs/
│   ├── architecture.md
│   ├── decisions/
│   ├── model-benchmarks.md
│   └── operations.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
└── README.md
```

Do not introduce a monorepo framework unless it solves a demonstrated problem.

---
