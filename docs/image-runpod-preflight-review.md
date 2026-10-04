# Phase 5.4 — RunPod preflight review (কোনো deployment নয়)

২০২৬-১০-০১। Runtime imports/metadata, pip consistency, local snapshot headers ও
source review; official RunPod/NVIDIA/Python/safetensors references মিলিয়ে review।
কোনো model load, generation, tensor CUDA allocation, installation/download,
RunPod call/deploy বা paid resource নয়। Source/guards বদলানো হয়নি; শুধু handoff docs।

## যা যাচাই হয়েছে

- Local runtime: torch `2.14.0+cu130`, CUDA build `13.0`; diffusers `0.40.0`,
  transformers `5.16.1`, accelerate `1.14.0`, safetensors `0.8.0`, numpy `2.5.3`।
- `StableDiffusionXLPipeline` import PASS; `pip check` PASS। torchvision absent
  warning PIL fallback-এ import সফল; এটিকে blocker বা install requirement ধরা হয়নি।
- `torch.cuda.is_available()` false, `nvidia-smi` absent: স্থানীয়ভাবে GPU/driver/
  virtual-address compatibility পরীক্ষা করা সম্ভব হয়নি। CUDA-built torch থাকা
  মানেই usable GPU নয়।
- `safe_open` installed signature-এ keyword-only `backend` আছে। Loader সরাসরি
  `backend='pread'` ব্যবহার করে; arbitrary পুরোনো safetensors interchangeable নয়।
- Local 4 weight files, model index, scheduler/configs ও দুই tokenizer assets
  উপস্থিত। Header-only check-এ সব weights F32, inventory sizes মিলে। 13 GB model
  hash আবার পড়া বা load করা হয়নি। Weight files সব HF cache blob-এর symlinks।
- CUDA preparation source: device-only transfer, F32 VAE, FP16 denoisers,
  CPU mixed adapter bypass এবং matching generator/decode device যৌক্তিক;
  existing 152-test evidence reused। Actual GPU evidence এখনো নেই।

## Remaining blockers / spend-এর আগে যা resolve করতে হবে

### 1. 24 GiB virtual address guard

`child_probe` torch import/CUDA initialization-এর **আগে** `RLIMIT_AS` soft ও hard
24 GiB করে। এটি process virtual address-space limit; 24 GiB physical RAM বা VRAM
budget নয়। CUDA unified virtual addressing ও driver/allocator reservations-এর
জন্য RSS ছোট থাকলেও address-space ceiling allocation/initialization আটকাতে পারে।
অতএব এই cap-কে generic RunPod CUDA-compatible বলা যাবে না।

সীমা: NVIDIA-এর explicit 40-bit uncommitted reservation উদাহরণ older Maxwell/
আগের architecture-এর; সেটি দিয়ে আধুনিক RTX GPU-তে exact reservation বা সব
RunPod host-এ নিশ্চিত failure দাবি করা হচ্ছে না। Target GPU/driver-এ bounded
CUDA init/tiny allocation smoke অথবা GPU-specific memory-policy validation বাকি।
যদি policy পরিবর্তন লাগে, CPU AS limit রেখে GPU path-এ RSS/container/VRAM
controls বজায় রাখার নকশা করতে হবে; অন্ধভাবে unlimited/বড় arbitrary AS cap নয়।
এই review-এ কোনো guard শিথিল করা হয়নি।

### 2. Reproducible CUDA runtime selection

মূল requirements-এ model/GPU packages নেই; selected RunPod image digest ও tested
GPU dependency lock নেই। Local successful versions উপরের reference, deploy lock
নয়। RunPod official container matrix-এ CUDA 12.8/12.9/13.0/13.2 variants আছে;
যেকোনো template current environment-এর সমান নয়।

বর্তমান `cu130` build রাখতে NVIDIA driver family **580+** প্রয়োজন (normal CUDA
13.x compatibility; GPU architecture support-ও যাচাই করতে হবে)। Host selection
CUDA requirement দিয়ে মিলাতে হবে; অন্য CUDA/PyTorch build নিলে import/contract
compatibility আবার verify করতে হবে। safetensors pread API ও CLIP key migration
বিশেষভাবে preserve করতে হবে। Model installation owner করবেন; কিছু install হয়নি।

### 3. GPU-required preflight এবং allocated memory

বর্তমান `select_device()` CUDA unavailable হলে CPU নেয়—local fallback হিসেবে
সঠিক, কিন্তু paid GPU test-এ broken driver silently CPU run করতে পারে। CUDA
selection model load-এর পর হয়। First paid launch-এর entry/preflight-এ **CUDA
required, tiny allocation/synchronize pass, তারপর model load** gate দরকার।
বর্তমান source-এ এমন fail-fast paid-test gate নেই; সাধারণ CPU fallback বাদ দেওয়া
প্রয়োজন নয়। GPU availability check একা actual allocation success প্রমাণ করে না।

`/proc/meminfo` host MemAvailable মাপে, Pod cgroup allowance নয়। Selected Pod-এর
allocated RAM/cgroup limit+usage এবং free VRAM যাচাই করতে হবে; 8 GiB child RSS,
2 GiB host reserve ও 300s guards নিজে থেকে container/VRAM limit নয়। CPU loader
আগে সব components host RAM-এ রাখে, তাই GPU হলেও host pressure শূন্য নয়।

### 4. Remote snapshot preparation

`SDXL_TURBO_SNAPSHOT` override ঠিকভাবে child-এ যায়; absolute mounted path ব্যবহার
করতে হবে। Default `/home/arafat/...` remote-এ থাকবে ধরে নেওয়া যাবে না। Verified
**F32 Diffusers directory**-ই লাগবে—single-file checkpoint বা fp16 variant বর্তমান
loader contract নয়। সব configs/tokenizers ও weight blob targets-সহ copy করতে
হবে (symlink dereference অথবা cache blobs-সহ)। Remote checksum/size/headers
মেলাতে হবে। Offline guard থাকায় missing file স্বয়ংক্রিয় download হবে না।
এই turn কোনো model copy/upload/deployment হয়নি।

## সিদ্ধান্ত

READY নয়। Source preparation আছে, কিন্তু virtual-memory policy/target smoke,
reproducible CUDA image+dependencies, GPU-required/resource preflight এবং remote
snapshot availability resolve না করে প্রথম model GPU test-এ টাকা ব্যয় করা উচিত নয়।
এখানে safe target-specific guard replacement বেছে নেওয়ার evidence নেই; তাই
review-only scope-এ speculative code fix করা হয়নি। Phase 5.4 incomplete।

## Sources

- [Python resource: RLIMIT_AS / limits](https://docs.python.org/3/library/resource.html#resource.RLIMIT_AS)
- [NVIDIA unified addressing](https://docs.nvidia.com/cuda/cuda-driver-api/cuda_driver_api/group__CUDA__UNIFIED.html)
- [NVIDIA older reservation example—architecture-qualified](https://docs.nvidia.com/cuda/archive/11.0/cuda-c-programming-guide/index.html#device-memory)
- [NVIDIA CUDA driver compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)
- [RunPod official CUDA build matrix](https://github.com/runpod/containers/blob/main/official-templates/shared/versions.hcl)
- [RunPod CUDA host filtering](https://github.com/runpod/docs/blob/main/docs/sdks/graphql/manage-pods.mdx)
- [Safetensors backend API](https://github.com/huggingface/safetensors/blob/main/bindings/python/py_src/safetensors/__init__.pyi)
