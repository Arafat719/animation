<!-- Generated from AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md; do not edit directly. -->
<!-- Refresh: python3 scripts/build_plan_docs.py -->

### Phase 7 — voice; built-in আগে, clone পরে

| Step | Codex শুধু এই কাজ করবে | Pass check |
|---|---|---|
| 7.1 | TTSProvider mock contract বানাবে | provider tests pass |
| 7.2 | একটি built-in voice ও একটি supported language select/verify করবে | license/language documented |
| 7.3 | এক line dialogue generate করবে | clear audio and metadata |
| 7.4 | timing/duration record করবে | dialogue timeline-এ বসে |
| 7.5 | UI-তে built-in voice preview বানাবে | select and play works |
| 7.6 | custom sample upload validation ও consent checkbox বানাবে | consent ছাড়া save/use blocked |
| 7.7 | sample normalization ও private storage বানাবে | public URL দিয়ে access করা যায় না |
| 7.8 | একটি consented custom voice isolated test করবে | owner human-review result records |
| 7.9 | Delete Voice Data feature বানাবে | active copy deletion verified |
| 7.10 | multiple dialogue lines generate করবে | speaker/order/timing correct |

## Phase 7 — Built-in voice and consented voice cloning

### Codex tasks

1. Implement `TTSProvider` with separate built-in and custom voice adapters.
2. Require explicit consent confirmation before saving or using a custom voice sample.
3. Validate uploaded audio type, duration, sample rate and clipping; normalize a private working copy.
4. Start with one supported language and one built-in voice. Add languages only after a pronunciation test set passes.
5. Benchmark candidate TTS models for the required language. F5-TTS is a private-prototype candidate, not an approved dependency. Verify the exact selected code and weight licenses before use; do not assume a family-level license claim applies to every version or permits production use.
6. Generate dialogue per line with speaker, emotion hint, duration and timestamps.
7. Store private voice samples outside public/static directories and exclude them from logs and Git.
8. Provide **Delete Voice Data** and verify deletion from active local storage.

### Acceptance gate

- Built-in voice generates clear timed dialogue.
- A consented custom sample produces recognizably similar private-test speech.
- Unsupported language/model combinations fail clearly.
- Voice data is never publicly reachable.

---
