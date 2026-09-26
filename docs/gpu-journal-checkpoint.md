# Durable mock journal checkpoint

2026-09-26: gpu_journal.py and test_gpu_journal.py added.

- Strict frozen versioned record rejects malformed data, unknown fields (including
  credentials), invalid IDs/timestamps and inconsistent recovery state.
- Atomic same-directory 0600 temporary write, file/directory fsync; persistent
  nonblocking flock serializes writers. Caller supplies a private local directory.
- Fresh arm cannot overwrite an existing session. I/O failures propagate; no
  cleanup mutation occurs before durable intent is saved.
- Explicit recover binds the exact mock backend ID, closes unfinished sessions
  even before their saved deadline and preserves original session timestamps.
- Crash after delete but before final save reconciles by inspecting first.
  Persisted attempts cap at three; absence with unknown storage requires manual
  review. Terminal outcomes do not repeat mutation or claim billing completion.

Checks: 93 journal/REST/controller tests PASS; targeted lint, plan drift and
whitespace checks PASS. Includes failed fsync/replace, lock contention, corrupt
records, identity mismatch, restart attempt cap and simulated post-delete crash.
A strict-version boolean regression and JSON tuple-validation interaction were
fixed; the final suite passed. No dependency installation or live cloud call.

Limits: Linux flock and local filesystem assumptions; caller must protect the
journal directory. No production admission wiring, autonomous process, scheduler,
retry delays or external supervisor. Recovery is explicitly invoked once per
cycle; structured authentication-error policy remains for runner integration.
A failure after atomic replace can leave the new record durable even though the
call raises; recovery must re-read it, never infer the previous state from errors.
The journal contains no secrets by schema; it is not an encrypted/tamper-proof store.

Next authorized mock micro-step: separate runner and parent-exit/restart tests.
Paid/live execution and full Phase 4 acceptance remain pending.
