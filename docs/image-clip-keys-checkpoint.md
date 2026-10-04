# 5.4 — Legacy CLIP text encoder key compatibility

2026-09-29। Owner next-work instruction authorized schema diagnosis and focused
correction/tests. No full-model loading or inference in this step.

## Evidence

Read only bounded JSON headers from both local encoder safetensors files and
construct their configured models under init_empty_weights. Initial diagnostic
printed too many keys; follow-up summarized and asserted full correspondence.
First encoder: 196 keys match exactly after adding `text_model.` to current model
names; every shape and F32 dtype matches. Second encoder: 517 keys already match
exactly without transformation. No checkpoint tensors loaded for this comparison.
Diagnostic subprocesses used 45s alarm and 24 GiB address ceiling; initial peak
RSS 694,592 KiB. Installed Transformers conversion_mapping.py line 712 declares
CLIPTextModel PrefixChange(prefix_to_remove="text_model"). The current projection
class retains its text_model subtree. This explains attempt-4's first encoder
key validation failure without assuming checkpoint corruption.

## Change and verification

Loader first accepts exact native key correspondence. Otherwise only an exact
CLIPTextModel instance can use a complete, bijective `text_model.` prefix mapping.
All source keys must be accounted for; no mixed layouts, missing/extra keys,
implicit key dropping or checkpoint rewrite. Existing complete shape/F32
validation still precedes all tensor materialization. Other classes, including
the projection encoder, retain strict native keys. pread and resource limits unchanged.

93 relevant tests PASS: 19 streaming + 23 probe + 22 image + 29 workflow.
Eight added cases: legacy F16/F32 values and forward equality with native small
CLIP, source preservation, missing/extra/mixed/shape/dtype rejection before
materialization, and non-CLIP prefix rejection. Existing four-component roundtrip
also validates the native projection encoder. Ruff lint/format, plan drift,
whitespace, local doc links and RESUME length PASS.

## Limits and next

Full pipeline load and inference remain unproven. The correction does not accept
arbitrary checkpoint migrations or bypass schema validation. No install/download,
paid resource, model-file edit, commit or automatic retry.
Next proposed owner-directed micro-step: fresh memory preflight and one bounded
load-only attempt-5 in a new ignored directory, same limits; stop/report on
failure. Phase 5.4 real image acceptance remains incomplete; inference/5.5 not started.
