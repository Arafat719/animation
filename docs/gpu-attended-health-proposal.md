# প্রথম GPU health পরীক্ষা: owner উপস্থিত থাকার প্রস্তাব

2026-09-26। Owner existing VPS/server সম্পর্কে নিশ্চিত নন। তাই external server
আছে ধরে নেওয়া হবে না এবং একই প্রশ্ন আবার করা হবে না। এটি executable launch
অনুমতি নয়; নতুন server কেনা/ভাড়া বা plan acceptance gate পরিবর্তনও নয়।

## প্রস্তাবিত সীমিত পথ

প্রথম health-only session-এ owner browser-এ উপস্থিত থাকবেন। এক disposable Pod
console থেকে owner তৈরি করবেন, পরে একই Pod বন্ধ/terminate করবেন। Agent verified
health evidence ব্যাখ্যা করবে। Automatic create/live adapter এখন enable নয়।
একবার create submit-এর পরে response অস্পষ্ট হলে Pods inventory দেখে আগে মিলাতে
হবে; পুনরায় Deploy নয়। Session name ও Pod ID লিখে রেখে শুধু সেটিতেই কাজ হবে।

অন্য device/connection দিয়ে একই console খোলার উপায় session-এর আগে যাচাই করতে
হবে; আছে ধরে নেওয়া হচ্ছে না। সেটি না থাকলে local power/network failure-এ cleanup
সম্ভব নাও হতে পারে। এই পথ unattended service বা hard billing cap নয়। External
supervisor-এর বিকল্প production guarantee হিসেবে এটি গণ্য হবে না।

## Launch-এর আগে পূরণযোগ্য handoff

| তথ্য | বর্তমান অবস্থা |
| --- | --- |
| Tested immutable image | GHCR reference private-access checkpoint-এ verified |
| RunPod account/console access | owner-এর কাছে যাচাই বাকি; token/password চাইবে না |
| Private image pull | আলাদা registry credential configuration বাকি |
| GPU, region, tier, disk, ports, command | exact console configuration ও quote বাকি |
| Credit/top-up/tax | অজানা; কোনো payment অনুমোদিত নয় |
| Session duration ও cleanup reserve | final quote/action preview-এ স্থির করতে হবে |
| Alternate console access | owner যাচাই বাকি; server আছে বলে অনুমান নয় |
| Phase 3/order prerequisite | বিদ্যমান gate বহাল; health-only exception অনুমোদিত নয় |
| Paid action approval | exact final preview-এর পরে পৃথক অনুমতি প্রয়োজন |

## পরীক্ষার দিন: উপরোক্ত gates ও approval পূরণ হলে মাত্র

1. Selected Pod ID, start time ও approved configuration record করো। Personal
   files/models/volumes ব্যবহার নয়; health-only image অপরিবর্তিত।
2. Authentication rejection এবং authenticated health/devices/capabilities যাচাই;
   GPU identity ও VRAM record। Model inference এই session-এর বাইরে।
3. পরীক্ষা ব্যর্থ হলে অথবা cleanup reserve শুরু হলে পরীক্ষা থামিয়ে cleanup করো।
   Local watchdog mock ফলকে actual shutdown evidence বলবে না।
4. Console-এ ওই Pod expand করে Stop, তারপর Terminate confirm। এটি disposable
   test Pod-এর জন্য; existing resource বা valuable data মুছে ফেলার নির্দেশ নয়।
5. Pod inventory refresh, relevant storage inventory ও account usage দেখো।
   Record-এ observation time এবং অনিশ্চয়তা রাখো; missing Pod alone billing-zero
   proof নয়। Confirmation না পেলে session closed দাবি নয়; operator follow-up।

Official [RunPod manage-Pods guide](https://docs.runpod.io/pods/manage-pods)
2026-09-26-এ যাচাই: console থেকে Stop/Terminate সম্ভব; stopped Pod volume storage
charge থাকতে পারে। Termination Pod-local data মুছে দেয়; attached network volume
থাকতে পারে। এই proposal-এ persistent/network volume তৈরি করার পরিকল্পনা নেই।

## Outcome এবং পরের নির্দিষ্ট কাজ

Unknown-server blocker-এর জন্য attended manual path-এর concrete proposal প্রস্তুত।
এখন আর VPS সম্পর্কে পুনরাবৃত্ত প্রশ্ন বা অতিরিক্ত mock watchdog feature নয়। পরের
ধাপ: RunPod account/console access আছে কি না জানা এবং non-billable configuration
preview সংগ্রহের handoff; Deploy/top-up/credential creation নয়। Account access
ছাড়া actual quote জানা যাবে না; historical price-কে current quote বলা হবে না।

Docs links/plan drift/whitespace checks PASS; prior 126-test evidence retained।
No source change, install, secret read, account mutation or paid action।
