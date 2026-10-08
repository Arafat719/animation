# Phase 5.4 — offline admission contract proposal

2026-10-08। Owner-এর GPU-free next-scope নির্দেশে একক design/review সম্পন্ন।
[L4.4 gaps](comfy-live-admission-review.md) থেকে পরের implementation scope নির্বাচন;
এখন source implementation বা live activation নয়। Feature requirements অপরিবর্তিত।

## উদ্দেশ্য ও reuse

Target evidence অনুপস্থিত থাকলেও admission decision-এর fail-closed semantics
offline যাচাই করা যায়। Existing ComfyExecutionContext, ComfySupervisionPolicy ও
resource decision boundary reuse করতে হবে; নতুন executor/store বা transport নয়।
[Resource evaluator](../animation_studio/providers/comfy_resource_guard.py) বর্তমানে
mock-only telemetry decisions দেয়; সেটি runtime/TLS/model capability validation নয়।
[Inventory wrapper](../animation_studio/providers/comfy_checked.py) শুধু node inventory
দেখে; installed/native runtime বা remote worker ownership attestation নয়।

## প্রস্তাবিত pure input/output

একটি immutable snapshot-এ expected execution context, worker identity, selected
device, policy identity এবং required capability observations থাকবে। Caller-এর
current monotonic time ও explicit maximum evidence age লাগবে; একই process clock
session-এর evidence ছাড়া acceptance নয়। Persisted wall time দিয়ে নতুন run budget
বা restart admission নয়। Observation-এর source fixture/target আলাদা থাকবে।

| Required capability | কীসের evidence চাই |
| --- | --- |
| runtime_native | Selected runtime/driver/device-এর bounded native operation |
| model_identity | Expected model manifest এবং selected deployment registration |
| endpoint_auth_routes | Selected origin-এর TLS/auth ও required prompt-scoped routes |
| worker_ownership | Selected worker-এর scope; shared server-এর global kill অনুমোদন নয় |
| resource_supervision | Target RAM/VRAM telemetry, enforcement limitations এবং independent deadline/cleanup supervision |

প্রতিটি observation-এ capability enum, passed/failed/unknown state, matched
context/worker/device/policy binding, checked-at time এবং bounded evidence digest
থাকবে। Free-text secret, raw response বা exception body নয়। Missing/duplicate/
unknown capability, mismatch, stale/future/nonfinite time বা invalid input deny।
Maximum age/policy caller explicit দেবেন; target-specific value অনুমান নয়।

Output কেবল decision ও bounded reason codes; pure evaluator কোনো I/O, journal
write, POST, resource launch বা readiness token তৈরি করবে না। Fixture evaluation
সফল হলেও result fixture থাকবে; production caller সেটি গ্রহণ করতে পারবে না।

## Trust ও integration সীমা

Schema-valid `passed` field বা evidence hash trusted verification নয়। Future
collector-কে actual target evidence সংগ্রহ ও identity/freshness verify করতে হবে;
caller labels cryptographic attestation নয়। Pure evaluator completion live-ready
করবে না। Production collector/consumer ও supervisor binding পৃথক pending কাজ।

Future submission ordering: same job lock → verified admission → mandatory node
preflight → admission freshness/resource recheck → durable intent → one submit →
durable receipt। Preflight এবং submit atomic নয়; last check-এর পর target বদলানোর
ঝুঁকি ownership/session control-এ সামলাতে হবে। Existing intent থাকলে এই sequence
পুনরায় নয়। Accepted recovery GET-only; expired generation admission fresh POST বা
cleanup retry-এর অনুমতি নয়। Run শুরু হওয়ার পরে failure হলে existing one-attempt
cleanup contract; admission evaluator নিজে cancel/terminate করবে না।

## পরের একক implementation ও pass checks

**A1: pure offline admission schema/evaluator ও contract tests।**
No-network tests-এ all-required fixture result, missing/failed/unknown/duplicate
capability, each context/worker/device/policy mismatch, source isolation,
stale/future/nonfinite clock, bypassed model revalidation ও bounded error যাচাই।
Existing mock executor/live storage gates unchanged থাকার regression check লাগবে।
Evidence collection, execution wiring, schema migration, server/model/GPU run নয়।

এই turn scope proposal/design পর্যন্ত। পরবর্তী owner next-work নির্দেশে A1 শুরু
করা যাবে; এখন implementation শুরু হয়নি। Available GPU-এর real preflight আগে থেকেই
অনুমোদিত কিন্তু blocked; paid resources/new phase-এর পৃথক অনুমোদন বহাল।

## Checks

L4.4 review ও existing identity/resource/inventory boundaries cross-check। Docs
links/RESUME length, plan excerpt drift ও whitespace PASS। Source/requirements
পরিবর্তন নেই; app tests বা unchanged GPU probe চালানো হয়নি।

## A1 implementation update — 2026-10-08

Owner next-work নির্দেশে [A1 evaluator](comfy-admission-checkpoint.md) সম্পন্ন;
85 new cases, combined 460 PASS। Tuple snapshot max five, source/mode isolation,
policy digest ও caller clock-session UUID binding; invalid input bounded deny।
Target labels passed হলেও actual attestation নয়; execution wiring নেই। Next
owner-directed A2 fixture-only offline admission/recheck integration; live বন্ধ।

## A2 implementation update — 2026-10-08

[Offline integration](comfy-admission-integration-checkpoint.md) সম্পন্ন; 237 tests
PASS। Session execute mandatory fixture snapshot, same-lock pre/post-preflight
check, bounded clock failure; recovery no admission/GET-only। Capability claims
actual resource enforcement নয়। Next proposed owner-directed A3 mock resource
admission/recheck integration; target collector ও live workflow এখনও বাকি।
