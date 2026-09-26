# Voice baseline checkpoint — 1.17c

Date: 2026-09-15. Voice baseline implementation complete; full 1.17 remains
PARTIAL. Next bounded step: 1.17d persisted Shot contract.

## Changes

- Extract existing VoiceCreate/Voice unchanged into `domain/v1/voice.py`.
- Add strict, frozen, complete six-column VoiceRecord, with required nullable keys.
- Publish three Draft 2020-12 schemas through the existing export/CI registry.
- Document `voice_type` versus future `type`, SQL/API defaults, normalization,
  unrestricted legacy types and feature-phase limits in [the contract](contracts/voice-v1.md).
- Add 11 tests: schema/API matching; independent legacy and actual 0001/0002/0003
  upgrade/reopen preservation; strict record/default rules; future-field rejection.

## Checks

- New Voice contract suite: 11 PASS, two existing dependency warnings.
- Full OpenAPI snapshot before/after: identical.
- All nine exported schemas match models and appear byte-for-byte in the web build.
- Frontend lint, typecheck/build and frontend/backend incremental formatters: PASS.
- No UI change; browser regression and live schema HTTP checks were not repeated.
- Full backend suite: **307 PASS**, three existing dependency deprecation warnings (55.38s).
  Command: `DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -o faulthandler_timeout=30`.

Initial full-suite attempts omitted CI's `DISABLE_REAL_PIPE=1` and were interrupted
while the legacy image test imported optional transformers/diffusers. The corrected
command uses that existing fixture-only setting and a 180-second timeout.
Sandbox API test attempts were interrupted; focused tests passed outside the sandbox.

Git status works, but `git diff --stat` / `--numstat` fails with an empty object
`.git/objects/03/863f9b0e86390e1a6f89839c745bc57538d213` and a segmentation fault.
Git objects were not modified or repaired. This limits Git-based diff review.

No SQL migration, dependency change or user runtime database operation was needed.
Shot/RenderJob contracts and Project NULL-status compatibility still block 1.17.
Real synthesis, custom audio/consent and automatic crash recovery remain future work.
