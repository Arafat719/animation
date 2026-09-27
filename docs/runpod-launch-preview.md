# Phase 4.7 — GPU launch cost/action preview draft

2026-09-25। **Research ও draft প্রস্তুত; 4.7 exact approval-ready preview অসম্পূর্ণ।**
কোনো resource, account API call, download বা paid action হয়নি।

2026-09-26 update: [বর্তমান gap review](gpu-launch-readiness-review.md)।
GHCR publication ও mock REST watchdog সম্পন্ন; নিচের price estimate পুরোনো draft,
বর্তমান quote নয়। Live readiness এখনও অসম্পূর্ণ।

## সর্বশেষ owner নির্দেশ: RunPod স্থগিত

Owner আপাতত RunPod ছাড়া local কাজ করতে বলেছেন। নিচের preview পুনরারম্ভের
নোট historical; quote/screenshot অনুরোধ আর pending নয়। Paid launch/payment নয়।

## 2026-09-27: preview পুনরারম্ভ

Owner-এর পরের-কাজ নির্দেশে শুধু non-billable 4.7 preview আবার চলছে। Paid launch,
top-up, credential creation ও CPU model experiment অনুমোদিত হয়নি।
[Official public pricing](https://www.runpod.io/pricing) পুনরায় যাচাই: RTX A5000
24 GB $0.27/hr এখনও দেখায়। 15 মিনিট compute $0.0675; নিচের provisional disk
assumption-সহ প্রায় $0.068195 before tax। এটি account quote বা guaranteed total নয়।
[Pod pricing](https://docs.runpod.io/pods/pricing) অনুযায়ী exact GPU price deployment
console-এ; on-demand launch-এর জন্য নির্বাচিত configuration-এর অন্তত এক ঘণ্টার
credit লাগে। স্বল্প session cost এবং required account funding আলাদা।

Completed: local image/GHCR identity, mock lifecycle/watchdog/supervisor ও durable
session/report; [handoff](gpu-mock-handoff.md)। পুরোনো next-supervisor নির্দেশ সম্পন্ন।
Execution path-এর প্রস্তাব [attended manual health](gpu-attended-health-proposal.md);
এটি approved live execution বা unattended protection নয়।

পরের required input: owner console-এ বর্তমানে দেখানো GPU name/VRAM, cloud tier,
region, hourly compute rate, disk sizes ও storage/total quote। Agent-এর authenticated
RunPod console access নেই। Account-specific তথ্য ছাড়া final preview শেষ করা যাবে না।
কোনো Deploy/top-up নয়; token/card/password পাঠানোর প্রয়োজন নেই। Quote পেলে existing
image digest/command/port এবং startup/test/cleanup window দিয়ে final sheet পূরণ হবে;
phase-order, private pull, alternate operator access ও paid approval gates বহাল।

এই update-এ public sources/arithmetic ও docs consistency checks PASS; app tests নয়।

## নির্বাচিত প্রাথমিক scope

প্রথম paid session-এর প্রস্তাব শুধু 4.8 authenticated GPU health: এক Pod, এক GPU,
এক region, এক launch attempt; মোট billable window সর্বোচ্চ 15 মিনিটের লক্ষ্য।
Model weights নয়; GPU discovery/VRAM এবং authenticated worker health/capabilities
যাচাই। Existing mock healthy=true real GPU health-এর evidence হবে না।
4.9 real inference আলাদা: model/source/license/hash/size এবং artifact verification
চূড়ান্ত না হওয়া পর্যন্ত inference অনুমোদন চাওয়া হবে না। CPU planner experiments
স্থগিতই থাকবে। Phase 3 acceptance/order prerequisite নিজে থেকে শিথিল হচ্ছে না।

## Candidate ও হিসাব

[Official pricing](https://www.runpod.io/pricing) 2026-09-25-এ পড়া; page updated
September 13, 2026। Public list-এ RTX A5000 24 GB $0.27/hr, L4 24 GB $0.49/hr,
RTX 4090 24 GB $0.74/hr। Health-only candidate হিসেবে A5000 নির্বাচন provisional;
account/region availability, cloud tier এবং worker compatibility যাচাই হয়নি।
এটিকে guaranteed cheapest suitable available GPU বলা হচ্ছে না।

| Proposed item | Preview |
| --- | --- |
| GPU | 1 × RTX A5000 24 GB, on-demand; no spot/savings commitment |
| Compute list rate | $0.27/hr; deployment quote required |
| Proposed rate ceiling | $0.30/hr; বেশি হলে launch নয় |
| Total billable window | 15 minutes, initialization ও teardown-সহ; measured নয় |
| Compute at list rate | $0.27 × 15/60 = $0.067500 |
| Compute at rate ceiling | $0.30 × 15/60 = $0.075000 |
| Container disk | provisional 20 GB; pinned image size যাচাইয়ের পরে final |
| Pod volume / network volume | proposed 0 GB / none; console defaults verify required |
| Container storage estimate | 20 × $0.10 × (0.25/720) = $0.00069445 |
| List-rate subtotal | প্রায় $0.068195, tax-এর আগে |
| Rate-ceiling subtotal | প্রায় $0.075695, tax-এর আগে |
| Proposed session budget | $0.10; owner-approved নয়, enforced hard cap-ও নয় |

Storage হিসাবের 720 ঘণ্টা/month একটি planning assumption, provider billing divisor
verified নয়। [Official Pod pricing](https://docs.runpod.io/pods/pricing)-এ container
storage $0.10/GB/month; deployment-এর console quote final। Ingress/egress fee নেই
বলা আছে। On-demand deploy করতে configuration-এর অন্তত এক ঘণ্টার credits প্রয়োজন;
এটি 15-minute usage cost নয়। Account top-up minimum, tax/currency/credit balance
অজানা; কোনো top-up প্রস্তাব অনুমোদিত নয়। Paid session budget-এ tax/other fees fit
না করলে launch নয়। Startup সময় বা cleanup failure হলে actual cost বাড়তে পারে।

## Approval-ready হতে বাকি নির্দিষ্ট তথ্য

1. Local build/test করা worker image এবং immutable image digest; image size,
   CUDA/runtime compatibility, container entrypoint/port ও source revision।
   Health-worker source, Docker recipe ও allowlisted packager এখন আছে;
   [checkpoint](gpu-health-packaging-checkpoint.md)। Owner-built local image ও CPU/no-GPU smoke এখন PASS;
   [image evidence](../deploy/gpu-health/local-image-evidence.json)। GHCR immutable reference/publication verified; provider-side private pull
   ও remote GPU compatibility এখনও বাকি।
2. GPU device-discovery health/capabilities ও unauthorized-access local tests PASS;
   real GPU/container execution বাকি। Device discovery inference readiness নয়।
3. Approved execution path: RunPod adapter বর্তমানে mock-transport-only; live
   dispatch, resource-ID capture, ambiguous-create reconciliation ও independent
   stop/terminate fallback নেই। এগুলো ছাড়া paid create retry নিরাপদ নয়।
4. Runtime timeout/stop verification; budget estimator preflight-only। 15 মিনিট
   শেষ হলে GPU নিজে থেকে বন্ধ হবে—এমন implementation বর্তমানে নেই।
5. Exact region/cloud tier/availability, console quote, disk feasibility, account
   balance/tax এবং পূর্ণ create payload (image digest-সহ) পুনরায় দেখানো।
6. Phase 3 real acceptance/phase-order prerequisite এখনো বহাল; 4.8 execution-এর
   prerequisite readiness অথবা owner-approved scoped revision প্রয়োজন।

এগুলো placeholder দিয়ে execute করা হবে না। Read-only public pricing research
শেষ; launch approval এখন pending নয়—প্রস্তাব এখনও approval-ready হয়নি।

## প্রস্তাবিত action sequence — prerequisites ও approval-এর পরে মাত্র

1. Final quote/digest/config/budget এবং exact selected GPU দেখিয়ে explicit paid
   approval নাও; configuration বদলালে revised preview দাও।
2. এক Pod create; ID capture। Ambiguous response হলে আগে reconcile; blind create
   retry নয়। অন্য বিদ্যমান resource স্পর্শ নয়।
3. Worker ready হওয়ার সময়সহ clock track; GPU identity/VRAM যাচাই, token ছাড়া 401,
   token-সহ health/capabilities PASS। ব্যক্তিগত assets বা model upload নয়।
4. Failure বা window শেষের আগেই cleanup; শুধু এই session-এর disposable Pod।
   Logs/metadata স্থানীয়ভাবে সংরক্ষণ করে Stop, তারপর Terminate; no retained volume।
5. Pod absent/compute stopped এবং storage inventory/billing status আলাদাভাবে
   verify; cleanup failure হলে immediately report, billing ended দাবি নয়।

[Official manage-Pods guide](https://docs.runpod.io/pods/manage-pods) অনুসারে stopped
Pod-এ volume disk-এর charge থাকে; termination-এর আগে প্রয়োজনীয় data export করতে
হয়। Network volume থাকলে Pod terminate করলেও সেটি থাকে—এই proposal-এ network
volume তৈরি নয়। এই cleanup sequence কোনো existing asset deletion অনুমোদন নয়।

## Outcome, checks ও next step

- Price sources, source/deployment gaps এবং Decimal arithmetic checked।
- Docs links/RESUME length/plan excerpt drift/whitespace PASS; docs-only বলে app
  tests নয়। আগের 214-test evidence retained। No source/master changes বা commit।
- পরের প্রয়োজনীয় local micro-step: existing Phase 4 worker requirement-এর pinned
  deployment packaging ও GPU-health contract source এখন সম্পন্ন (পরবর্তী owner নির্দেশে)।
  Local build/smoke ও GHCR distribution PASS; mock lifecycle/watchdog-ও PASS।
  পরের bounded mock supervisor test; বিস্তারিত বর্তমান gap review-তে।
- 4.8/4.9 শুরু হয়নি; paid approval চাওয়া হয়নি, কারণ concrete deployment অসম্পূর্ণ।
