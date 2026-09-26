<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

## 8. Model policy

Models change quickly. Treat every model as a provider implementation, not the product architecture. The candidates, hardware estimates and technical links below were not revalidated in this documentation-only audit; verify exact official versions, licenses and hardware needs before selection or use.

### Initial candidates, not permanent commitments

| Need | Candidate | Use in plan |
|---|---|---|
| Visual workflow engine | ComfyUI | Versioned API-format workflows |
| Character reference | IP-Adapter / InstantID | First consistency benchmark where compatible |
| Character-aware image edit | Qwen-Image-Edit family | Second benchmark if VRAM/license allow |
| Image-to-video | Wan2.2 TI2V-5B | Initial 24 GB-class GPU candidate |
| Alternative video | LTX-Video/LTX-2 | Speed/quality benchmark candidate |
| Voice clone prototype | F5-TTS | Private test only until licensing is resolved |
| Lip-sync | MuseTalk | Anime benchmark required |
| Composition | FFmpeg | Required deterministic media layer |

Before installing or running a model, Codex must record the verified preflight information:

- official source and exact model/version;
- code license and weight license;
- commercial-use restriction;
- minimum/recommended VRAM;
- disk size and checksum;
- supported languages and resolutions;
- estimated benchmark GPU time and maximum permitted cost;
- known safety or quality limitations.

After an approved benchmark, record measured GPU time, actual cost and quality separately from estimates. A proposal cannot claim measurements from a test that has not run.

Never download an unverified executable, pickle, custom node, or model from an unknown source. Prefer safetensors and pinned official repositories.

---
