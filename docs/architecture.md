# AI Animation Studio

This repository currently holds a lightweight starter project and is being expanded toward a private AI animation studio prototype.

## Current status

- Local Python project exists
- Minimal image generation example works
- No real GPU model is active yet
- Phase 1 focuses on local skeleton and mock pipeline

## Planned structure

- apps/api: FastAPI backend
- apps/web: React + Vite frontend
- animation_studio/domain: schemas and state models
- animation_studio/pipeline: orchestration and job flow
- animation_studio/providers: mock and provider abstractions
- animation_studio/media: FFmpeg/media tools
- animation_studio/persistence: SQLite and repository layer
- tests/unit and tests/integration: validation and regression coverage
