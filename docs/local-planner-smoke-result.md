# Approved local planner smoke test — result

2026-09-20. **Experiment executed; acceptance FAIL (case A timed out).**
3.10 adapter has not been started. This is not a successful real planner gate.

## Authorization and acquisition

Owner approved the concrete [3.9 proposal](local-planner-test-proposal.md) by
instructing the next step, then explicitly requested another attempt on Sep 20.
The Sep 19 setup stopped within its 45-minute download window with 37,229,648
bytes missing. Network read timeout and a short range response required resuming
saved ranges; an automatic approval review timeout succeeded on its allowed retry.
The Sep 20 retry downloaded only the missing bytes, not another full model.

Pinned assets:
- Model revision `bc640142c66e1fdd12af0bd68f40445458f3869b`, official
  [Qwen3-4B-Q4_K_M.gguf](https://huggingface.co/Qwen/Qwen3-4B-GGUF/blob/bc640142c66e1fdd12af0bd68f40445458f3869b/Qwen3-4B-Q4_K_M.gguf).
  2,497,280,256 bytes; whole-file SHA256 PASS:
  `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`.
- CPU runtime [llama.cpp b10964](https://github.com/ggml-org/llama.cpp/releases/tag/b10964),
  `llama-b10964-bin-ubuntu-x64.tar.gz`, 16,825,086 bytes.
  Archive SHA256 PASS:
  `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`.
  Executable reports `0.4.1-dev`, build 10964, commit `b29c606e2`.
- Asset payload total 2,514,105,342 bytes, plus small metadata/license files.
  No whole-file duplicate download. Interrupted reads can add small transport
  overhead; actual network-interface byte totals were not measured. Download
  scope remained inside the 3.5 GB cap, and directory usage was about 2.4 GiB,
  below the 6 GiB disk cap. Apache-2.0 model and MIT runtime notices retained.

All runtime/models/raw results and standalone harness are under ignored
`data/planner-smoke/`. They are not committed. Production app/database untouched.

## Actual test configuration

Intel i7-4790S; CPU only, four generation and batch threads, zero GPU layers,
no operation offload, one slot, 8192-token context. Localhost-only server with
explicit ephemeral port; closed after the test. Non-thinking template setting,
seed 42, temperature .7, top-p .8, top-k 20, min-p 0, presence penalty 1.5,
3072-token output cap. Full StoryPlan schema supplied both in instructions and
JSON-schema response format. Expected six five-second shots for case A.

Prompt: “A courier returns a lost notebook at a riverside market.”
One generation call was made. No repair, Bengali cases, cast case or repeatability
case was run because the proposal requires stopping after a smoke-case timeout.

| Measurement | Observed |
| --- | --- |
| Model health/load ready | 5.55 seconds |
| Case A elapsed | 300.02 seconds; timeout |
| Total runtime lifecycle | 306.30 seconds |
| Peak sampled process RSS | 5,483,256 KiB = about 5.23 GiB |
| Minimum available system RAM | 8,705,916 KiB = about 8.30 GiB |
| Resource stop / persistent swapping | None detected |
| Last logged generation speed | 2.08 tokens/sec, n_gen=220 at 303.69s runtime elapsed |
| Received content | 797 characters, 225 streaming events; incomplete first shot |
| Completed validated plans | 0 |
| Calls attempted / planned cases | 1 / 5 |

Generation speed is the runtime's logged decode metric, not end-to-end tokens/sec.
The stream ended before final token usage/timings, so exact total token counts
and prompt-evaluation latency are unavailable. The output starts with plausible
metadata and cast but stops inside the first shot's action string. It is invalid
JSON. No semantic-quality, Bengali-capability or repeatability PASS is claimed.
The observations show this full-schema configuration misses the 300-second
budget on this CPU; they do not prove every configuration of the model is too slow.

## Verification and recovery

- Exact model byte size and SHA256 PASS; runtime checksum/version PASS.
- Standalone harness Python compile check PASS before execution.
- Timeout guard stopped further calls; incomplete JSON explicitly rejected by
  StoryPlan validation; no validated-output file or production plan was saved.
- Runtime exited with return code 0 after termination; localhost port closure
  independently verified. No server remains from this test.
- Local doc links, RESUME size, generated plan drift and whitespace checks PASS.
- No app tests rerun: no production source changed in this experiment.

Raw evidence: `acquisition.json`, `range-progress.json`, `retry-authorization.json`,
`runtime-command.json`, `server.log`, `metrics.json`, `results.json`, and
`A-1-request.json`, `A-1-events.json`, `A-1-content.txt`, `A-1-result.json` in the
ignored experiment directory. `run_smoke.py` is the isolated harness. Preserve
these and the verified model; do not blindly rerun or redownload on resume.

The runtime warns that the template thinking flag is deprecated; a future pinned
run can use its supported reasoning-off flag. This warning did not stop loading.
The runtime also warns about default unauthenticated CORS despite loopback bind;
future runtime setup should constrain origins/auth. No service remains running.

## Next bounded work

The [revised compact proposal](local-planner-compact-test-proposal.md) is now complete
and its subsequently approved one-call test has finished: [compact result](local-planner-compact-test-result.md),
strict validation PASS, semantic acceptance FAIL.
The proposal uses the already verified model: reduce schema
prompt overhead and generate a compact content-only draft, then deterministically
assemble/validate StoryPlan fields and durations. Compare measured prompt/decode
cost before deciding whether to change timeout or model. This is a proposal,
not a claim the optimization works. Do not run a larger/longer experiment or
start 3.10 without the required authorization. Current mock flow stays available;
Phase 3 and its real-adapter acceptance gate remain incomplete.
