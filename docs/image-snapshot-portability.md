# Phase 5.4 — portable SDXL-Turbo F32 snapshot

2026-10-02। **REMOTE READY (copy source + verified manifest)**। Remote transfer
বা remote verification এখনো হয়নি; এই status GPU inference readiness নয়।

## কী যাচাই হয়েছে

- Model: `stabilityai/sdxl-turbo`, cached revision
  `71153311d3dbb46851df1931d3ca6e939de83304`। বর্তমান
  `SDXL_TURBO_SNAPSHOT` override নেই; probe-এর default নিচের cache path।
- 18টি runtime file, সব symlink; সব target উপস্থিত। দুই tokenizer-এর vocab ও
  merges একই blobs ব্যবহার করে। Snapshot directory একা symlink-preserving copy
  করলে `../../blobs` হারিয়ে যাবে। Source cache অপরিবর্তিত রাখা হয়েছে।
- পূর্ণ portable content: **13,878,864,870 bytes = 12.926 GiB (~13.879 GB)**।
  Regular-file copy-তে shared tokenizer files দুবার গণনা করা হয়েছে।
- Model index, scheduler, চার component config, দুই tokenizer-এর vocab/merges/
  special tokens/config এবং চার F32 safetensors weight উপস্থিত। Model index-এর
  optional image encoder/feature extractor null; আলাদা weights প্রয়োজন নেই।
- সব JSON parse, চার safetensors-এর bounded header/F32 dtype/tensor shape/
  contiguous offsets/file length যাচাই। চার weight-এর full SHA256 cache blob
  identity ও আগের inventory-এর hash-এর সঙ্গে মিলে গেছে। কোনো model load হয়নি।
- [SHA256 manifest](manifests/sdxl-turbo-71153311.sha256) সব 18টি file cover করে;
  [copy list](manifests/sdxl-turbo-71153311.files) শুধু এই complete runtime set নেয়।
  Cache-এর unrelated `.incomplete`/FP16/অন্য model files নেওয়া হবে না।

## ভবিষ্যৎ copy — এখন চালানো হয়নি

Repository root থেকে, owner-approved destination তৈরি হওয়ার পরে নিচের recipe।
`RUNPOD_SSH_TARGET` হবে owner-configured SSH alias; SSH port/key alias config-এ
থাকবে। নতুন/খালি destination ব্যবহার করুন; remote disk-এ অন্তত snapshot size,
তার বাইরে environment/output/installation headroom প্রয়োজন।

```sh
set -e
export SDXL_TURBO_SNAPSHOT="/home/arafat/.cache/huggingface/hub/models--stabilityai--sdxl-turbo/snapshots/71153311d3dbb46851df1931d3ca6e939de83304"
export RUNPOD_SSH_TARGET="your-configured-ssh-alias"
sha256_manifest="$PWD/docs/manifests/sdxl-turbo-71153311.sha256"
(cd "$SDXL_TURBO_SNAPSHOT" && sha256sum --check --strict "$sha256_manifest")
# Continue only if the preceding verification succeeds.
ssh "$RUNPOD_SSH_TARGET" 'mkdir -p /workspace/models/sdxl-turbo-71153311'
rsync -aL --files-from=docs/manifests/sdxl-turbo-71153311.files \
  "$SDXL_TURBO_SNAPSHOT/" \
  "$RUNPOD_SSH_TARGET:/workspace/models/sdxl-turbo-71153311/"
scp docs/manifests/sdxl-turbo-71153311.sha256 \
  "$RUNPOD_SSH_TARGET:/workspace/models/sdxl-turbo-71153311.sha256"
```

`-L` blob contents পাঠায়, symlink নয়। Local staging/archive/13 GiB duplicate নেই;
শুধু remote final copy লাগে। Rsync failure হলে inference নয়; copy আবার চালিয়ে
checksum verify করতে হবে। Cache cleanup/mutation copy চলাকালে করা যাবে না।
SHA manifest weights নয় এবং source paths/SSH credentials ধারণ করে না।

Remote shell-এ **যেকোনো model load-এর আগে**:

```sh
export SDXL_TURBO_SNAPSHOT=/workspace/models/sdxl-turbo-71153311
cd "$SDXL_TURBO_SNAPSHOT"
test -z "$(find . -type l -print)" &&
  sha256sum --check --strict ../sdxl-turbo-71153311.sha256
```

Exit status 0 এবং 18টি `OK` প্রয়োজন। Symlink থাকলে check fail করবে; missing বা
corrupt file-এ SHA check fail করবে। একই exported path থেকে পরের probe চালাতে হবে;
local `/home/arafat/...` fallback remote-এ ব্যবহারযোগ্য নয়।

## Checks ও সীমা

Standard `rsync`/`sha256sum` যথেষ্ট; নতুন custom transfer/loader code নেই। Tiny
fixture-এ external blob symlink dereference করে copy, source blob মুছে destination
স্বাধীনভাবে read/check, corruption ও missing-file rejection PASS। Full local
weights streaming hash করা হয়েছে; RAM-এ weights load বা generation নয়।
Model bytes duplicate/পরিবর্তন, download, deployment, remote contact হয়নি।

এটি complete **F32 Diffusers inference snapshot**, upstream repository-এর সব
variant/document-এর mirror নয়। Local README/license নেই; আগে যাচাইকৃত revision
license/card references [inventory](phase-5-model-inventory.md)-তে আছে। পাবলিক
redistribution package হিসেবে এই runtime set ঘোষণা করা হচ্ছে না।

পরের blocker: [locked CUDA runtime](image-cuda-runtime.md)-এর clean install ও
tiny CUDA operation/loaded-library/resource preflight; actual Pod RAM/VRAM,
driver, inherited RLIMIT_AS যাচাই। Remote copy checksum-ও destination-এ পাস করতে
হবে। Paid resource-এর explicit approval এখনো নেই; Phase 5.4 real image অসম্পূর্ণ।
