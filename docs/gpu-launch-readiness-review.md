# Launch readiness gap review

2026-09-26. Local evidence review only; prices/account state were not refreshed.
The 2026-09-25 pricing draft is historical, not an executable quote.

| Area | Evidence / current conclusion | Remaining work |
| --- | --- | --- |
| Worker image | Owner-built image, local no-GPU smoke and GHCR manifest identity passed | Provider-side private pull and NVIDIA compatibility unverified |
| Lifecycle protocol | Scoped inspect/stop/terminate mock REST tests passed | Live dispatch remains disabled; storage/billing observation absent |
| Recovery | Atomic journal, auth retry-stop, parent exit and restart tests passed | Local bounded mock supervisor now tested; external host supervision still pending |
| Watchdog | Separate process plus mock REST integration; 117 tests passed | Host power/network loss remains unprotected; external execution host not selected |
| Provisioning | No create implementation or account resource created | Exact payload/ID capture/ambiguous-create reconciliation or an explicitly manual provisioning path must be chosen |
| Cost | Existing estimator and historical preview only | Current account quote, region, credit/tax, full window and final budget needed |
| Scope gate | Phase 4.1–4.6 local/mock exception authorized | Real Phase 3 acceptance or explicit scoped plan revision still required before 4.8 |
| Inference | Health-only image has no inference capability | Separate model/runtime/artifact acceptance work; not part of first health proposal |

## Completed follow-up

[Bounded supervisor checkpoint](gpu-supervisor-checkpoint.md): 126 tests PASS.
Owner cannot confirm an existing server. [Attended health proposal](gpu-attended-health-proposal.md)
now records a manual/operator path for review; no repeat server question or mock
implementation. This does not authorize live launch or satisfy unattended protection.

## Original implementation scope (now completed)

Test bounded supervision of a hung mock cleanup runner. Existing HTTP timeouts
bound individual I/O phases, not total execution; the separate runner currently
has no outside process enforcing its cleanup window. This is the next concrete
local prerequisite, not a repetition of normal parent-exit/restart tests.

Use only local subprocess fixtures and the existing journal. A supervisor must
bound a cleanup attempt, terminate/reap a deliberately hung child, and report
unknown/manual cleanup unless an explicit later observation proves absence.
Restart must preserve durable attempts and must not create an unbounded restart
loop. No claim that killing the local runner stops remote compute. Acceptance:
hung-child timeout/reaping, no false complete, attempt preservation/restart bound,
and successful normal cleanup are tested without network calls or installs.
Implementation stays within the existing mock authorization.

## Decisions before live work (not requested yet)

After the bounded supervisor tests, choose an available always-on execution host
and operator fallback; a laptop-local mock cannot establish power/network-loss
protection. Confirm a live provisioning path, Phase 3/order scope, private registry
access and exact quote/configuration. Present one concrete action/cost preview
before any paid launch. Do not infer paid authorization from 'next work'.

No further broad readiness review is needed until evidence or scope changes.
Do not restart completed mock tests/features, CPU planner experiments or image
publication. No token creation, top-up, download or install is requested now.

Checks: compared Phase 4 requirements, launch draft, private-access and REST
watchdog checkpoints; stale draft claims corrected. Plan drift/whitespace and
local document links checked. Prior 117-test evidence retained; no source change.
