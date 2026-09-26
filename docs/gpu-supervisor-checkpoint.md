# Bounded mock cleanup supervision checkpoint

2026-09-26: gpu_supervisor.py supervises one explicitly requested recovery child
for an already-armed journal. Fixed mock scenarios only; no live provider inputs.
The watchdog's new hang fixture blocks after durable recovery intent is written.

- Finite positive timeout bounds child startup/execution. Timeout kills and reaps
  that exact child, returns needs_manual_cleanup, and never claims remote deletion.
- No automatic restart loop. Later explicit calls preserve original deadline and
  attempt count. Three durable cleanup attempts or saved auth failure prevent
  another child launch. Timeout before intent is saved consumes no journal attempt;
  callers must not add an unbounded external restart loop.
- Independent supervisor flock serializes supervisor calls. Existing runner and
  journal locks remain in place. Normal exit is checked against the saved record.
- Timeout leaves compute unknown until a subsequent explicit observation resolves
  it; unknown storage continues to require manual cleanup.

Checks: 126 relevant tests PASS; lint/format and docs checks PASS. Includes hung
child kill/reap, three explicit restarts and no fourth child, later absent fixture
observation, normal cleanup, authentication terminal state and invalid deadlines.
Prior REST watchdog, parent-kill and durable recovery tests included.

Limits: callable local supervisor, not an installed always-on service. It covers
only its own fixture child, which spawns no descendants; parent/supervisor machine
failure remains unprotected. SIGKILL reaping has an additional 5-second wait;
kernel-uninterruptible I/O is not a guaranteed hard wall-clock bound. No real GPU
or billable resource is stopped by killing this process. Mock resource state is
process-local. No live transport, installation, account change or paid call.

Next requires environment information, not another broad mock readiness review:
owner asked whether an existing always-on VPS/server is available. Select a
concrete external execution/operator fallback path based on that answer before
live integration. No new server rental requested or authorized. Phase3/order,
private provider pull and exact paid launch preview remain pending separately.
