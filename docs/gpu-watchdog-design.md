# Mock shutdown watchdog and restart recovery design

2026-09-26 — design checkpoint within the authorized local/mock scope.
Existing plan requirements unchanged; no launch or live transport authorization.

## Problem and boundary

MockSessionController needs caller ticks. If that caller exits, cleanup does not
run. Its deadline uses a process-local monotonic clock and cannot simply be saved
and reused after reboot. The next implementation will exercise durable session
recovery with mock backends; it will not claim independent cloud shutdown.

## Durable session record (next implementation micro-step)

Use a small standalone versioned JSON journal outside source-controlled assets;
no application DB migration. Fields: schema_version, session_id, provider='runpod',
mode='mock', pod_id, created_at_utc, deadline_at_utc, cleanup_requested,
attempt_count, last_compute, last_storage and last_error_codes. Store only scoped
identifiers and normalized errors; never credentials, prompts or response bodies.
Strictly validate types, finite timestamps, deadline ordering, statuses and IDs.
Reject unknown fields/version and malformed records before contacting a backend.

Save via a restrictive same-directory temporary file, flush/fsync, atomic replace
and parent-directory fsync. Use a single-writer lock; lock contention must not
start a second cleanup owner. Filesystem failure blocks arming/admitting work.
Before any cleanup mutation, durably set cleanup_requested and increment attempts.
Once set, cleanup_requested never resets and the deadline is never extended.

Recovery binds the journal's exact Pod ID to the supplied mock backend, rejecting
mismatch before any request. On a process restart, every unfinished session is
closed to new work and reconciled immediately, even if its saved deadline is in
the future. This intentionally trades unused session time for simpler clock-safe
recovery. Monotonic time remains suitable only inside a running process.
A crash after DELETE but before saving results must cause inspection first on
restart; a 404 must avoid repeat mutations. Storage stays unknown, not cleared.
Compute absent with unknown/retained storage becomes a manual-review outcome,
not an endless mutation loop and not CleanupResult.complete.

## Independent runner (later separate micro-step)

A separate process will own the journal and cleanup controller. It must be ready
and have durably armed the resource before the parent can admit work. Parent exit,
explicit completion/failure or deadline triggers cleanup. A thread in the parent
is insufficient for parent-crash recovery. Test this first with subprocess-local
fixtures; do not enable RunPod live transport as a side effect.

Reconciliation is sequential, inspecting before each mutation cycle. Proposed
fixture policy: at most three cycles with delays of 1 and 2 seconds, persisted
attempt count, then needs_manual_cleanup. Authentication failures should stop
repeated attempts and record manual intervention. Unknown outcomes never reopen
work. Timeout remains per I/O; an external supervisor is needed to bound hung
runner execution and restart it from the journal without resetting attempts.
The existing controller's generic errors may need structured codes in that later
step; avoid silently treating every provider error as retryable.

## Limits before any paid launch

A separate local process cannot survive the owner's machine losing power/network.
A continuously available external supervisor and explicit operator recovery path
must be selected, tested and included in the final paid-action preview. No such
service is installed or provisioned by this design. No hard billing cap is claimed.
Provider storage status and actual billing verification remain separate work.

## Acceptance for the next micro-step

- Atomic journal roundtrip, invalid/corrupt/version/credential-field rejection.
- Write or lock failure prevents cleanup mutation/admission.
- Restart closes an unfinished session without extending its original deadline.
- Identity mismatch never contacts a backend.
- Simulated crash after successful deletion reconciles via GET without re-delete.
- Persisted attempts are not reset; unknown storage never reports full completion.

Checks for this design: compared with current lifecycle/controller and REST
checkpoint; plan excerpt drift and whitespace checks PASS. No source behavior
changed, so prior 77-test result retained and application tests not repeated.
Next: implement only durable mock session journal/restart recovery and its tests.
Local implementation already authorized; live/paid execution requires separate
approval and the remaining Phase 3/4 readiness prerequisites.
