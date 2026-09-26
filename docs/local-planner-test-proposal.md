# 3.9 — local planner isolated test proposal

2026-09-19: proposal complete; download/run was not authorized at proposal time.
2026-09-20: owner subsequently approved the isolated experiment and retry;
[result](local-planner-smoke-result.md): acquisition PASS, case A timeout, acceptance FAIL.
This document is the recovery checkpoint for 3.9, not a benchmark result.

## Selected experiment

Use official `Qwen/Qwen3-4B-GGUF`, only `Qwen3-4B-Q4_K_M.gguf`, with a pinned
CPU build of llama.cpp. This is a bounded candidate test, not a claim that this
model is best or already meets Bengali planning requirements.

Primary sources checked on 2026-09-19:
- [Official file](https://huggingface.co/Qwen/Qwen3-4B-GGUF/blob/main/Qwen3-4B-Q4_K_M.gguf): approximately 2.5 GB;
  SHA256 `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`.
  Download only this quantization, not the entire model repository.
- [Model license](https://huggingface.co/Qwen/Qwen3-4B-GGUF/blob/main/LICENSE): Apache-2.0.
- [Official model card](https://huggingface.co/Qwen/Qwen3-4B-GGUF): non-thinking
  sampling guidance. Proposed temperature .7, top-p .8, top-k 20, min-p 0,
  presence penalty 1.5; fixed seed 42, explicitly disable thinking via template.
- [llama.cpp license](https://github.com/ggml-org/llama.cpp/blob/master/LICENSE): MIT.
- [Grammar documentation](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md):
  supports a subset of JSON Schema through grammar conversion. Grammar alone
  does not establish cross-shot arithmetic, reference validity or story quality.

Retain license notices with downloaded assets. Before downloading, resolve the
model revision and runtime release/commit to immutable identifiers and record
URLs, byte sizes and checksums. The model checksum above must match; a changed
artifact requires review. No moving-latest installation or pipe-to-shell setup.
The runtime build/version is not selected yet: inspect official release metadata
and choose a CPU-compatible pinned build within the approval budget. If that is
unavailable, stop and report; no unbounded source/toolchain install.

## Observed local resources and proposed limits

Read-only checks: Intel i7-4790S, four cores/eight threads; 15 GiB total RAM,
about 10 GiB available; 2 GiB swap unused; about 98 GiB free on the target disk.
`llama-cli`, `ollama`, `cmake`, `nvidia-smi` were not on PATH; `g++` is available.
This is not a full inventory and does not prove GPU hardware is absent.
CPU-only execution avoids requiring GPU discovery or drivers.

- Destination: `/home/arafat/Developments/animation/data/planner-smoke/`.
  Existing `data/` ignore rule excludes models, runtime and raw results from Git.
- Model transfer: about 2.5 GB. Total download cap: 3.5 GB including runtime;
  stop if required setup exceeds the cap. Do not download a second model.
- Local disk budget: at most 6 GiB including temporary partial files and runtime.
- Four CPU threads; no GPU offload; one request at a time.
- Context cap 8192 tokens; output cap 3072 tokens per call. No silent truncation:
  reaching the cap is a failed case. No speculative or secondary model.
- Process RSS budget 8 GiB; stop if available RAM drops below 2 GiB or persistent
  swapping begins. Actual memory use has not been measured.
- Model-load timeout 180 seconds; each generation timeout 300 seconds; combined
  inference cap 30 minutes, maximum ten calls including repairs. Stop on the
  first smoke-case timeout/OOM instead of repeating a failing setup.
- Setup/download window up to 45 minutes, separately from the inference cap.
  These are stop limits, not speed estimates. Network speed is unmeasured.
- No billable cloud/GPU/API. Local electricity and network use still apply.

## Isolated procedure after explicit approval

1. Recheck RAM/free disk, pin the runtime and model metadata, then download within
   the stated caps and verify checksums. Keep an acquisition manifest.
2. Start only a local CPU runtime bound to `127.0.0.1` on an unused port; stop it
   after testing. Use synthetic text only, no personal assets or project DB.
3. Build a standalone harness under the ignored experiment directory. Reuse
   `PlannerRequest`, `StoryPlan`, `split_duration` and character injection as
   applicable; do not wire the production UI/API or replace MockPlanner.
4. Supply the StoryPlan schema and explicit field semantics. Ask for 6–10 shots,
   3–6 seconds each, matching the supplied duration schedule, declared character
   IDs, pending states, zero attempts and null errors/artifact paths.
5. First run case A. Validate JSON/schema and measure timing/RSS. If viable, run
   the remaining cases. At most one repair call per failed case, with specific
   validation feedback and unchanged request. No regex extraction, unchecked
   JSON repair, defaulting invalid semantic output or hard-coded successful plan.
6. Record first-pass vs repaired success separately. Preserve raw completion,
   validated JSON, error/truncation/timeout details, seed/config/version/checksum,
   input/output tokens if available, latency, tokens/sec and peak RSS.
7. Shut down the runtime. Report results and whether a 3.10 adapter is justified.
   Approval for this experiment alone does not authorize production integration.

## Five planned cases and acceptance

| Case | Synthetic input | Target/check |
| --- | --- | --- |
| A | A courier returns a lost notebook at a riverside market. | English, 30s; smoke case |
| B | বৃষ্টির পরে রিমা নদীর ধারে হারানো খাতা খুঁজে মালিককে ফেরত দেয়। | Bengali, 30s; coherent ordered actions |
| C | A child and a shopkeeper close a market stall before a storm. | 45s; supplied two-character IDs/visual traits, no unknown cast references |
| D | ভোরে একজন মালী বাগানের গাছগুলিতে জল দিয়ে কাজ শেষ করে। | Bengali, 60s; ten shots, correct duration sum |
| E | Exact repeat of case B with identical configuration. | Measure repeatability, not assumed byte-identical across runtimes |

Required: 5/5 valid StoryPlan outputs within at most one repair per case and the
resource caps; at least 4/5 valid first-pass outputs. Every shot 3–6s, 6–10 shots,
requested total within 1e-6, contiguous order, unique IDs and valid cast references.
No prose fences/thinking mixed into the JSON content. For supplied characters,
apply the existing injection once to base prompts and validate length again;
report model-produced text and deterministic postprocessing separately.

Semantic review: each case follows the supplied story, preserves names and cast,
has a beginning/action/ending, uses distinct relevant shot actions, and does not
invent incompatible visual traits. Bengali cases must preserve meaning and
Bengali narrative/dialogue rather than merely copying the input. Record each
criterion explicitly. Schema success alone does not pass the experiment.
A failed/slow case is evidence to report, not authorization to try larger models.

## Authorization and completion status

[Phase 3 step 3.9](plan/phase-3.md) requires:
“download/run করার আগে অনুমতি চাইবে”. [Rules](plan/rules.md) also require explicit
approval for model downloads larger than 2 GB. This proposed file exceeds that
threshold. Request approval for this exact CPU-only experiment, its 3.5 GB total
transfer cap and runtime setup. Wait for an explicit answer; do not infer it from
the earlier instruction to prepare this proposal.

3.9 is complete when this reviewable proposal is presented. The isolated test is
pending approval; 3.10 adapter is pending experiment evidence and authorization.
Phase 3 is not complete: provider lifecycle/metadata, planner repair/retry and
remaining real-adapter/gate requirements still need implementation/evidence.

Checks this turn: hardware/disk read-only inspection, official source verification,
local document links/status consistency, plan excerpt drift and whitespace checks.
No application code changed, so app tests were not rerun. No models/runtimes were
downloaded or executed; no performance or quality measurements are claimed.
