# Phase 5.4 — pure resource/deadline evaluator

2026-10-05। Owner next-work নির্দেশে [design](comfy-resource-guard-design.md)-এর
R1–R7 implementation সম্পন্ন; GPU প্রয়োজন হয়নি।

## পরিবর্তন

[Evaluator](../animation_studio/providers/comfy_resource_guard.py) existing
ComfySupervisionPolicy reuse করে strict resource sample যাচাই করে। Expected mock
context, worker ও device identity match; missing/invalid/stale telemetry fail-closed।
RAM/VRAM limit equality, host reserve equality ও run deadline equality-তে deny/abort।
Multiple reasons deterministic order-এ আসে; decision frozen, input অপরিবর্তিত।

এক start থেকে run/cleanup/final deadlines ও remaining run seconds হিসাব হয়।
NaN/inf/bool, reversed time, overflow এবং floating-point precision-এ reserve collapse
reject। Existing policy/context এবং copied sample পুনরায় validate হয়। Sample error
bounded telemetry reason; invalid caller argument ValueError। কোনো I/O/clock read,
GPU import, process launch, persistence বা executor wiring নেই।

## Checks

- আগে existing policy/schema baseline: 99 PASS।
- [নতুন tests](../tests/test_comfy_resource_guard.py): 72 cases, R1–R7 boundary,
  identity, malformed/copied inputs, multiple breaches, deadline/no-reset ও purity।
- `.venv/bin/python -m pytest -q tests/test_comfy_resource_guard.py
  tests/test_comfy_supervision.py tests/test_comfy_supervision_storage.py
  tests/test_comfy_v2_executor.py` (এক লাইনে): **223 PASS**।
- New source/tests Ruff lint ও format PASS; docs links, RESUME length,
  plan drift ও whitespace checks PASS। নতুন dependencies বা master requirements নেই।

## সীমা ও next

এই result সিদ্ধান্তমাত্র; telemetry সংগ্রহ বা hard memory/time enforcement নয়।
Allow model-fit proof নয়; abort নিজে process/remote compute থামায় না। Sample-এর
process-tree/device provenance ও same-clock continuity caller-এর দায়িত্ব। Persistence
schema অপরিবর্তিত; generation/cancellation/recovery integration এখনও unchanged।

পরের owner-directed একক micro-step: ছোট owned dummy-child supervisor এবং P1–P3
acceptance (hang/cooperative-stop failure, normal-exit race, disappearing sample)।
I1 durable executor integration পরে পৃথক step। এই turn শুধু pure evaluator;
পরের নির্দেশে dummy-child কাজ করা যাবে, live transport/real Comfy server নয়।
Real GPU image gate deferred; এই offline micro-step-এর blocker নেই।
