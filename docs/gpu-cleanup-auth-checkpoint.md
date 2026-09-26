# Cleanup authentication failure checkpoint

2026-09-26: lifecycle result and journal preserve normalized provider error codes
separately from existing operation failure labels. Raw error messages/bodies are
not persisted. Local simulated RuntimeError maps to unavailable.

401/403 normalize to unauthorized. Any cleanup operation observing unauthorized
ends that cycle immediately; the same controller retains the failure. Durable
journal outcome becomes needs_manual_cleanup, preventing retries across restart.
Transient stop failures still allow termination fallback and later inspection.
No automatic credential repair, rearming or clearing of an auth failure exists.

last_provider_codes is an optional additive version-1 field, default empty.
New reader accepts older v1 records without it; older readers reject new records
with the unknown field (forward compatibility is not claimed). Historical generic
errors cannot be retrospectively classified as authentication failures.

Checks: 110 relevant tests PASS, including 401/403 at all four request positions,
no subsequent requests on journal reload, direct controller repeated tick,
transient timeout/unavailable persistence, secret-body exclusion and old-v1 read.
Targeted lint/format, plan drift and whitespace checks PASS.

Limit: auth outcome persistence still requires successful disk writes. A crash
before saving that outcome leaves only durable attempt intent; later recovery
can attempt again within the existing three-cycle cap. No exactly-once guarantee.
Runner remains memory-mock only; next local micro-step wires mock REST transport
into the separate runner and exercises subprocess recovery. No live/paid calls,
new dependency installation or production admission changes.
