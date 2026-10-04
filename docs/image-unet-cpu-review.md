# 5.4 — Read-only UNet CPU execution review

2026-09-30। Owner next-work instruction authorized review only. No model loading,
inference, tensor benchmark, dependency install or source change performed.

## Local findings

- lscpu: Intel Core i7-4790S, 4 physical cores / 8 logical CPUs. Current process
  affinity covers CPUs 0–7; harness deliberately uses 2 intra-op/1 inter-op threads.
- Installed torch 2.14.0+cu130 reports AVX2/FMA3/F16C true; AVX512 FP16/BF16,
  AVX512 F, AMX FP16/BF16 false. MKLDNN available/enabled. These capabilities
  do not establish which kernel executed or its performance in attempt-2.
- Current editor cgroup memory.max is max; cpu.max was absent at its leaf path.
  Ancestor quotas were not established; affinity does not prove unrestricted CPU
  throughput. Current observations cannot reconstruct attempt-2 scheduling.
- Existing UNet config has 320/640/1280 channels, two resnets per down block,
  transformer depth 1/2/10, three down and up blocks and a cross-attention mid
  block. At the fixed 512x512 profile the input latent is 64x64 with 4 channels.
- Installed UNet forward runs embeddings then conv_in, down blocks, mid block,
  up blocks and conv_out. ResnetBlock2D uses 3x3 convolutions. Attention's default
  source selects AttnProcessor2_0 when scaled_dot_product_attention is available;
  that processor has Q/K/V linear projections and SDPA. The exact runtime CPU
  SDPA/convolution backend was not captured, so no Flash/oneDNN kernel claim.
- Loader constructs modules on meta, then installs owned CPU FP16 UNet/encoder
  tensors; VAE stays F32. No explicit channels-last conversion, compilation or
  attention-processor override is present in this path.

Sources inspected locally: scripts/image_stream_load.py; installed Diffusers
models/unets/unet_2d_condition.py, models/resnet.py and
models/attention_processor.py; cached snapshot unet/config.json; lscpu and
bounded torch.cpu.get_capabilities() import query. Initial JSON serialization
of the capability mappingproxy failed; converting it to dict returned results.
No model operation was involved.

## Decision

Attempt-2 proves both encoders finish and UNet does not return before timeout;
it does not identify a slow operator. Reduced-precision kernel efficiency is a
candidate to measure given these capabilities, not a proven root cause. Tiny
previous dtype probes cannot establish performance at UNet-like shapes.

Full F32 UNet is not a safe speculative switch under the existing RSS limit:
its inventoried payload alone is 10,269,854,736 bytes (~9.56 GiB), exceeding 8 GiB
before encoders/runtime/activations. BF16 speed/quality and channels-last benefit
are unmeasured; extra threads or a longer timeout are likewise not justified yet.

## Concrete next proposed micro-step

Build/test/run an isolated synthetic operator probe, without checkpoint reads:
3x3 convolution on (1,320,64,64) with 320 output channels, and linear projection
on (1,256,1280) to 1280. Compare F32/FP16/BF16 on identical seeded inputs/weights,
two intra-op threads and inference_mode. Record first-call and bounded warmed
latencies separately, process CPU time, finite output and numerical differences
against F32; rotate dtype order to expose ordering bias. Do not claim end-to-end
speed or image quality from these synthetic measurements.

Proposed guard budget: at most 6 isolated cases (2 operators x 3 dtypes), each
20s wall/CPU including import, 8 GiB address space, sampled 2 GiB RSS, 2 GiB host
reserve; aggregate maximum 120s, no retries. Bound warm repeats to two. Save
partial case evidence on timeout and stop the experiment on guard/runtime
failure. Test the supervisor with stubs before running cases. No full UNet,
planner model, download, install or change to the existing inference profile.
Results would guide one later optimization or narrower diagnostic proposal.
This review has not executed that proposed benchmark.

## Checks/status

Capability query and source/config review complete; prior 109 tests reused for
unchanged source. Documentation links, plan drift, whitespace and RESUME length
PASS. Real image acceptance 5.4 remains incomplete; 5.5 not started.
