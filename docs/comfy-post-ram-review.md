# Phase 5.4 — D6 post-RAM readiness review

2026-10-11। Owner next-work নির্দেশে একক source/evidence review সম্পন্ন।
নতুন implementation scope নির্ধারিত না থাকায় বর্তমান offline completion ও real
execution-এর অবশিষ্ট dependency মিলিয়ে দেখা হয়েছে; source/test পরিবর্তন নয়।

## এখন কী প্রস্তুত

| অংশ | বর্তমান evidence | যা এখনও প্রমাণিত নয় |
| --- | --- | --- |
| Deadline | D1 এক original run/cleanup ceiling propagate করে; D3 parent child-কে stop/kill/reap করে | Parent death, OS scheduling বা remote worker-এর hard deadline |
| RAM | D5 প্রথম valid local reading-এর আগে startup পাঠায় না; চলমান guard stale/invalid/budget breach-এ abort করে | Allocation hard cap, descendants, target Comfy server RAM বা GPU VRAM |
| Cleanup | Independent child/sampler/pipe cleanup; unknown outcome-তে caller-owned handles | Remote job/compute/storage বন্ধ হওয়ার প্রমাণ |
| Durable offline flow | Mandatory preflight, intent/receipt, single cancel, GET-only recovery | Live durable orchestration, trusted target capability collection |
| Image | Fixture PNG validation ও mock provenance | বাস্তব model-generated image ও human anime-quality review |

## Source মিলিয়ে পাওয়া boundary

- [Parent](../animation_studio/providers/comfy_session_supervisor.py)-এ startup write
  `admitted` দ্বারা gated; অসম্পূর্ণ startup abort-এ stdin close। Monitor sampler
  snapshot ব্যবহার করে; synchronous procfs read parent loop-এ নেই। Final cleanup
  original deadline ব্যবহার করে এবং sampler unknown হলে manual-cleanup handle রাখে।
- [Child](../animation_studio/providers/comfy_session_child.py)-এর resource_sample
  এখনও synthetic zero RSS/VRAM ও fixture capability claims। Parent-এর measured RAM
  এগুলোকে real target claims করে না। দুই evidence source আলাদা আছে।
- [Session](../animation_studio/providers/comfy_offline_session.py) matching mock
  context ও mock transport নেয়। D5 wrapper যোগ হলেও standalone session নিজে independent
  supervisor নয়। Mock check সরিয়ে live execution চালানো এই review-এর ফল নয়।
- [Live store](../animation_studio/providers/comfy_storage.py) explicit live identity
  সংরক্ষণ করতে পারে; [transport](../animation_studio/providers/comfy_transport.py)
  production request করতে পারে। এগুলো real durable workflow/supervisor composition
  তৈরি করে না। Target collector/trust binding এখনও বাকি।

এ review-এ নতুন concrete source defect প্রতিষ্ঠিত হয়নি; সব সম্ভাব্য bug নেই এমন
দাবি নয়। Completed D1/D3/D5 পুনরায় implement করার প্রয়োজন পাওয়া যায়নি।

## পরের বাস্তব কাজ ও blocker

পরবর্তী নির্ধারিত micro-step: owner-selected available GPU environment-এ আগের
অনুমোদিত bounded native/runtime preflight। Install owner করবেন। Existing
[local evidence](comfy-local-preflight.md)-এ dependency/native imports PASS, CUDA
unavailable/count 0; owner GPU নেই জানিয়েছেন। Environment বদলের নতুন তথ্য নেই,
তাই পুনরায় probe করা হয়নি।

Resume করার প্রয়োজনীয় তথ্য: ব্যবহারযোগ্য GPU host/environment এবং তার interpreter/
ComfyUI checkout location। Target পাওয়া গেলে আগে pin/import/driver/tiny CUDA check;
তারপর model/server validation, selected-origin TLS/auth/route evidence, owned worker
RAM/VRAM/time supervision ও live durable composition-এর scoped কাজ নির্ধারণ হবে।
এসব readiness dependency; এখন live dispatch বা implementation approval নয়।

আরেকটি mock layer বানালে hardware/native/live evidence-এর এই gap বন্ধ হবে না।
এই review নতুন offline micro-step উদ্ভাবন করছে না। অন্য GPU-free কাজ চাইলে owner
তার scope নির্বাচন করবেন; 5.5/new phase ও স্থগিত CPU experiment নিজে থেকে শুরু নয়।
Paid resource বা >2 GB download-এর পৃথক explicit approval বহাল।

## Checks ও outcome

D5-এর 515 combined PASS evidence reused; source অপরিবর্তিত বলে app tests rerun নয়।
Changed-doc links, RESUME length, plan excerpt drift ও whitespace PASS।
Readiness summary-তে D5 যোগ করে stale A3/D3-only current heading সংশোধন হয়েছে।
Master requirements/schema অপরিবর্তিত; install/model/server/network/GPU/paid কাজ
বা commit হয়নি। D6 review complete; 5.4 real image এখনও blocked/incomplete।
