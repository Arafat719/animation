# Phase 5.4 — VAE RAM diagnostics

২০২৬-১০-০১। Owner-এর নির্দেশে শুধু diagnostics ও bounded experiments;
কোনো allocator/tiling/dtype/resolution fix, install/download বা limit পরিবর্তন হয়নি।

## পরিবর্তন

- `scripts/image_memory.py`: `/proc/self/status` থেকে RSS/HWM/anonymous/file-backed
  bytes; model roots ও parameter/buffer-এর weakref inventory; decoder এবং leaf
  operation-এর enter/exit hooks। Tensor copy/dump বা diagnostic strong ownership নেই।
- `scripts/image_inference.py`: mixed diagnostic run-এ release-এর আগে/পরে inventory।
- `scripts/image_load_probe.py`: memory ও allowlisted scalar JSONL persistence;
  সর্বোচ্চ 512 events (isolated decode-এ 237), পুরোনো guard বহাল।
  `decode-only` mode শুধু existing F32 VAE এবং zero latents চালায়।
- Synthetic tests: weakref দিয়ে retained parameter বনাম dead root শনাক্ত,
  hook cleanup on success/failure, scalar persistence, missing RSS, bounded events,
  isolated driver এবং inference release integration।

## Runs ও মাপ

প্রথম পূর্ণ-run readiness-এ available 10,670,039,040 bytes ছিল, 10 GiB threshold
না পেরোনোয় run হয়নি। Isolated test শেষে fresh readiness 11,358,375,936 bytes
ও প্রায় 90.7 GiB disk free থাকায় একটি পূর্ণ run হয়েছে। দুই run-এই offline,
দুই CPU threads, 300 wall/CPU seconds, 8 GiB sampled RSS, 24 GiB address-space,
2 GiB host reserve। কোনো retry নেই। Evidence নতুন ignored directories-এ।

| পরিমাপ | Isolated real VAE / zero latents | Full SDXL / real latents |
|---|---:|---:|
| Decode-এর আগে RSS | 1,079,672,832 B / 1.0055 GiB | 7,757,402,112 B / 7.2246 GiB |
| Decode চলাকালীন peak | sampled 2,108,907,520 B / 1.9641 GiB | observed boundary maximum 7,757,688,832 B / 7.2249 GiB; অসম্পূর্ণ |
| Decode return-এর পরে RSS | 1,102,381,056 B / 1.0267 GiB | পাওয়া যায়নি; child terminated |
| Output release-এর পরে RSS | 1,103,335,424 B / 1.0276 GiB | পাওয়া যায়নি |

Isolated decode সফল: finite `[1,3,512,512]` output, decode প্রায় 48.06s;
পুরো run 57.62s। এটি anime image acceptance নয়; zero input, PNG তৈরি করা হয়নি।
Kernel HWM 2,108,035,072 bytes; polling ও proc accounting approximate হওয়ায়
sampled peak থেকে সামান্য ভিন্ন।

### কোথায় বৃদ্ধি

Isolated run-এর সবচেয়ে বড় leaf-operation HWM বৃদ্ধি:
`decoder.up_blocks.2.upsamplers.0.conv` (তৃতীয় upsampler convolution)।
Enter RSS 1,572,016,128 bytes → exit 1,840,472,064 bytes;
operation-এর মধ্যে HWM বৃদ্ধি 536,018,944 bytes (~511.19 MiB)।
এর আগের দ্বিতীয় upsampler convolution-এ HWM বৃদ্ধি 267,825,152 bytes।
Installed `upsampling.py`-এ nearest interpolation-এর পরে convolution হয়।
তৃতীয় upsampler-এর F32 `[1,256,512,512]` input একাই 256 MiB;
input/output এবং convolution workspace-এর overlap peak বাড়াতে পারে।
Hooks একটি operation-এর peak interval শনাক্ত করে; native workspace-এর exact
allocation-by-allocation attribution দেয় না।

### কী বেঁচে ছিল

Full run-এ release-এর আগে:

| Model | Tracked parameter/buffer payload | Release-এর পরে |
|---|---:|---|
| UNet | 5,134,927,368 B (4.7823 GiB), 1680 tensors | root dead; tracked tensors 0 |
| Text encoder | 246,121,576 B, 197 tensors | root dead; tracked tensors 0 |
| Text encoder 2 | 1,389,320,296 B, 518 tensors | root dead; tracked tensors 0 |
| VAE | 334,615,452 B (319.11 MiB), 248 tensors | root alive; সব 248 tensors |

