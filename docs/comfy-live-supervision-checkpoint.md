# Phase 5.4 — L4.2 offline live supervision contract/storage

2026-10-08। বর্তমান L4 authorization ও owner next-work নির্দেশে L4.2 সম্পন্ন।
এটি standalone data/storage support; cleanup dispatcher বা live executor নয়।

## পরিবর্তন

[Contract](../animation_studio/providers/comfy_supervision.py)-এ পৃথক
`LiveComfySupervisionObservation` ও `parse_live_supervision_observation` আছে।
Live sidecar exact schema_version=2/live context নেয়; source none/live। Existing
mock v1 parser/model শুধু mock-ই নেয়। Strict types, frozen/revalidation, bounded
4096-byte JSON, duplicate/nonfinite rejection, context matching ও sanitized error
shared। Observation-এর timestamp/evidence hash/status syntax যাচাই হয়; evidence
lookup, freshness বা actual stop যাচাই হয় না। Synthetic live-mode test data real
observation/inference evidence নয়।

[Storage](../animation_studio/providers/comfy_supervision_storage.py)-এ explicit
`LiveComfySupervisionStore` শুধু exact LiveComfyJournalStore নেয়। Existing mock
store live journal/observation reject করে। Shared path/job lock, thread ownership,
atomic fsync/replace, accepted receipt matching ও guarded transitions reuse হয়।
not_requested → intent → observed/unknown; restart-এ দ্বিতীয় intent/retry নয়।
Cancellation acknowledgement worker/job/compute/storage status বদলায় না।

## Versioning/backward compatibility

Generation v1/v2 schema ও bytes অপরিবর্তিত। Mock supervision v1 পুরোনো parser/store
দিয়ে readable থাকে; live v2-তে automatic migration নেই। Mock evidence live-এ
upgrade করা যায় না, তাই migration policy reject/preserve। Existing same-path
sidecar ভুল mode/version হলে read/transition fail, create overwrite করে না। Missing
sidecar cleanup unknown; action permission নয়। Direct create initial observation
snapshot রাখতে পারে; cleanup dispatch ordering enforce করার future caller এখনও
দরকার। Model/store একা orchestration বা evidence authority নয়।

## Checks

Pre-change relevant baseline **254 PASS**। Final combined **337 PASS** (+83 cases):

```sh
.venv/bin/python -m pytest -q tests/test_comfy_live_supervision.py tests/test_comfy_supervision.py tests/test_comfy_supervision_storage.py tests/test_comfy_storage.py tests/test_comfy_v2_executor.py tests/test_comfy_supervised_recovery.py tests/test_comfy_cancel_crash.py
```

শেষ internal validator naming edit-এর পরে schema suites **147 PASS** পুনরায়।
[Live contract tests](../tests/test_comfy_live_supervision.py) malformed/size/duplicate,
প্রতিটি identity field, version/source isolation, v1 backward-read/rejected migration,
ack≠stop ও bypassed instance rejection cover করে।
[Shared storage suite](../tests/test_comfy_supervision_storage.py) mock/live দুই পথে
restart/one attempt, generation unchanged, private permissions/lock/thread,
corruption/symlink/FIFO, fsync/replace failure, receipt mismatch ও cross-mode
read/create/transition rejection cover করে। Tests-এ socket/DNS forbidden।
Ruff/format, excerpt drift, docs links/RESUME length ও whitespace PASS।

## সীমা ও next

L4.2 complete; পুরো L4 এখনও অসম্পূর্ণ। Runtime/GPU/TLS/auth/remote worker/resource
supervision acceptance হয়নি; live workflow gate বন্ধ। No install/model/network/
paid resource। Existing unrelated dirty work preserved; commit নয়।
Next L4.3: durable orchestration-এর offline composition ও failure/recovery tests,
বর্তমান L4 scope-এ অনুমোদিত। Synthetic transport fixture-এর result mock থাকবে;
live dispatch চালু নয়। Real target/GPU ও supervised acceptance prerequisites বহাল।
