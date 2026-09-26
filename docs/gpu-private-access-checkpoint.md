# Private image access preflight

2026-09-26। Read-only image-access micro-step সম্পন্ন।

## Evidence

- GHCR anonymous pull-token request HTTP 401; stored credentials ব্যবহার হয়নি।
  আগের authenticated registry manifest SHA256/config identity PASS।
- এই evidence credential-free access blocked প্রমাণ করে; GitHub package settings-এর
  visibility সরাসরি query করা হয়নি। Private path ধরেই deployment প্রস্তুত হবে।
- [Evidence](../deploy/gpu-health/ghcr-evidence.json)। কোনো image pull/install নয়।

## Concrete deployment access plan — এখনও execute নয়

- Registry: ghcr.io; username: Arafat719; image:
  `ghcr.io/arafat719/animation-gpu-health@sha256:00d8030ad886682f972486d7700b7d7e5c3c8df23c4baf3d8c38b9fdbf9b568b`।
- [GitHub docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
  অনুসারে PAT classic read:packages এবং account-এর package read access ব্যবহার।
  Upload token-এর write scope runtime pull-এর জন্য প্রয়োজন নেই। Short-lived আলাদা
  read token owner নিজে provider registry-credentials UI-তে দেবেন; chat/source নয়।
- [RunPod template docs](https://docs.runpod.io/pods/templates/manage-templates)
  অনুসারে private image-এর registry credentials আলাদাভাবে attach করতে হবে।
  Local Podman login RunPod-এ নিজে থেকে পৌঁছায় না। কোনো credentials/template এখন
  তৈরি বা provider-এ সংরক্ষণ করা হয়নি।
- Registry token শুধু image pull-এর জন্য; worker ANIMATION_GPU_TOKEN আলাদা random
  secret; RunPod management API key-ও পৃথক। Registry token worker env-এ নয়।
- Worker command explicit host override: python -m uvicorn
  animation_studio.workers.gpu_health:create_app --factory --host 0.0.0.0 --port 8091।
  Port 8091/http, provider HTTPS proxy ও worker Bearer auth; অন্য ports প্রয়োজন নেই।
- Image-এ no inference operations; /health,/devices,/capabilities-only। Registry
  success NVIDIA utility injection বা actual GPU health সফল হওয়া প্রমাণ করে না।
- Experiment শেষে no-redeploy সিদ্ধান্ত হলে owner ওই dedicated read token revoke
  এবং provider credential record remove করবেন; shared credentials স্পর্শ নয়।

## Remaining readiness

Live lifecycle control/independent shutdown fallback এখনও implement/test হয়নি;
বর্তমান deadline controller শুধু mock। Final quote/region/account credit/tax এবং
Phase 3/order prerequisite-ও বাকি। তাই এখন owner-কে token creation বা paid launch
করতে বলা হচ্ছে না। পরের local micro-step: real REST stop/terminate/inspect protocol
adapter **mock HTTP transport-এ** implement/test; create/live calls disabled থাকবে।
তারপর watchdog/recovery integration প্রয়োজনমতো এক micro-step-এ। একই readiness
review বারবার নয়; next কাজ source implementation।

Checks: anonymous denial observed; sources/access scope/doc links/plan drift/
RESUME length/whitespace PASS। Docs/evidence-only, app tests পুনরায় নয়। Existing
source/image/231-test ও lifecycle 99-test evidence retained। No install/download/
secret read/publication/provider mutation/paid action/commit।
