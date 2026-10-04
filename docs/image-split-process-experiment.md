# Phase 5.4 — পৃথক process-এ real-latent decode experiment

২০২৬-১০-০১। Owner একটিমাত্র experiment অনুমোদন দিয়েছেন: SDXL থেকে real latents
সংরক্ষণ, সেই process সম্পূর্ণ exit/reap, তারপর fresh VAE subprocess-এ decode।
এটি experiment harness; production provider/API/UI বা final architecture নয়।

## সীমিত পরিবর্তন

- `scripts/image_inference.py`: opt-in `latent_only`; finite real latents লিখেই
  return, decode নয়। Default existing inference behavior অপরিবর্তিত।
- `scripts/image_split_probe.py`: bounded non-pickle NPY + SHA256/provenance;
  generation child successful exit/reap হওয়ার পরেই decode child। Decoder একই
  scaling factor, F32 VAE, real latent values ও verified PNG/metadata ব্যবহার করে।
- `scripts/image_load_probe.py`: দুটি experimental mode; supervisor-parent RSS ও
  simultaneous parent+child RSS sampling। বিদ্যমান guard/cleanup পুনর্ব্যবহার।
- Relevant tests: latent roundtrip/tamper/type/shape/nonfinite rejection,
  failed generation-এ decode বন্ধ, latent-only branch decode না করা, synthetic
  VAE-তে real-latent handoff/scaling এবং output verification।

প্রতিটি child-এর আগের 8 GiB sampled RSS, 24 GiB address-space, 300 wall/CPU
seconds, 2 GiB available-host-memory reserve, offline guard ও দুই threads বহাল।
দুই child sequential; প্রত্যেকের নিজস্ব 300-second guard—এটি end-to-end 300s
promise নয়। No automatic retry, installation/download, paid resource বা major fix।

## একমাত্র real run

Command:
```
.venv/bin/python -m scripts.image_split_probe --output data/image-inference-probe/split-real-attempt-1
```

Preflight existing snapshot files উপস্থিত; available RAM 10,948,411,392 bytes,
free disk 97,474,621,440 bytes। Launcher-ও fresh >10 GiB memory এবং disk check
pass করেই generation শুরু করেছে। Seed 42, 512x512, এক step/guidance 0;
existing FP16 UNet/encoders, mixed F32 convolution compute।

**Result: experiment incomplete, generation failed `host_memory`।**
UNet চলাকালীন MemAvailable 2 GiB reserve-এর নিচে নামায় supervisor child kill/reap
করেছে। Guard-trigger sample-এর exact MemAvailable বর্তমান monitor persist করে না;
threshold-crossing reason আছে। অন্য host process-এর memory usage মাপা হয়নি।
এটি child-এর 8 GiB RSS-limit failure বা VAE decode failure নয়।

| মাপ | ফল |
|---|---:|
| SDXL generation child peak sampled RSS | 8,239,050,752 B / 7.6732 GiB |
| Supervisor parent peak sampled RSS | 19,357,696 B / 18.46 MiB |
| Simultaneous parent + child peak RSS | 8,258,408,448 B / 7.6912 GiB |
| Parent RSS after generation child exit | 19,361,792 B / 18.47 MiB |
| Generation elapsed / return code | 129.275s / -9 |
| Decode subprocess peak/before/after | পাওয়া যায়নি—subprocess শুরু হয়নি |
| Latents/image | কোনোটিই তৈরি হয়নি |

Final stage `unet_enter`; encoder 2 শেষ হয়েছে। Child reap-এর পরে returncode
recorded; decode directory অনুপস্থিত, latent file-ও অনুপস্থিত। `experiment.json`-এর
`parent_after_decode` এখানে function-end parent snapshot মাত্র: decode চলেনি,
এটি decode completion-এর প্রমাণ নয়। আগের successful isolated zero-latent decode
এই real-latent experiment-এর success হিসেবে ধরা হয়নি।

## সিদ্ধান্ত ও checks

এই run দিয়ে পৃথক process-এ **real** latents decode 8 GiB-এ সফল হবে কি না বলা
যায় না; decoder পর্যন্ত পৌঁছানো যায়নি। আগের native-memory-retention diagnosis
বহাল, কিন্তু প্রস্তাবিত process separation এখনো real end-to-end প্রমাণিত নয়।
একটিমাত্র experiment সীমা মেনে আর retry/limit change হয়নি।

145 relevant regression tests PASS (18.32s), পরে নতুন latent-only branch test
1 PASS (1.75s): মোট 146 distinct relevant tests। Ruff lint/format PASS।
Evidence: `data/image-inference-probe/split-real-attempt-1/experiment.json` এবং
`generation/{events.jsonl,result.json}`। Generated files ignored/uncommitted।

পরের সম্ভাব্য কাজ: owner নতুন attempt নির্দেশ দিলে বেশি available host RAM-এর
সময়ে এই একই experiment চালানো; guard কমানো নয়। Phase 5.4 incomplete।
