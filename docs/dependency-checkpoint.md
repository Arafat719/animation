# Micro-step 1.2 — dependency checkpoint

Date: 2026-09-07

Runtime dependencies and their Linux Python 3.11/3.12 transitive dependencies
are pinned in `requirements.txt`. Test dependencies are pinned separately in
`requirements-dev.txt`. Versions were retained from the existing passing
environment; no dependency upgrade was performed.

Validation on Linux, Python 3.12.3:

- Existing environment baseline: 17 tests passed.
- Fresh isolated environment: `/tmp/animation-deps-check`, without system packages.
- Binary-only installation from `requirements-dev.txt`: successful.
- `python -m pip check`: no broken requirements.
- Imports of FastAPI, Pydantic, Uvicorn, Pillow, pytest, HTTPX and the API: passed.
- `DISABLE_REAL_PIPE=1 python -m pytest -q -p no:cacheprovider`: 17 passed in 3.28s.
- Two existing TestClient deprecation warnings remain (HTTPX and BlockingPortal).
- Python 3.11 and remote GitHub CI have not been executed in this step.

Tests require system FFmpeg/ffprobe and an environment that permits local
socketpair communication. The restricted sandbox blocks that communication,
so tests were run outside it. No real model or paid GPU was used.

Files in this step: `requirements.txt`, `requirements-dev.txt`,
`.github/workflows/ci.yml`, `README.md`, and this checkpoint. The original
`.venv` was preserved. No commit was made because the worktree already contained
user changes. This checkpoint records the validated state without claiming
that Phase 1 as a whole is complete.
