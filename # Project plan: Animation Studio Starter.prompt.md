# Project plan: Animation Studio Starter — historical legacy snapshot

> **Planning status corrected: 2026-09-09.** This document describes the old
> `app.py` / `web_app.py` starter. Its completion counts and proposed work are
> historical, not the current Studio build queue. Use the
> [master plan](AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md) and
> [current status ledger](docs/current-build-status.md) to resume. The current
> plan-only request applied to 2026-09-09; current owner instructions and the
> ledger determine today's work. Real AI remains a later phase.
>
> The React/FastAPI/SQLite fixture pipeline has since been added. Latest recorded
> backend validation is 206 tests from [step 1.12](docs/artifact-api-checkpoint.md),
> 2026-09-10; frontend/browser checks passed in
> [step 1.13](docs/sample-preview-checkpoint.md). Next candidate:
> **1.14, structured pipeline logging**, not discovery 0.1 or real-model setup.

## Legacy state recorded at the time

- The core generator in [app.py](app.py) is working for deterministic local image generation.
- Prompt sanitization, character profile generation/persistence, caching, storyboard generation, and GIF animation creation are already implemented.
- The HTTP API in [web_app.py](web_app.py) exposes health, character listing, image generation, storyboard creation, and animation creation endpoints.
- The project includes a basic README and local usage instructions.
- The original starter snapshot reported 4 passed, 0 failed. This is a historical count, not the current repository test result.

## Legacy functionality recorded as done

- Prompt sanitization and validation
- Character profile creation and reuse via characters.json
- Output image generation with caching
- Deterministic background + scene composition
- Storyboard generation from multiple scenes
- GIF animation assembly from frames
- CLI execution path
- Local web server endpoints for programmatic use

## Legacy backlog snapshot — not the active execution queue

The items below are retained for reference, not revalidated completion statuses.
The new FastAPI tests do not establish coverage of the separate `web_app.py`
legacy server. Reassess a legacy item only if the owner chooses that work.

1. Validate the real AI backend in [app.py](app.py)
   - Confirm diffusers/torch stack works in the intended environment
   - Resolve or document dependency and warning issues
   - Keep the real pipeline optional and safe behind the disable flag

2. Add API coverage for [web_app.py](web_app.py)
   - Health endpoint validation
   - Character listing endpoint validation
   - Generate endpoint validation
   - Storyboard endpoint validation
   - Animate endpoint validation

3. Improve storyboard and animation consistency
   - Enhance scene-to-scene character continuity
   - Improve pose and expression stability across frames
   - Refine style and composition for more cinematic output

4. Add stronger validation and error handling
   - Empty or invalid prompt handling
   - Invalid scene lists
   - Missing/unsupported character inputs
   - Graceful failure for generation and conversion errors

5. Improve output lifecycle and storage management
   - Better output directory organization
   - Duplicate prevention and smarter naming
   - Cleanup strategy for stale generated files

6. Polish user-facing docs and UX
   - Add troubleshooting notes for dependency warnings
   - Document actual real-pipeline requirements
   - Clarify API usage and example responses
   - Add known limitations section

7. Plan future roadmap features
   - More advanced diffusion model integration
   - Character consistency improvements
   - Pose/expression control
   - Short video generation
   - Storyboard timeline controls
   - LoRA-based character training / custom model workflows

## Historical proposed order — superseded

Do not execute this sequence as the Studio roadmap. The current master plan
continues local fixture/media work first; real-model work has later phase gates.

1. Resolve backend warnings and verify real pipeline behavior
2. Add web API tests
3. Improve generation consistency and quality
4. Add validation and error handling
5. Clean up output management and docs
6. Expand roadmap features after the prototype is stable

## Historical overall assessment

At the time of this starter snapshot, the recorded assessment was: core functionality works, tests pass, and the main remaining work is around validation, robustness, and feature expansion rather than fixing broken base functionality.
