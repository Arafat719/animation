# Phase 4 local prerequisite — GPU health worker ও packaging source

2026-09-25। Owner-এর পরের কাজ শুরুর নির্দেশে local implementation সম্পন্ন;
**source/contract PASS; container build/pinned image artifact অসম্পূর্ণ।**

- [gpu_health.py](../animation_studio/workers/gpu_health.py): পৃথক authenticated
  /health, /devices, /capabilities। Env token required; configured log redaction।
- Fixed argument-array nvidia-smi query, subprocess timeout 5s; GPU UUID/name,
  VRAM MiB ও driver version validated। Missing/timeout/nonzero/malformed/empty
  probe unhealthy; stderr/exception details API-তে নেই।
- Health মানে driver-visible device discovery, CUDA kernel execution/inference
  readiness নয়। Capabilities operations empty; /jobs নেই। Mock worker অপরিবর্তিত।
- Query contract: [NVIDIA nvidia-smi documentation](https://docs.nvidia.com/deploy/nvidia-smi/)।
- [Dockerfile](../deploy/gpu-health/Dockerfile) recipe: non-root, loopback default,
  utility GPU driver capability, no model/PyTorch dependency। Approved container
  deployment-এ external mapping-এর জন্য explicit 0.0.0.0 override লাগবে; local
  run-এ default loopback। NVIDIA Container Toolkit/host driver integration required।
- [Minimal requirements](../deploy/gpu-health/requirements.txt): existing project
  pins-এর subset; নতুন version/install নয়। Python 3.12 Debian-compatible base চাই।
- [Packager](../scripts/package_gpu_health.py): explicit source allowlist, reproducible
  tar metadata, file SHA256 manifest; existing output overwrite নয়। Secret/assets/
  .git/unrelated files context-এ নেয় না। SHA256-pinned base reference ছাড়া reject;
  packaged Dockerfile-এ direct immutable FROM লেখা হয়। Build/pull/push করে না।

## ব্যবহার — verified base digest হাতে এলে

`python3 scripts/package_gpu_health.py --base-image VERIFIED_REPOSITORY@sha256:VERIFIED_DIGEST --output /tmp/gpu-health-context.tar`

এই example executable final command নয়: real digest এখনও নির্বাচিত/verified নয়।
Packager digest syntax যাচাই করে, registry provenance যাচাই করে না। Tests-এর
synthetic digest deploy করার জন্য নয়। Dependencies version-pinned হলেও wheel
hash/base verification ও completed build evidence ছাড়া reproducible image দাবি নয়।

## Checks ও blocker

- Health/package + পূর্বের GPU suites **231 PASS**, 2 existing dependency warnings।
  Auth/device fields/probe failures, deterministic context, input pin ও no-overwrite
  checks PASS। Ruff format/lint, plan drift/doc links/RESUME length/whitespace PASS।
- Actual local probe: devices=[], error_code=tool_missing। এটি expected unavailable
  evidence; real GPU success নয়। কোনো GPU model/inference চালানো হয়নি।
- Docker/Podman executables ও /var/run/docker.sock নেই। Container build/run,
  verified base digest, final image digest/size ও GPU-enabled smoke evidence নেই।
- Full app/media suite নয়; production API/UI/DB/schema অপরিবর্তিত। Unrelated work
  অক্ষত; install/download/paid action/commit নয়।
- পরের কাজ: local container builder ব্যবস্থা/verified base নির্বাচন, এই context
  build ও CPU no-GPU/auth smoke; তারপর immutable image evidence দিয়ে 4.7 update।
  Packaging source restart নয়। Builder environment দরকার; cloud launch নয়।
- 4.7 approval-ready নয়; paid approval/Phase 3 prerequisites আগের মতো বহাল।
