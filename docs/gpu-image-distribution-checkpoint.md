# Local image distribution preparation

2026-09-26। Local OCI export/verification micro-step সম্পন্ন; publish হয়নি।
Owner GHCR নির্বাচন করেছেন; namespace `arafat719` (owner: Arafat719)।

- Exact tested image ID থেকে Podman OCI export; no pull/install/build/push।
- Archive `/tmp/animation-gpu-health-45b4d841.oci.tar`, 53,340,160 bytes (~50.87 MiB)।
- [Evidence](../deploy/gpu-health/distribution-evidence.json)-এ archive checksum,
  OCI manifest digest, config/image ID ও layer count সংরক্ষিত।
- [Verifier](../scripts/verify_gpu_image_archive.py) extraction ছাড়া manifest/config/
  সাত layer-এর descriptor size/SHA256, platform/user ও tested image ID যাচাই করে।
- Export manifest digest স্থানীয় image manifest থেকে আলাদা; config/image ID একই।
  Registry upload-এর পরে returned manifest digest-ই final pull reference হবে।
- [Tests](../tests/test_gpu_image_archive.py): valid archive, corrupt layer,
  duplicate tar entries ও wrong image identity—4 PASS। Actual archive verification,
  ruff format/lint, docs links/plan drift/RESUME length/whitespace PASS।
- Existing 231-test source evidence ও owner-built image smoke retained; worker
  source/image অপরিবর্তিত। No new install/download/paid action/commit।

## GHCR publication প্রস্তুতি

[Official GHCR docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
অনুযায়ী OCI images supported; নতুন package default private। Proposed image name
`animation-gpu-health`, tag `health-45b4d841a9a3`; target `ghcr.io/arafat719/animation-gpu-health:health-45b4d841a9a3`।
Upload-এর আগে namespace/access এবং concrete artifact review দরকার; registry নির্বাচন
একা publish authorization নয়। Public visibility নিজে থেকে পরিবর্তন নয়।
Authentication owner terminal-এ; token chat/source/checkpoint-এ নয়। Local CLI-তে
PAT classic-এর প্রয়োজনীয় package permission বা approved existing auth ব্যবহার হবে।
RunPod private pull credentials-এর পরিকল্পনাও final preview-তে আলাদা করতে হবে।

পরের independent local micro-step: mock-tested lifecycle deadline/cleanup control;
namespace পাওয়া গেছে; concrete publication handoff পরের প্রস্তুতি। Paid create/stop/delete
এখন নয়। /tmp archive মুছে গেলে tested local image থেকে পুনরায় export ও verify করতে হবে।
Chat length নিয়ে owner-এর উদ্বেগ নথিভুক্ত: context অসংগতি হলে অনুমান করে edit নয়,
checkpoint মিলিয়ে owner-কে জানাতে হবে। বর্তমানে checkpoint/source evidence সঙ্গত।
