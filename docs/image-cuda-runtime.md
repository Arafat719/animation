# Phase 5.4: প্রথম RunPod CUDA runtime

তারিখ: 2026-10-02। শুধু dependency নির্বাচন/lock; deployment অনুমোদন নয়।
Inference architecture, CPU fallback ও safety guards অপরিবর্তিত।

## নির্ধারিত environment

| অংশ | নির্বাচিত সংস্করণ |
| --- | --- |
| OS / architecture | Ubuntu 24.04, Linux amd64 |
| Python | CPython 3.12, isolated venv; local reference 3.12.3 |
| RunPod base tag | `runpod/base:1.0.7-cuda1300-ubuntu2404` |
| Immutable image | `runpod/base@sha256:5056a1432409049b116029f2ed8526ea7fc0f041dbee2173ecb44a65d9a8035e` |
| Base system CUDA | 13.0.0 |
| PyTorch | `2.14.0+cu130` |
| Wheel CUDA toolkit metapackage | `cuda-toolkit==13.0.3.0` (13.0 Update 3) |
| Wheel CUDA runtime / cuDNN | `nvidia-cuda-runtime==13.0.96` / `nvidia-cudnn-cu13==9.24.0.43` |
| Host NVIDIA Linux driver | এই test-এর নির্বাচিত minimum **580.126.20**, অথবা নতুন compatible driver |
| diffusers / transformers | `0.40.0` / `5.16.1` |
| accelerate / safetensors | `1.14.0` / `0.8.0` |

বর্তমান torch রাখা উপযুক্ত: [official cu130 index](https://download.pytorch.org/whl/cu130/torch/)
এ exact CPython 3.12 manylinux_2_28 x86_64 wheel আছে। Upgrade/downgrade প্রয়োজনের
প্রমাণ নেই। CUDA 12.x stock PyTorch template-এর packages মেশানো যাবে না;
[RunPod base](https://github.com/runpod/containers/blob/main/official-templates/base/README.md)
থেকে আলাদা Python 3.12 venv ব্যবহার করতে হবে (base-এর default Python নয়)।
Registry manifest/config read করে উপরের digest, Linux amd64 ও CUDA 13.0.0 যাচাই হয়েছে;
image pull/run হয়নি। Digest interpreter patch-সহ image contents স্থির রাখে।

[NVIDIA 13.0.3 release notes](https://docs.nvidia.com/cuda/archive/13.0.3/cuda-toolkit-release-notes/index.html)
অনুযায়ী 13.0 Update 3-এর corresponding Linux driver 580.126.20। CUDA 13.x-এর
[minor compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)
family floor 580; প্রথম পরীক্ষায় উপরের আরও নির্দিষ্ট minimum অনুসরণ করব।
Host driver container install দিয়ে বদলায় না; Pod host-এ যাচাই করতে হবে।
`nvidia-smi`-এর CUDA field installed wheel runtime নয়। Base-এর toolkit 13.0.0;
torch-এর bundled runtime 13.0.96; custom CUDA compilation এই test-এর অংশ নয়।
Lock বর্তমান metadata-compatible auxiliary `cuda-bindings==13.3.1` ও
`nvidia-nvjitlink==13.3.33`-ও রাখে; সব CUDA component-এর version 13.0.3 নয়।
Minor compatibility-র feature/PTX সীমা থাকায় বাস্তব GPU allocation/operation gate
পাস না করা পর্যন্ত hardware compatibility verified বলা যাবে না।

## Lock ও installation boundary

[requirements-sdxl-cu130.lock](../requirements-sdxl-cu130.lock)-এ 62 package-এর
exact version এবং নির্বাচিত CPython 3.12/Linux wheel SHA256 আছে। Torch-এর direct
official wheel URL; অন্যগুলোর PyPI wheel hash। CUDA toolkit extras-সহ 95 active
dependency constraints offline metadata validation-এ PASS। Backend requirements
এই inference environment-এ মেশানো হয়নি। নতুন package version নির্বাচন করা হয়নি।

Owner ভবিষ্যতে installation করবেন; নিচের commands এই review-তে চালানো হয়নি:

```sh
python3.12 -m venv /workspace/sdxl-venv
/workspace/sdxl-venv/bin/python -m pip install -r requirements-sdxl-cu130.lock
/workspace/sdxl-venv/bin/python -m pip check
```

`--system-site-packages` নয়; stock torch/torchvision/xformers মেশানো নয়।
Base-এর `LD_LIBRARY_PATH`-এ `/usr/local/cuda/lib64` আছে: preflight-এ wheel libraries
লোড হচ্ছে যাচাই করতে হবে; system CUDA path দিয়ে wheel libraries override হলে
সেই CUDA entry সরাতে হবে, host NVIDIA driver library paths রাখতে হবে।
সম্পূর্ণ environment-এর install/pull size ও disk budget owner-এর installation-এর
আগে যাচাই বাকি। এখানে binary wheel/model/image download করা হয়নি।

## safetensors এবং যাচাইয়ের সীমা

[`safetensors` 0.8.0 release](https://github.com/safetensors/safetensors/releases/tag/v0.8.0)
থেকে `safe_open(..., backend="pread")` সমর্থিত। Diffusers 0.40.0 এবং transformers
5.16.1 দুটিই metadata-তে safetensors >=0.8 চায়; পুরোনো pin নিরাপদ নয়।
Local 0.8.0-এ 84-byte F32 fixture `[1, 2, 3]` দিয়ে `get_tensor` ও `get_slice`
দুটির pread read PASS। Local pipeline imports PASS; কোনো model load হয়নি।

Public index/PyPI metadata ও wheel hashes যাচাই হয়েছে; clean locked install হয়নি।
Torch wheel-এর PEP 658 sidecar HTTP 403 দিয়েছে: dependency validation-এ installed
2.14.0 metadata ও PyPI 2.14.0 metadata ব্যবহৃত, cu130 binary metadata পুনরায়
extract করা হয়নি। তাই resolver/install এবং real CUDA compatibility এখনো remote
preflight acceptance-এর অংশ; metadata PASS-কে GPU PASS বলা হচ্ছে না।

## পরের blocker

নির্বাচিত host-এ model ছাড়াই tiny CUDA allocation/operation+synchronize gate:
driver, actual loaded CUDA libraries, CUDA-required behavior, unlimited inherited
RLIMIT_AS, Pod RAM/VRAM এবং 2 GiB reserve যাচাই। Existing explicit
`--address-policy cuda` প্রয়োজন; default CPU policy 24 GiB AS cap রাখে।
এরপর remote full F32 snapshot-এর `SDXL_TURBO_SNAPSHOT` path/symlink targets/content
যাচাই বাকি। Paid launch ও heavy inference এখনো অনুমোদিত/সম্পন্ন নয়।
