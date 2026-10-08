# Phase 5.4 — live transport offline contract/design

2026-10-08। Owner GPU নেই জানিয়েছেন এবং প্রস্তাবিত offline contract/design
অনুমোদন করেছেন। এটি design-only micro-step; implementation, network/server,
GPU/model/paid resource বা live dispatch অনুমোদন নয়। Master feature requirements
অপরিবর্তিত; existing 5.4 transport gap-এর implementation boundary নির্ধারণ।

## 1. বর্তমান source boundary

- [Config](../animation_studio/providers/comfy_config.py): explicit canonical HTTPS
  origin + in-memory SecretStr; construction-এ network/credential discovery নেই।
- [Auth client](../animation_studio/providers/comfy_auth.py): exact MockTransport,
  narrow route/method/view parameters, no redirect/retry/ambient proxy, is_mock=True।
- [Executor](../animation_studio/providers/comfy_http.py): shared bounded JSON/MIME/
  image validation; exact mock boundary। Per-I/O timeout hard total deadline নয়।
- [Storage](../animation_studio/providers/comfy_storage.py): existing constructor mock-only;
  L4.1-এ separate standalone live-mode store যোগ হয়েছে।
  [Identity](../animation_studio/providers/comfy_identity.py) v2 discriminator reuse;
  live executor/supervision admission ও actual acceptance এখনও বাকি।
- Local pinned ComfyUI/server.py-এ POST /api/jobs/{job_id}/cancel route inspected;
  current executor এই prompt-scoped route ব্যবহার করে। Target deployment-এ একই
  capability যাচাই বাকি; global interrupt/cancel-all fallback গ্রহণযোগ্য নয়।

Completed mock/auth/durable/C1–C3 acceptance restart নয়।
[Readiness review](comfy-readiness-review.md) ও
[cleanup fix](comfy-cpu-cleanup-checkpoint.md)-এর সীমা বহাল।

## 2. প্রস্তাবিত transport boundary

Future production transport আলাদা explicit factory দিয়ে তৈরি হবে; existing mock
constructor থেকে MockTransport check সরিয়ে নির্বিচার transport নেওয়া যাবে না।
Factory config revalidate করবে; constructor network খুলবে না, request-এ dispatch।
Offline tests dependency injection ব্যবহার করবে, production factory arbitrary
caller client/transport নেবে না। Test injection production opt-in নয়।

| বিষয় | প্রয়োজনীয় আচরণ |
| --- | --- |
| Origin | এক explicit canonical HTTPS origin; arbitrary absolute URL, authority, userinfo, fragment বা route query override reject |
| TLS | Certificate/hostname verification বাধ্যতামূলক; insecure bypass নয়; trust configuration explicit, ambient env নয় |
| Credentials | Selected origin-এ bearer header; token repr/journal/errors/artifact-এ নয়; automatic refresh/fallback নেই |
| Routing | Existing narrow methods/routes/view parameters reuse; redirects follow নয়, Location-এ credential যাবে না |
| Retry | Transport/application retry শূন্য; 401/403/429/5xx-এ resubmit নয় |
| Response | Identity encoding; existing byte/MIME/JSON/image checks; bounded parser একটিই |
| Lifetime | One owner; response success/error/cancel-এ close, client close idempotent; closed client নতুন request reject |
| Provenance | Transport kind ও inference evidence আলাদা; fixture result সবসময় mock, TLS connection real inference proof নয় |

Selected private GPU endpoint বৈধ হতে পারে; blanket private-IP ban এই design দেয়
না। Explicit owner-selected origin-এর বাইরে fallback/discovery/proxy নয়।
DNS routing/network isolation-এর deployment evidence offline tests দিতে পারে না।

## 3. Deadline ও failure semantics

এক request-এর caller-supplied absolute monotonic deadline থাকবে। Dispatch/chunk
read-এর আগে remaining budget check; pool/connect/write/read budget remaining-এর
বেশি নয়। Byte cap ও finite timeout configuration বাধ্যতামূলক। তবে slow streaming,
DNS/OS scheduling বা synchronous blocking call-এ cooperative check কঠোর total
wall-clock bound নয়। Production hard execution bound-এর জন্য independent owned
supervisor প্রয়োজন; CPU dummy supervisor সরাসরি remote worker supervision নয়।

