# Mock REST watchdog integration checkpoint

2026-09-26: separate runner accepts --mock-rest-scenario with fixed fixture choices:
success, unauthorized, unavailable, ambiguous-delete, absent. Default memory-only
fixture remains supported. No URL/token/live transport argument or credential read.

RunPodLifecycle with mandatory MockTransport is wrapped by MockRESTLifecycle and
passed to the existing durable recovery loop. Adapter closes on runner exit.
The normal journal intent, three-attempt limit, 1s/2s waits, auth stop and unknown
storage outcome apply across the process boundary. All scenarios are simulated;
ambiguous-delete sets fixture absence before raising a simulated timeout.

Checks: 117 relevant tests PASS; lint/format/plan drift/whitespace PASS. Includes
REST subprocess completion, auth stopping at one attempt, 503 reaching three,
delete timeout followed by observed absence, already-absent fixture, terminal
restart preserving journal bytes and runner crash/restart. Existing actual-parent-
kill test now also runs with the REST fixture. No real HTTP requests occur.

Fixture resource state remains process-local, not a persistent external cloud.
Restart tests explicitly select an absent fixture to represent observed deletion;
they do not claim actual resource persistence. Paid GPU shutdown, external
supervision, hard total HTTP deadlines, real storage/billing verification and
production admission wiring remain unimplemented. No install/publication/paid call.

Next bounded local step: consolidate launch-readiness gaps against completed
mock evidence and choose the next necessary prerequisite. Do not repeat completed
mock implementations or assume this checkpoint authorizes live transport/launch.
