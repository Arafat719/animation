# 5.1 — Local model inventory

2026-09-28। Owner-approved scoped exception; read-only inspection, কোনো model run নয়।

## পরিচয় ও উপস্থিতি

Existing Hugging Face cache-এ `stabilityai/sdxl-turbo` পাওয়া গেছে। Snapshot:
`/home/arafat/.cache/huggingface/hub/models--stabilityai--sdxl-turbo/snapshots/71153311d3dbb46851df1931d3ca6e939de83304`।
এটি আগে বলা প্রায় 13 GB asset-এর সম্ভাব্য মিল; পুরোনো exact identity না থাকায়
একই asset বলে নিশ্চিত করা নয়। Snapshot total 13,878,864,870 bytes (~12.93 GiB)।
একক `sd_xl_turbo_1.0.safetensors` নেই; এটি Diffusers multi-component layout।
`model_index.json`: StableDiffusionXLPipeline, EulerAncestralDiscreteScheduler,
দুই CLIP encoder, UNet ও VAE; tokenizer/config files উপস্থিত।

| Snapshot-relative weight | Bytes | SHA256 |
| --- | ---: | --- |
| text_encoder/model.safetensors | 492265168 | 778d02eb9e707c3fbaae0b67b79ea0d1399b52e624fb634f2f19375ae7c047c3 |
| text_encoder_2/model.safetensors | 2778702264 | fa5b2e6f4c2efc2d82e4b8312faec1a5540eabfc6415126c9a05c8436a530ef4 |
| unet/diffusion_pytorch_model.safetensors | 10270077736 | 1968fc61aa8449ab3d3f9b9a05bce88c611760c01e0c4a7a3785911b546fe582 |
| vae/diffusion_pytorch_model.safetensors | 334643268 | 716971093e3428c9156906fcbcc5500abf005317c5f4d3a5bb3fa28c45e1e071 |

সব weight F32 safetensors; bounded JSON header/contiguous offsets/file length
পরীক্ষিত। Full SHA256 cache blob identity ও cached revision tree-এর LFS hash/size
এর সঙ্গে মেলানো হয়েছে; remote weight manifest স্বাধীনভাবে পুনরায় আনা হয়নি।
Weight completeness এই static checks-এর সীমায়; runtime compatibility/quality নয়।
Cache-এ চারটি `.incomplete` file-ও আছে (0, 256000000, 256000000, 1676771384 bytes);
সেগুলো snapshot target নয় এবং verified weights-এর মধ্যে গণনা হয়নি। কিছু মুছিনি।

## Official identity ও license

[Revision model card](https://huggingface.co/stabilityai/sdxl-turbo/blob/71153311d3dbb46851df1931d3ca6e939de83304/README.md)
SDXL-Turbo text-to-image পরিচয় নিশ্চিত করে।
[Revision LICENSE.md](https://huggingface.co/stabilityai/sdxl-turbo/blob/71153311d3dbb46851df1931d3ca6e939de83304/LICENSE.md)
হলো Stability AI Community License Agreement (July 5, 2024)। Card metadata-তে
`sai-nc-community` থাকলেও license text গবেষণা/অবাণিজ্যিক এবং শর্তসাপেক্ষ সীমিত
বাণিজ্যিক ব্যবহার বর্ণনা করে; commercial registration, revenue threshold ও
redistribution/attribution শর্ত আছে। Unlimited commercial permission ধরে নেওয়া নয়।
Local snapshot-এ license/card copy নেই; official revision online যাচাই করা হয়েছে।
এই inventory ভবিষ্যৎ runtime/code-license/hardware preflight-এর বিকল্প নয়।

## Scope ও সীমা

Search: Developments, Downloads, animation-app, Hugging Face cache এবং readable
/media ও /mnt; hidden/ignored project weights-ও দেখা হয়েছে। দুই existing Qwen GGUF
planner asset পাওয়া গেছে; সেগুলো এই image step-এর target নয়, run/hash পুনরাবৃত্তি নয়।
/media-র কিছু directory permission denied; পুরো filesystem-এ অন্য model নেই এমন
দাবি নয়। Symlinked HF snapshot আলাদাভাবে অনুসরণ করে যাচাই করা হয়েছে।
কোনো install/download/load/inference/cloud action/asset deletion হয়নি। Anime
quality, character consistency ও ComfyUI compatibility এখনও অযাচাইকৃত।

## Outcome ও next

5.1 inventory সম্পন্ন; duplicate model download প্রয়োজন বলে কোনো সিদ্ধান্ত নয়।
পরের numbered step 5.2 ImageProvider mock contract; বর্তমান exception শুধু 5.1,
তাই 5.2 শুরু করতে scoped authorization extension প্রয়োজন। Phase 3/4 real gates
ও RunPod suspension বহাল। Docs drift/whitespace checks; app tests প্রযোজ্য নয়।
