# 5.3 — Minimal ComfyUI API workflow

2026-09-28। Owner-এর next-work নির্দেশে scoped exception 5.3 offline কাজ পর্যন্ত।

## Deliverable

- `workflows/sdxl-turbo-api.json`: seven-node API prompt graph; editor UI JSON নয়।
- `animation_studio/providers/comfy_workflow.py`: ImageRequest থেকে fresh graph
  builder, exact profile validator ও duplicate-key-rejecting JSON loader।
- Flow: DiffusersLoader → positive/empty CLIP encodings → EmptyLatentImage →
  KSampler → VAEDecode → SaveImage। Fixed 512×512, batch 1, steps 1, CFG 1,
  euler/normal, denoise 1; request prompt ও seed ছাড়া settings fixed।
- Model mapping pinned to inventoried SDXL-Turbo revision
  `71153311d3dbb46851df1931d3ca6e939de83304`। Relative loader name `sdxl-turbo`
  একটি future registration alias, বর্তমান server-এ model পাওয়া যায় এমন দাবি নয়।
- Validator exact node classes/inputs/links/ports/settings checks করে; dangling
  link, cyclic/wrong-port rewiring, extra node/input, path changes, wrong scalar
  type/model/version rejected। Arbitrary ComfyUI workflow validator নয়।
- Provider request model/seed mapping retained; JSON graph-এর বাইরে runtime manifest
  দিয়ে model identity প্রমাণ করতে হবে। এটি real ImageProvider adapter নয়।

## Official sources checked

[ComfyUI core nodes](https://github.com/Comfy-Org/ComfyUI/blob/master/nodes.py) এবং
[official API example](https://github.com/Comfy-Org/ComfyUI/blob/master/script_examples/basic_api_example.py)
2026-09-28-এ read-only review করা হয়েছে। Nodes use class_type/inputs and node/port
links; API submission later wraps graph under `prompt`। কোনো submission code নেই।
DiffusersLoader is deprecated but present; it discovers model_index.json under
configured diffusers roots and outputs MODEL/CLIP/VAE। Existing asset multipart
Diffusers snapshot বলে এটি বেছে নেওয়া; single checkpoint আছে বলে ধরে নেওয়া হয়নি।
Upstream master mutable; selected runtime pin এবং তার node inventory যাচাই বাকি।

## Checks ও সীমা

Previous ImageProvider baseline 22 PASS reused; new workflow 29 + image regression
22 = 51 PASS। Tests include JSON roundtrip, Bengali prompt/seed preservation,
independent graphs, checked-in JSON, malformed/duplicate JSON, wrong model,
graph mutation rejection ও network-disabled builder/validator। Ruff lint/format,
plan excerpt drift, whitespace ও local links PASS।

5.3 offline deliverable সম্পন্ন; live ComfyUI `/object_info`/server prompt validation,
registered model mapping, loader compatibility, runtime/hardware/license preflight,
real output quality ও inference এখনও অযাচাইকৃত। No install/download/model load,
cloud call, asset mutation বা API/UI/DB পরিবর্তন। Phase 3/4 gates deferred।

## Next

5.4 প্রথম real anime image। শুরু করার আগে runtime/hardware/model-registration
preflight ও পৃথক execution scope স্থির করতে হবে; current exception model run
অনুমোদন করে না। RunPod suspension এবং owner-only installation preference বহাল।
