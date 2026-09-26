# Phase 2 / 2.9 composer errors and UI checkpoint

Date: 2026-09-16. **2.9 PASS** for the local fixed-sample composer application
boundary. Next bounded task: **2.10 full Phase 2 audit/regression gate**.

Added checked_export with safe Bengali failure codes/messages, storage headroom
preflight and runtime disk-full translation. Added a bounded fixed-sample ZIP API
and workspace UI with busy/error/retry/download states. No caller filesystem paths
accepted. Downloaded manifest omits absolute local paths. [Behavior/limits](composer-errors.md).

Verification:

- **385 backend tests PASS**, three existing warnings, 94.63 seconds; six new cases.
- Real missing/corrupt media, low-disk preflight and injected runtime OS/FFmpeg
  disk errors verified; no physical disk exhaustion performed.
- Safe API errors, lock release, busy response and real ZIP with all four bundle
  files PASS. No runtime database creation required by composer endpoint.
- Frontend lint/typecheck/build, both formatters and 17-schema drift PASS.
- Full existing browser regression plus composer error states, busy button, retry,
  successful real-API ZIP blob and navigation cleanup PASS; no browser exceptions.
- Browser missing/corrupt/disk failures used controlled HTTP responses; backend
  tests separately verify real translation. Browser evidence directory:
  `/tmp/animation-jobs-thmlt6`, temporary runner `/tmp/check_composer_ui.mjs`.

Backend command: `DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -o faulthandler_timeout=30`.
Browser command: `timeout 180s node /tmp/check_composer_ui.mjs`.
Approved local escalation used for established sandbox test/browser limitations.

Limits: per-process synchronous fixed-sample export, no durable job/cancel/recovery;
client navigation/timeout does not stop server encoding. Disk preflight is a minimum
heuristic, supplemented by runtime handling. Full arbitrary media upload/export UI
is not added. No model, real inference, personal voice or paid compute involved.
