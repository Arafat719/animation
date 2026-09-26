# Local builder readiness ও verified base checkpoint

2026-09-26। **Base manifest/context প্রস্তুত; container build/smoke অসম্পূর্ণ।**

- Sandbox-এর বাইরে unprivileged user namespace ও isolated tmpfs mount PASS।
  Existing subuid/subgid range: account `arafat:100000:65536` উপস্থিত।
- Docker/Podman/buildctl নেই; newuidmap/newgidmap নেই। `sudo -n true` ফল:
  `sudo: a password is required`। Automatic approval rejection নয়; OS privilege
  blocker। Security settings পরিবর্তন করা হয়নি। Free disk প্রায় 94 GiB।
- Ubuntu package metadata-এ podman candidate 4.9.3+ds1-1ubuntu0.2 এবং uidmap
  1:4.13+dfsg1-4ubuntu3.2 আছে। Owner terminal-এ `sudo apt install podman uidmap`
  সম্পন্ন করা প্রয়োজন; agent password পায় না, chat-এ password প্রয়োজন নেই।
- Rootless BuildKit বিকল্প যাচাই করা হয়েছিল; official GitHub release metadata API
  HTTP 403 rate-limit দিয়েছে। Binary download হয়নি। Standard rootless setup-এর
  UID helpers-ও নেই; privileges bypass করার চেষ্টা হয়নি।

## Verified metadata ও context

[Base record](../deploy/gpu-health/base-image.json): official Docker registry থেকে
python:3.12-slim-bookworm-এর linux/amd64 manifest bytes SHA256 ও registry header
মিলেছে। Immutable reference:

`docker.io/library/python@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a`

Compressed layers মোট 45,443,850 bytes (~43.34 MiB); layers এখনও download হয়নি।
Manifest integrity image run/compatibility/signature verification নয়। Public registry
bearer token transient ছিল; log/file-এ সংরক্ষণ হয়নি।

Allowlisted pinned context `/tmp/animation-gpu-health-pinned-context.tar`, 30,720 bytes:
SHA256 `5aeb77896190e5ec5bdcb3a4b6002737338e30fed8907f053dd99d5d2f6e6746`।
Embedded manifest-এর সব source file hashes PASS। Archive-এর digest final image
digest নয়। Source বদলালে context regenerate করতে হবে; /tmp স্থায়ী storage নয়।

## Resume

1. Owner tools install সম্পন্ন করলে `podman info` দিয়ে rootless builder যাচাই।
2. বর্তমান source থেকে নতুন context তৈরি; digest-pinned base দিয়ে local build।
   Base layers ~43.34 MiB plus pinned Python packages/cache; no model download।
3. Temporary token, loopback port-এ container auth/no-GPU health smoke; token ছাড়া
   401, no-GPU unhealthy, capabilities empty। Container stop/remove শেষে verify।
4. Image ID/size/digest ও build logs checkpoint; registry push নয়। তারপর 4.7 update।

এই checkpoint-এ source implementation বদলায়নি। Context hashes, document links,
plan drift/RESUME length/whitespace PASS; আগের 231 tests evidence retained।
No package install/image download/paid resource/commit। Build dependency owner input
অপেক্ষমাণ; completed source/contract কাজ restart নয়।

## Owner installation-এর পরে (2026-09-26)

Podman/newuidmap/newgidmap উপস্থিত; sandbox-এর বাইরে `podman info` rootless=true,
overlay PASS। Sandbox read-only runtime-dir error local execution-এ resolved।
Owner এখন থেকে সব software/package/dependency install নিজে করবেন। Docker recipe-তে
pip install থাকায় image build owner-কে দেওয়া হচ্ছে; agent install/build চালায়নি।
Current source-এর নতুন context: `/tmp/animation-gpu-build-2zjcc452/context`।
SHA256: `5aeb77896190e5ec5bdcb3a4b6002737338e30fed8907f053dd99d5d2f6e6746`।
Owner build command:

```bash
podman build -t localhost/animation-gpu-health:local /tmp/animation-gpu-build-2zjcc452/context
```

Base compressed download প্রায় 43.34 MiB plus Python packages; user-level Podman
storage-এ image থাকবে। Host Python packages পরিবর্তন নয়। Build শেষে agent image
inspect/auth/no-GPU smoke/cleanup করবে। Image build PASS এখনও দাবি নয়।

## Owner-built image ও smoke সম্পন্ন (2026-09-26)

উপরের build blocker resolved: owner image build করেছেন। Agent install/pull করেনি।
[Image evidence](../deploy/gpu-health/local-image-evidence.json):

- Local image ID: `45b4d841a9a333f8d3be70dba655d17c474e607ea930a1b4d6e8eeaae6a45cef`।
- Local manifest digest: `sha256:cf6d763e453be68cd78406731a860b862dad69f6cfd7c2f7ffa844322ce7516f`।
- Size: 144,892,683 bytes (~138.18 MiB); user 65532:65532।
- Exact image ID দিয়ে --pull=never, read-only, cap-drop=ALL, no-new-privileges,
  ephemeral host loopback port ও runtime-only test token-এ smoke PASS।
- /health,/devices,/capabilities-এ missing/wrong auth 401; authorized health false,
  devices empty/tool_missing; capabilities empty; /jobs 404।
- pip check PASS; container logs-এ test token অনুপস্থিত। Container removed এবং
  absence verified; image রেখে দেওয়া হয়েছে। Registry push হয়নি।
- Local manifest digest remote pullable registry reference নয়; publication ও
  remote GPU driver compatibility/real health এখনো বাকি।
- Docs/evidence consistency, excerpt drift ও whitespace PASS; source unchanged,
  আগের 231-test evidence retained। কোনো নতুন install/download/paid action নয়।
- পরের 4.7 prerequisite: image distribution plan ও live lifecycle/timeout controls
  প্রস্তুতি; তারপর final quote/approval preview। Paid launch অনুমোদিত নয়।