Public failure code/message bounded; token, response body, request headers,
Location বা raw transport exception প্রকাশ নয়। Private diagnostics-ও credential
redaction ছাড়া log করা যাবে না। Cleanup error primary failure মুছবে না; unclosed
resource হলে caller-owned cleanup handle/status দিতে হবে।

| Failure stage | Durable outcome |
| --- | --- |
| Config/route validation | Zero dispatch; no new intent |
| Mandatory preflight rejected | No submit intent/POST |
| Submit intent durable, receipt নেই | Outcome unknown; intent রাখা; automatic POST retry নয় |
| Valid accepted receipt আছে | Same context/journal-এ GET-only recovery |
| Timeout/cancel after receipt | Existing same-lock durable single cancel path; no parallel POST |
| Cancel acknowledgement | Dispatch acknowledgement মাত্র; worker/compute/storage stop proof নয় |
| Transport/client close | Local connection cleanup; remote job cancelled দাবি নয় |

GET-only recovery-তে fresh submit বা cancel যোগ করা যাবে না। Intent-only recovery
receipt বানাবে না। নতুন job/root দিয়ে unknown submission পুনরায় করা deduplication
নয়; এই existing limitation caller-এর সামনে থাকবে।

## 4. Live execution gate — transport factory যথেষ্ট নয়

Live workflow composition চালুর আগে সব শর্ত দরকার:

1. Target runtime/GPU/native validation এবং trusted model/deployment identity।
2. Explicit selected origin-এর actual TLS/auth ও route capability evidence।
3. Versioned durable storage live-mode support, backward-read/context isolation;
   mock journal-কে live relabel নয়। Schema change হলে migration tests।
4. Mandatory preflight → durable intent → one submit → durable receipt ordering।
5. RAM/VRAM/time enforcement, worker ownership, bounded cleanup ও ambiguous outcome
   recovery। Remote server/descendant coverage C3 direct-child scope দিয়ে পূরণ নয়।
6. Accurate real artifact provenance; verified PNG/model/seed evidence। 5.5 আলাদা।

Actual target না থাকায় শর্তগুলো এখন যাচাই হয়নি। কোনো constructor flag বা
is_mock=False assignment একা live readiness দেয় না।

## 5. Offline acceptance matrix

পরবর্তী implementation-এ synthetic credentials ও forbidden socket/DNS fixture
ব্যবহার করে পরীক্ষা হবে; server/model প্রয়োজন নেই।

- Invalid origin/route/method/params/timeout → zero dispatch।
- Valid selected-origin request → exact method/path/query/header/body;
  foreign-origin URL ও redirect credential forwarding → zero follow-up।
- TLS verification/no proxy/no retries policy construction checks; এগুলো handshake
  acceptance নয়। Simulated TLS/auth/timeout/read errors → bounded sanitized failure।
- 401/403/429/5xx, midstream failure ও ambiguous POST → exactly one dispatch।
- Oversized/compressed/wrong MIME/malformed JSON ও slow chunk fixture → bounded
  rejection; hard deadline claim নয়।
- Response/client cleanup on success, parse failure, cancellation ও close failure;
  original error retained, leaked resource unknown/manual cleanup।
- Existing mock-only constructor/storage gates ও fixture provenance unchanged।
- Later durable integration: preflight no-intent failure, receipt persistence,
  same-key no-resubmit, GET-only recovery, context mismatch ও v1/v2 compatibility।

## 6. একক micro-step order ও authorization

**L1 — পরের প্রস্তাবিত implementation:** pure transport request-policy validator
ও no-network contract tests। Existing canonical origin/config semantics reuse;
route/method/view/finite positive timeout validation, typed bounded rejection।
Config বা auth feature পুনরায় বানানো নয়; এই validator তৈরি হলেও production
factory/executor/storage live gate বন্ধ থাকবে।

