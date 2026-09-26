<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

### Phase 5 — প্রথম real anime image, তারপর character consistency

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 5.1 | আগে উল্লেখ করা প্রায় 13 GB model এখনও পাওয়া গেলে তার exact path/size/identity/license/format verify করবে; না পেলে missing হিসেবে report করবে | উপস্থিতি অনুমান নয়; duplicate download নয়; findings documented |
| 5.2 | ImageProvider mock contract বানাবে | provider tests pass |
| 5.3 | ComfyUI API-format minimal image workflow বানাবে | workflow validates |
| 5.4 | একটি text prompt থেকে একটি low-cost anime image বানাবে | valid image; model/seed recorded |
| 5.5 | 1.12/1.13-এর artifact delivery/preview ব্যবস্থায় real image result যুক্ত করবে | refresh-এর পর real image artifact থাকে; fixture সীমা আরোপ করে real output ভুল দেখানো নয় |
| 5.6 | reference image upload validation যোগ করবে | wrong type/size rejected |
| 5.7 | description থেকে character profile বানাবে | traits database-এ save হয় |
| 5.8 | reference conditioning দিয়ে দ্বিতীয় pose বানাবে | একই character recognizably থাকে |
| 5.9 | five-pose character sheet বানাবে | hair/eyes/outfit checklist human review pass |
| 5.10 | approve/regenerate/edit prompt/lock seed controls বানাবে | approved keyframe immutable থাকে |
| 5.11 | পাঁচটি shot keyframe test করবে | video generation-এর আগে সব approved |

## Phase 5 — Character creation and consistent keyframes

### Codex tasks

1. Implement `ImageProvider` and a ComfyUI-workflow adapter using API-format JSON.
2. Reuse a verified existing model if suitable; do not redownload duplicate weights.
3. Support:
   - text-only character creation;
   - reference-image-guided creation;
   - character sheet generation with front, three-quarter, side and expression views.
4. Store immutable visual traits and inject them into each shot.
5. Generate one approved keyframe per shot before any video generation.
6. Benchmark at least two consistency methods behind the provider boundary:
   - reference conditioning such as IP-Adapter/InstantID where compatible;
   - a modern image-edit/identity-preserving model such as Qwen-Image-Edit where hardware and license permit.
7. Do not train a LoRA in the first pass. Add LoRA training only if reference conditioning fails a documented consistency test.
8. Add manual **Approve**, **Regenerate**, **Edit Prompt** and **Lock Seed** controls.

### Acceptance gate

- One saved character appears recognizably consistent across at least five different shot keyframes.
- Hair, eye color, main outfit and accessories match the CharacterProfile.
- All keyframes preserve seeds and model metadata.
- No video GPU time is spent before keyframes are approved.

---
