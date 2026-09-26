<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

## 2. Fixed product decisions

These decisions are already made. Do not ask again unless a technical blocker forces a change.

| Decision | V1 choice |
|---|---|
| Product | Smart AI animation studio/agent |
| Main flow | One prompt to finished scene |
| Output | 30–60 second video |
| Visual style | 2D Japanese anime |
| Character input | Text description and/or reference image |
| Character reuse | Save a character and reuse the same identity |
| Voice | Built-in voices and consented custom voice sample |
| Runtime | Hybrid: local control app plus rented cloud GPU |
| Local hardware | Must work without a local discrete GPU |
| First interface | Web app |
| Later interface | Desktop app after the web pipeline is stable |
| First audience | Owner-only private prototype |
| Build method | Codex implements the project phase by phase |

### V1 definition of done

The owner can enter one prompt, optionally select a saved character and voice, click **Generate**, watch job progress, preview individual shots, regenerate a failed shot, and export one 30–60 second MP4 with anime visuals, dialogue audio, basic lip-sync, and subtitles.

V1 does **not** require perfect movie-level motion or identity in every frame. It must instead be reliable, inspectable, resumable, and improveable.

---

## 3. Reality and core strategy

A reliable 30–60 second scene should not be generated as one long clip. V1 must build it as a sequence of short shots.

```text
User prompt
  -> structured story plan
  -> character and style references
  -> 6–10 short shot plans
  -> keyframe for every shot
  -> 3–6 second image-to-video clips
  -> dialogue audio
  -> lip-sync where a speaking face is visible
  -> FFmpeg composition
  -> final MP4
```

This shot-based design makes failed parts regenerable and keeps cloud cost under control.

---
