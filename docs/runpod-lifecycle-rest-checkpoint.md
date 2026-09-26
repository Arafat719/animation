# RunPod lifecycle REST mock checkpoint

2026-09-26: single-Pod inspect/stop/terminate adapter implemented with mandatory
httpx.MockTransport. No real cloud call, dependency install or credential read.

- GET validates identity and desiredStatus; 404 records absence only.
- POST stop accepts 200; DELETE accepts 204. Acknowledgement is not verified
  shutdown. Subsequent inspection remains explicit; storage/billing unknown.
- No automatic retries, redirects, provisioning or live transport. Timeout and
  transport errors report an unknown outcome without echoing remote response text.
- Desired status is not actual compute state. Adapter deliberately does not map
  observations to ResourceState or claim CleanupResult.complete.
- MockSessionController now accepts the mock REST bridge; an independent
  watchdog and persistent restart recovery are still pending. Per-I/O timeout is not a total deadline.

Protocol references: [stop](https://docs.runpod.io/api-reference/pods/POST/pods/podId/stop),
[delete](https://docs.runpod.io/api-reference/pods/DELETE/pods/podId).

Checks: new REST and existing mock lifecycle tests 67 PASS; targeted ruff PASS.
Initial combined run reached unchanged RunPod TestClient tests and stalled in the
sandbox; interrupted, then ran the two relevant pure-mock suites successfully.
No claim that the interrupted combined suite passed. Prior provider evidence retained.

## Cleanup integration follow-up (2026-09-26)

MockRESTLifecycle bridges the scoped adapter to MockSessionController. Presence
maps to unknown compute regardless of desiredStatus; 404 maps to absent, storage
always unknown. No REST observation can claim complete billing cleanup.
Provider errors are recorded; termination fallback follows stop failure. A later
caller tick re-inspects before repeating mutations, including ambiguous timeouts.
Wrong resource IDs fail before HTTP. Existing mock-only transport gate retained.

REST/cleanup/controller tests: 77 PASS; targeted lint and docs checks PASS.
No dependencies installed, live cloud calls or secrets read. This is cooperative
in-process recovery, not autonomous shutdown or restart-persistent recovery.
Watchdog/recovery design now recorded in [design](gpu-watchdog-design.md).
Next: durable mock journal/restart recovery implementation; live/paid execution
remains unauthorized.
