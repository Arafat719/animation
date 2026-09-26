# Publication completed — historical instructions below

2026-09-26: Owner login/push সম্পন্ন করেছেন। [Evidence](../deploy/gpu-health/ghcr-evidence.json)।
Registry manifest SHA256 ও tested config identity PASS। Installed Podman single-image
OCI parsing error দেয়; error-এ থাকা raw manifest bytes decode করে digest independently
মেলানো হয়েছে। নিচের পুরোনো manifest inspect command এই version-এ সফল নয়—পুনরায়
push করার প্রয়োজন নেই। Visibility/layer pull/real GPU এখনো যাচাই নয়।

# GHCR publication handoff — review-ready, not executed

2026-09-26। Scope: এক tested health-worker image GHCR-এ upload; no build/install,
cloud GPU launch, repository push বা visibility change।

## Concrete artifact ও destination

- Source image ID: `45b4d841a9a333f8d3be70dba655d17c474e607ea930a1b4d6e8eeaae6a45cef`।
- Destination: `ghcr.io/arafat719/animation-gpu-health:health-45b4d841a9a3`।
- Local image ~138.18 MiB; verified OCI archive ~50.87 MiB। Actual upload size
  compression/deduplication-সাপেক্ষ; exact bandwidth পূর্বমাপা নয়।
- Includes health worker source ও Python dependencies; কোনো project DB, personal
  assets, .env, registry/GPU token বা full repository context যোগ করা হয়নি।
- [Distribution evidence](../deploy/gpu-health/distribution-evidence.json),
  [local smoke evidence](../deploy/gpu-health/local-image-evidence.json)।

## আগে owner-এর প্রয়োজন

[GitHub official instructions](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
অনুযায়ী local CLI login-এর জন্য PAT classic-এর write:packages scope ব্যবহার করা যায়।
Token শুধু terminal-এর hidden password prompt-এ; chat-এ নয়। Repository permissions
বা delete:packages প্রয়োজন নেই এই handoff-এ। Existing package থাকলে owner তার
visibility private এবং target tag unused নিশ্চিত করবেন; tag থাকলে overwrite নয়।
নতুন GHCR package default private। Account quota/billing policy owner যাচাই করবেন;
এই proposal paid storage/plan subscription অনুমোদন নয়।

## Owner terminal command — upload অনুমোদনের পরে

যেকোনো directory থেকে block চালানো যাবে। এটি **আসল upload করবে**। Login password
prompt-এ GitHub password নয়, PAT classic দিতে হবে। Temporary auth directory শেষে
সরানো হবে; existing login files বদলানো হবে না।

```bash
(
set -eu
umask 077
publication_tmp=$(mktemp -d /tmp/animation-ghcr-auth.XXXXXX)
trap 'rm -rf -- "$publication_tmp"' EXIT
podman image exists 45b4d841a9a333f8d3be70dba655d17c474e607ea930a1b4d6e8eeaae6a45cef
podman login --tls-verify=true --authfile "$publication_tmp/auth.json" --username Arafat719 ghcr.io
podman push --tls-verify=true --authfile "$publication_tmp/auth.json" --digestfile "$publication_tmp/digest" 45b4d841a9a333f8d3be70dba655d17c474e607ea930a1b4d6e8eeaae6a45cef docker://ghcr.io/arafat719/animation-gpu-health:health-45b4d841a9a3
publication_digest=$(cat "$publication_tmp/digest")
printf '%s\n' "$publication_digest" | python3 -c 'import re,sys; assert re.fullmatch(r"sha256:[a-f0-9]{64}",sys.stdin.read().strip())'
podman manifest inspect --tls-verify=true --authfile "$publication_tmp/auth.json" "docker://ghcr.io/arafat719/animation-gpu-health@$publication_digest" > "$publication_tmp/manifest.json"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["config"]["digest"] == "sha256:45b4d841a9a333f8d3be70dba655d17c474e607ea930a1b4d6e8eeaae6a45cef"; print("Remote config identity PASS")' "$publication_tmp/manifest.json"
printf 'Verified image: ghcr.io/arafat719/animation-gpu-health@%s\n' "$publication_digest"
)
```

Last Verified image reference owner চ্যাটে দিতে পারেন; সেটি secret নয়। Token বা auth
file পাঠাবেন না। Upload সফল কিন্তু verification ব্যর্থ হলে uploaded artifact থাকতে
পারে—blind repush/delete নয়, error report করে remote identity যাচাই করতে হবে।
Script metadata fetch করে; image pull/install নয়। No registry upload executed in
this preparation step. Remote digest local OCI/export digest-এর সমান ধরে নেওয়া হয়নি।

## Checks ও পরের ধাপ

Installed Podman push/login/manifest inspect help-এ flags যাচাই; command block
`bash -n` PASS। Document links/plan drift/RESUME length/whitespace PASS। Source
implementation/image অপরিবর্তিত; আগের tests পুনরায় চালানো হয়নি। Actual login,
upload ও remote verification এখনও হয়নি।

পরের ধাপ: exact destination/artifact upload-এর owner approval ও terminal auth;
তারপর verified registry reference checkpoint। এর পরেও real lifecycle/watchdog,
private image pull configuration ও Phase 3/order gates মিটিয়ে 4.7 final করতে হবে।