Latents মাত্র 32 KiB FP16 (decode input cast প্রায় 64 KiB F32)।
Release-এর আগে RSS 8,121,999,360 B; পরে 7,757,402,112 B: কমেছে মাত্র
364,597,248 B (~347.71 MiB), যদিও ~6.31 GiB denoiser tensor objects মারা গেছে।
অবশিষ্ট RSS-এর anonymous অংশ 7,437,742,080 B (6.9269 GiB), file-backed
319,655,936 B (0.2977 GiB)। তাই বড় অংশ resident checkpoint file mapping নয়।

### Full run-এর সীমা

UNet return 214.14 wall seconds / 293.94 CPU seconds; decode শুরুতে CPU 294.20s।
`decoder.mid_block.resnets.1.conv2` enter-এর পরে child `-24` (`SIGXCPU`)-এ বন্ধ।
Run 218.28s; process-wide sampled peak 7.7950 GiB **decode peak নয়** (আগের UNet)।
Supervisor-এর existing exit race result reason-এ `monitor_error:ValueError`
লিখেছে; raw return code ও persisted CPU timing CPU limit termination দেখায়।
এবার RSS guard ভাঙেনি; আগের attempt-4-এর RSS failure সরাসরি reproduce হয়নি।
কোনো successful full decode/PNG নেই; after-decode memory শূন্য দাবি করা যাবে না।

## সম্ভাব্য মূল কারণ ও সীমা

সবচেয়ে শক্তিশালী ব্যাখ্যা: loader/UNet execution-এর পরে CPU allocator/native
backend memory ধরে রাখছে; তার উপর VAE-এর high-resolution activations/workspace
যোগ হয়ে আগের run-এ 8 GiB guard ভেঙেছে। শুধু 319 MiB VAE weights কারণ নয়;
UNet/encoder Python roots বা tracked parameter objects-ও বেঁচে নেই।
Weakref মৃত্যু underlying সব storage/native cache মুক্ত হওয়ার প্রমাণ নয়;
allocator fragmentation, cached workspace এবং অন্য native storage-এর ভাগ এখনো
সরাসরি মাপা হয়নি। Isolated peak full pipeline-এ সরলভাবে যোগ করা যায় না,
কারণ retained allocations পুনর্ব্যবহার হতে পারে।

## Checks / next

Final relevant regression **138 PASS** (16.25s)। Ruff lint/format ও
plan excerpt drift যাচাই করা হয়েছে। Phase 5.4 incomplete, 5.5 শুরু হয়নি।
পরের প্রস্তাবিত diagnostic: retained allocator/native storage আলাদা করে পরীক্ষা
এবং inference-এর CPU budget থেকে আলাদা process-এ real latents decode মাপা;
এটি বর্তমান turn-এ বাস্তবায়ন বা retry করা হয়নি। Major fix owner নির্দেশের অপেক্ষায়।

Evidence:
- `data/image-inference-probe/vae-isolated-diagnostics/{events.jsonl,result.json}`
- `data/image-inference-probe/attempt-5-diagnostics/{events.jsonl,result.json}`

পুনরুৎপাদনের minimal command (fresh readiness ও নতুন output directory প্রয়োজন):
```python
from pathlib import Path
from scripts.image_load_probe import run_probe
run_probe(Path('data/image-inference-probe/NEW-DIRECTORY'), mode='decode-only')
```

## Owner-requested retry — attempt 6

Owner-এর “ok try again” নির্দেশে একই code/limits-এ একটি অতিরিক্ত full run।
Fresh available RAM 10,944,851,968 bytes (>10 GiB), disk check PASS।
Evidence: `data/image-inference-probe/attempt-6-diagnostics/` (206 events)।
UNet return 191.925 wall / 252.748 CPU seconds; release-এর পরে আগের মতোই
তিন denoiser root dead এবং tracked tensor count 0; VAE 248 tensors/319.11 MiB।
Decode-before RSS **7,757,582,336 bytes / 7.2248 GiB**।
Decode boundary maximum **8,160,702,464 bytes / 7.6003 GiB**, observed at
`decoder.up_blocks.2.resnets.0.nonlinearity` exit। এটি completed decode peak নয়।
Process-wide sampled peak 8,370,028,544 bytes / 7.7952 GiB (UNet-era HWM)।
শেষ event `decoder.up_blocks.2.resnets.2.conv2` enter; RSS 8,026,529,792 bytes,
CPU 297.402s। Child আবার SIGXCPU (-24); run 217.363s। Supervisor একই existing
exit-race reason `monitor_error:ValueError` রেখেছে। RSS guard এবারও ভাঙেনি।
After-decode RSS/PNG নেই; third upsampler convolution পর্যন্ত পৌঁছায়নি।
দ্বিতীয় run release-পরবর্তী RAM retention পুনরায় নিশ্চিত করেছে, কিন্তু exact
native allocation ownership বা complete full-decode peak এখনো অজানা।
No further retry/limit change/fix। Code unchanged; আগের 138-test PASS বহাল।
