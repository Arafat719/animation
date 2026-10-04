# Phase 5.4 — CUDA-specific RLIMIT_AS policy

২০২৬-১০-০২। Owner শুধু AS policy + lightweight tests অনুমোদন দিয়েছেন। No deploy,
paid GPU, model load/generation বা real CUDA kernel test।

## Policy

- Default `--address-policy cpu`: আগের 24 GiB RLIMIT_AS soft+hard limit imports ও
  allocation-এর আগে বসে। Existing custom Limits.address_bytes-ও বহাল।
- Explicit `--address-policy cuda`: application RLIMIT_AS cap বসে না, ফলে CUDA
  initialization-এর আগে 24 GiB VA ceiling নেই। Inherited soft/hard AS limits
  দুটোই unlimited হতে হবে; finite থাকলে structured error, host limit কখনো বাড়ায় না।
- CUDA policy শুধুমাত্র infer/infer-mixed/latent-only/decode-real modes-এ বৈধ;
  load-only, operator ও synthetic CPU probes-এ cap bypass করা যায় না।
- CUDA child-এর CPU time/core/wall timer, offline audit এবং parent RSS/reserve
  monitoring আগের মতোই active থাকে। CUDA availability import/check এরপর হয়,
  model load-এর আগে। CUDA না থাকলে fail; এই disposable child-এ GPU requirement
  latch থাকে, পরে availability বদলালেও CPU fallback নয়।
- Default CPU policy-তে আগের auto device selection/fallback behavior অপরিবর্তিত;
  GPU run-এ নতুন CUDA policy flag দিতে হবে। GPU availability দেখে নিজে থেকে
  CPU AS guard বাদ দেওয়ার ঝুঁকি নেওয়া হয়নি।
- Supervisor result ও bounded child JSONL policy record করে। Split experiment
  একই নির্বাচিত policy দুই sequential child-এ দেয়।

অপরিবর্তিত: 8 GiB sampled host RSS, 2 GiB host reserve, 300 wall/CPU seconds,
24 GiB CPU AS default, offline network block, no retry, kill/wait এবং artifacts
verification। CUDA mode-এর RAM protection parent sampling-ভিত্তিক; hard allocation
ceiling নয়, তাই brief overshoot সম্ভব। এটি GPU VRAM cap/cgroup budget নয়।

## Files

- `scripts/image_load_probe.py`: policy validation/application, supervisor→child
  forwarding, CLI flag, result/event evidence ও guarded pre-model CUDA check।
- `scripts/image_device.py`: disposable CUDA-policy child-এর GPU-required latch;
  CUDA unavailable হলে error, default CPU fallback অক্ষত।
- `scripts/image_split_probe.py`: CLI/experiment থেকে উভয় child-এ policy forwarding।
- `tests/test_image_address_policy.py`: নতুন lightweight policy/guard tests।
- `tests/test_image_split_probe.py`: CPU/CUDA policy forwarding-এর parameter cases।
- RESUME/status, এই checkpoint এবং CUDA preparation command হালনাগাদ।

## Validation

CPU vs CUDA disposable-process tests বাস্তব RLIMIT_AS যাচাই করে; untouched
32 GiB private PROT_NONE virtual reservation CPU cap-এ rejected, CUDA policy-তে
accepted। কোনো 32 GiB physical RAM allocation নয়। প্রথম test default shared mmap
ব্যবহার করায় OS shared-mapping accounting-এ ব্যর্থ হয়েছিল; private reservation-এ
সংশোধিত। CUDA runtime availability mocked; GPU hardware ব্যবহার হয়নি।

Inherited finite limit refusal, invalid/mode-restricted policy, pre-runtime
availability failure, latched no-fallback, unchanged CPU/core/wall/offline guards,
CUDA-policy parent RSS/reserve kill/reap ও split forwarding covered। Final relevant regression
**167 PASS (14.78s)**; Ruff lint/format, plan drift/whitespace PASS। কোনো test skip বা guard শিথিল করা হয়নি।

## Usage / next blocker

Future authorized GPU inference:
```
SDXL_TURBO_SNAPSHOT=/absolute/path/to/verified-snapshot \
  .venv/bin/python -m scripts.image_load_probe --infer-mixed \
  --address-policy cuda --output data/image-inference-probe/NEW-DIRECTORY
```
Split experiment-এও `--address-policy cuda` flag। এই commands চালানো হয়নি।

Application-imposed 24 GiB CUDA initialization blocker resolved by policy;
external finite AS limit থাকলে environment blocker হিসেবে explicit error হবে।
Actual target GPU/driver test এখনো হয়নি। Next bounded blocker: pinned RunPod
CUDA/PyTorch/diffusers/safetensors runtime নির্বাচন, driver compatibility এবং
bounded CUDA allocation/synchronize preflight। Availability check একা actual
allocation proof নয়। Pod RAM/VRAM ও verified remote F32 snapshot-ও বাকি।
Phase 5.4 incomplete; নতুন phase/deployment/paid GPU authorization নয়।
