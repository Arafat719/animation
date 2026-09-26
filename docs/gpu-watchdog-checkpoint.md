# Separate mock watchdog process checkpoint

2026-09-26: gpu_watchdog.py and subprocess tests added. Fixture only; constructs
MockLifecycle with unknown storage, never a RunPod REST/live client.

- CLI accepts a journal and optional --arm-record JSON fixture. Fresh run emits
  READY only after durable arm. Parent must own the sole stdin pipe writer;
  any input or EOF requests cleanup. Inherited writers can delay EOF detection.
- Saved UTC deadline becomes a monotonic deadline for that running process.
  Parent death, explicit completion/failure signal or deadline invokes recovery.
- Persistent runner flock excludes another runner throughout wait and recovery.
  Journal lock continues to serialize individual durable recovery operations.
- Existing journal startup recovers immediately, preserving deadline/attempts.
  Pending fixture failures have bounded 1s/2s retry delays and the journal's cap.
- Exit 0 means complete, 2 means manual cleanup required, 1 means runner error.
  Unknown storage is intentionally preserved, so normal fixture cleanup exits 2.
  Malformed journal/readiness failures print only a normalized error.

Checks: 99 watchdog/journal/REST/controller tests PASS; lint/format and docs checks
PASS. Real subprocess tests cover explicit signal, deadline with open parent pipe,
runner kill/restart, competing runner exclusion, corrupt input and actual parent
kill with an independently running child observing EOF. Tests clean up children;
no persistent service, cloud resource or dependency was installed.

Limits: this runner simulates compute in its own memory. It does not observe a
real external resource or preserve mock resource state across runner restart;
only session state/attempt history persist. REST-runner integration and structured
authentication-error policy remain pending. No production admission wiring or
external supervisor; local machine/network failure is not protected. Per-I/O vs
hard wall-clock cutoff remains unresolved for future HTTP integration. No paid
launch readiness or actual billing shutdown is claimed.

Next authorized local step: preserve provider error codes through cleanup/journal
and test authentication failures stopping retries before mock REST runner wiring.
