<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

### Phase 0 — প্রাথমিক discovery; বর্তমান resume point নয়

নিচের মূল discovery checklist ঐতিহাসিক reference হিসেবে রাখা হয়েছে। `0.1` ও code inspection আগে হয়েছে; 0.2–0.4-এর সম্পূর্ণ পুরোনো inventory report এই audit-এ পাওয়া যায়নি। তাই সব row-তে নতুন PASS বসানো হয়নি। প্রয়োজনভিত্তিক inventory refresh করা যাবে; বর্তমানে 0.1 থেকে ধারাবাহিক restart বা পুরোনো minimum-install proposal পুনরায় দেওয়া লাগবে না।

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 0.1 | বর্তমান folder এবং Git status দেখবে | কোন file আছে/নেই তার সংক্ষিপ্ত বাংলা তালিকা |
| 0.2 | OS, CPU, RAM ও GPU তথ্য দেখবে | exact detected specification report |
| 0.3 | free disk space ও বড় AI file খুঁজবে | model path, name ও size report; কোনো load নয় |
| 0.4 | Python, Node, npm, Git, FFmpeg ও Docker version দেখবে | installed/missing table |
| 0.5 | existing code/package manifest পড়বে | reusable এবং missing অংশ আলাদা list |
| 0.6 | Phase 1-এর minimum install proposal দেবে | কোনো install না করে মালিকের অনুমতি চাইবে |

## Phase 0 — Discovery and feasibility report

### Codex tasks

1. Locate existing animation folders, virtual environments, downloaded weights and code.
2. Record, without exposing secrets:
   - OS/version;
   - CPU and RAM;
   - disk size and free space;
   - GPU and VRAM, if any;
   - Python/Node/npm/Git/FFmpeg/Docker versions;
   - existing model names, exact paths and sizes;
   - existing package manifests and Git status.
3. If the previously reported approximately 13 GB model can still be located, identify its exact path, size, format and completeness. If absent or unverified, record that fact; do not assume it exists, load it or download a replacement as part of discovery.
4. Create a concise gap analysis and recommend only the prerequisites needed for Phase 1.
5. Estimate disk requirements separately for source code, model cache, intermediates and final media.

### Acceptance gate

- A report contains exact evidence, not guesses.
- No file or system change has occurred.
- The owner approves creating or modifying the project.

---
