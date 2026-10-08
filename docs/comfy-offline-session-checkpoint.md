# Phase 5.4 — L4.3 offline durable composition

2026-10-08। Owner next-work নির্দেশে bounded transport + durable orchestration-এর
owned offline entry point ও failure/recovery acceptance সম্পন্ন। পূর্ণ L4 live-mode
composition/supervised acceptance সম্পূর্ণ নয়।

[Session](../animation_studio/providers/comfy_offline_session.py): explicit endpoint,
private root, matching mock context ও exact MockTransport নিয়ে bounded transport,
HTTP executor এবং existing DurableComfyExecutorV2 compose করে। Constructor-এ
request/file creation নেই। Live context, mismatched origin ও invalid config reject;
execute/recover-এর আগে closed/provenance checks। Fixture result is_mock=True,
readonly session label; ComfyImageProvider দিয়ে PNG/model/seed path reuse হয়।

Existing preflight → durable intent → one submit → durable receipt ordering এবং
same-lock durable cancel reuse; কোনো নতুন retry path নেই। Same root/context-এ
restart GET-only recovery, unknown receipt-এ zero dispatch। Live-mode generation
বা supervision store-এ mock receipt/ack লেখা হয় না। L4.1/L4.2 standalone live data
support remains separate until actual live admission/supervision is available।

Session owns local close; context manager success/failure-এ close করে। Constructor
failure-তেও acquired transport close হয়। Failed cleanup-এ retained handle;
primary exception মুছে যায় না, subsequent local close retry করা যায়। Client close
remote job stopped দাবি নয়। Caller same private root/context রাখবেন; অন্য job/root
নিয়ে duplicate submission prevention নেই।

## Checks

Recent unchanged v2/transport evidence reused as baseline; initial combined 109
PASS, added lifecycle/context cases-সহ final **113 PASS**, new session **20 cases**:

```sh
.venv/bin/python -m pytest -q tests/test_comfy_offline_session.py tests/test_comfy_v2_executor.py tests/test_comfy_transport_composition.py tests/test_comfy_transport.py
```

[Tests](../tests/test_comfy_offline_session.py): no socket/DNS, preflight/intent/
receipt ordering, invalid admission, lost/malformed/unpersisted receipt, no resubmit,
GET-only restart, true/false/unknown cancel, preserved sidecar, fixture PNG provenance,
constructor/exit cleanup failure handle, closed/provenance rejection ও context mismatch।
Ruff/format, plan excerpt drift, docs links/RESUME length ও whitespace PASS।
Schema/requirements বদলায়নি; migration নেই। No install/GPU/model/network/billable run।
Existing dirty work preserved; commit নয়।

## Next ও প্রকৃত সীমা

Offline composition complete; live-mode durable executor integration, actual TLS/
auth/routes/runtime/GPU validation ও independent remote resource/time supervision
বাকি। Synchronous cooperative timeout hard total bound নয়; CPU dummy supervisor
remote server stop proof নয়। এই offline session সেই gaps বন্ধ করার দাবি করে না।
Next L4.4: live admission ও remote supervision-এর remaining gap/prerequisite review,
বর্তমান L4 scope-এ; readiness evidence ছাড়া live dispatch enable করা যাবে না।
Actual target/GPU owner-confirmed unavailable; একই GPU probe পুনরায় নয়।