L2: explicit transport factory/lifecycle ও injected offline failure tests।
L3: shared executor boundary composition ও provenance contract tests।
L4: durable live-mode composition/backward-read + supervised acceptance।
L2–L4 পৃথক scope; prerequisites ও owner নির্দেশ ছাড়া শুরু নয়। Actual TLS/server/
GPU acceptance তাদের offline tests থেকে পৃথক এবং target environment প্রয়োজন।

এই turn শুধু design অনুমোদিত; L1 source/tests implementation অনুমোদিত নয়।
Owner-এর পরবর্তী next-work নির্দেশে শুধু L1 শুরু করা যাবে। Paid resource,
>2 GB download, GPU launch এবং নতুন phase-এর approval বহালভাবে পৃথক।

## Checks/outcome

Relevant source/auth checkpoint ও local ComfyUI route cross-check সম্পন্ন।
Docs links, RESUME length, excerpt drift ও whitespace PASS। App tests rerun
প্রয়োজন হয়নি; নতুন runtime/TLS/inference evidence নেই। Design blocker নেই;
real 5.4 GPU gate owner-confirmed blocked।

## L1 implementation update — 2026-10-08

Owner next-work নির্দেশে [L1](comfy-request-policy-checkpoint.md) সম্পন্ন: pure
validator + 64 cases; relevant combined 237 PASS। উপরের design-turn authorization
historical; এখন next owner-directed scope L2। Live dispatch অনুমোদিত নয়।

## L2 implementation update — 2026-10-08

Owner নির্দেশে [L2 factory/lifecycle](comfy-transport-checkpoint.md) সম্পন্ন;
34 new cases, combined 271 PASS। Request tests mock-only; actual TLS/live workflow
acceptance নয়। Per-read timeout initial remaining budget, in-flight read-এর timeout
কমে না; cooperative checks আছে, independent hard supervisor এখনও pending।
Next owner-directed L3 offline executor composition/provenance tests।

## L3 implementation update — 2026-10-08

Owner next-work নির্দেশে [L3 composition](comfy-transport-composition-checkpoint.md)
সম্পন্ন; combined 590 PASS। Offline executor/shared policy/parser/provenance
verified; live workflow/storage disabled। Next owner-directed L4 পৃথক scope।

## L4.1 implementation update — 2026-10-08

Owner L4 next-work নির্দেশে প্রথম একক অংশ [live-mode storage](comfy-live-storage-checkpoint.md)
সম্পন্ন; baseline 242, final 290 PASS। Existing v2 schema reuse; v1/v2 backward-read,
no relabel ও same-job mode isolation verified। Live execution disabled। পূর্ণ L4
সম্পূর্ণ নয়; next L4.2 offline live supervision contract/storage বর্তমান L4 scope-এ
অনুমোদিত। Actual target/GPU ও subsequent supervised acceptance বাকি।

## L4.2 implementation update — 2026-10-08

[Live supervision contract/storage](comfy-live-supervision-checkpoint.md) সম্পন্ন;
combined 337 PASS। পৃথক live v2 sidecar, mock v1 backward read/no promotion,
same-lock/one-attempt guarded storage। Data/storage support live execution বা stop
proof নয়। Next authorized L4.3 offline durable orchestration composition/tests;
পূর্ণ L4 ও actual target/GPU supervised acceptance এখনও অসম্পূর্ণ।

## L4.3 implementation update — 2026-10-08

[Offline durable session](comfy-offline-session-checkpoint.md) সম্পন্ন: owned bounded
transport/HTTP/durable composition, mock provenance, no-resubmit/GET-only recovery
ও cleanup failure ownership; 113 PASS। Live data stores-এ mock receipt লেখা নয়।
Actual live-mode durable composition/supervised acceptance unresolved। Next L4.4
live admission/remote supervision prerequisite gap review; live dispatch disabled।

## L4.4 review update — 2026-10-08

[Remaining admission/supervision review](comfy-live-admission-review.md) সম্পন্ন।
Live stores/transport standalone; production workflow composition এবং actual target
supervised acceptance বাকি। Next available GPU target-এর existing-authorized
preflight; owner-confirmed hardware absence-এ blocked, repeated probe নয়।
