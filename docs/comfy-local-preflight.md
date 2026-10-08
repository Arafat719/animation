# Phase 5.4 — local runtime prerequisite check

তারিখ: 2026-10-03। Owner-এর next-work নির্দেশে pending runtime preflight-এর
স্থানীয় prerequisites পরীক্ষা করা হয়েছে। ফল **BLOCKED**, runtime acceptance PASS নয়।

## Evidence

- Interpreter: `/home/arafat/Developments/animation/.venv/bin/python`, Python 3.12.3।
- `importlib.metadata.version('torch')`: `2.14.0`; `torch.version.cuda`: `13.0`।
  Distribution metadata-কে exact installed `+cu130` wheel identity verification
  বলা হচ্ছে না; আগের runtime pin অপরিবর্তিত।
- `torchvision`, `comfy-kitchen`, `comfy-aimdo`, `comfyui-frontend-package`:
  এই interpreter-এর distribution metadata-তে **NOT INSTALLED**।
- `importlib.util.find_spec('comfy')`: পাওয়া যায়নি।
- পরীক্ষিত path-গুলো অনুপস্থিত: `/workspace/ComfyUI`, `/workspace/sdxl-venv`,
  `/home/arafat/ComfyUI`, `/home/arafat/Developments/ComfyUI` এবং
  `/home/arafat/Developments/animation/ComfyUI`। এটি পুরো filesystem search নয়।
- `torch.cuda.is_available()`: `False`; `torch.cuda.device_count()`: `0`;
  `nvidia-smi` PATH-এ নেই।
- Inherited `RLIMIT_AS`: soft/hard উভয়ই unlimited (`-1`)।
- Read-only Python probe exit 0; model weights load হয়নি।

## Outcome ও next

বর্তমান environment-এ native ComfyUI import/server validation এবং tiny CUDA
allocation/operation চালানোর prerequisites নেই। Missing dependencies install
করার দায়িত্ব আগের owner নির্দেশ অনুযায়ী owner-এর। অন্য installed runtime থাকলে
তার interpreter ও ComfyUI checkout path দিয়ে পরবর্তী verification করতে হবে।
[Pinned installation recipe](comfy-runtime.md) বহাল; install/download, paid GPU,
server launch, heavy inference বা ImageProvider adapter implementation হয়নি।

পরের micro-step: owner-installed runtime-এর exact pin/native imports ও available
GPU-তে bounded tiny CUDA checks। এই pending verification existing scope-এর মধ্যে;
paid resource বা নতুন phase-এর অনুমোদন এতে অন্তর্ভুক্ত নয়। Phase 5.4 incomplete।

## 2026-10-04 prerequisite recheck

Owner next-work নির্দেশে সীমিত read-only metadata/path check পুনরায় করা হয়েছে।
একই .venv-এ torchvision/comfy-kitchen/comfy-aimdo/comfyui-frontend-package অনুপস্থিত;
উপরের পাঁচটি known checkout/interpreter path এখনও absent; nvidia-smi PATH-এ নেই।
Probe exit 0। এবার torch import/CUDA availability probe চালানো হয়নি; আগের CUDA
ফল historical evidence, নতুন GPU discovery claim নয়। Full filesystem search নয়।
Native preflight এখনও BLOCKED। অন্য installed interpreter/checkout location জানতে
owner-কে জিজ্ঞাসা করা হয়েছে; উত্তর pending। Install owner করবেন; model load হয়নি।

## 2026-10-05 prerequisite recheck

Project `.venv` metadata probe exit 0: torch 2.14.0 আছে; torchvision,
comfy-kitchen, comfy-aimdo ও comfyui-frontend-package এখনও NOT INSTALLED।
এবার `/home/arafat/Developments/animation/ComfyUI` পাওয়া গেছে; git HEAD pinned
`6b747c0428c343e1417219641db93a4fb7cb69ae`-এর সঙ্গে মেলে; checkout clean।
বাকি চার known path absent; nvidia-smi PATH-এ নেই। Checkout-এর file search-এ
pyvenv.cfg পাওয়া যায়নি; এটি alternate interpreter নেই এমন পূর্ণ প্রমাণ নয়।
Torch/CUDA/native imports, server বা model চালানো হয়নি। Native preflight এখনও
BLOCKED: owner-installed dependency interpreter path প্রয়োজন। Install owner-এর
দায়িত্ব বহাল; বিকল্প interpreter/checkout path জানতে চাওয়া হয়েছে।

## 2026-10-05 owner installation verification

Owner install completion জানানোর পরে project `.venv` দিয়ে verification:
- `python -m pip check`: No broken requirements found। Pip cache permission
  warning ছিল; dependency check সফল, install/change করা হয়নি।
- দুই lock-এর 107 package entry installed metadata version-এর সঙ্গে মেলে;
  mismatch 0। এটি installed wheel bytes/hash integrity verification নয়।
- torch `2.14.0+cu130`, torchvision `0.29.1+cu130`, comfy-kitchen `0.2.36`,
  comfy-aimdo `0.5.5`, frontend `1.53.6` উপস্থিত।
- torch, torchvision, comfy_kitchen, comfy_aimdo native package imports PASS;
  bounded probe (45s wall timeout / 30s CPU limit) exit 0, প্রায় 9.1s।
- torch CUDA build 13.0; CUDA available False, device count 0; nvidia-smi নেই।
  RLIMIT_AS soft/hard unlimited। GPU অনুপস্থিত বলে tiny CUDA operation চালানো হয়নি।
- ComfyUI HEAD pinned 6b747c0428c343e1417219641db93a4fb7cb69ae, checkout clean।

Dependency prerequisite এখন PASS; alternate interpreter আর প্রয়োজন নেই। Full
ComfyUI server/node import, object_info/prompt validation, CUDA ABI/kernel operation
এবং model inference এখনও অযাচাইকৃত। Server/model launch বা download হয়নি।
Next: available GPU environment-এ existing authorized bounded CUDA/native runtime
preflight; local GPU gate BLOCKED। Paid resource authorization বহালভাবে পৃথক।
