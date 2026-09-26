# প্রয়োজনীয় অংশটুকু পড়ার সূচি

শুরু: [RESUME](../RESUME.md)। সব link একসঙ্গে খুলবে না।

| প্রয়োজন | নথি |
| --- | --- |
| Implementation rules, tests, security, cost | [rules](rules.md) |
| Product decisions / V1 scope | [product](product.md) |
| Components, boundaries, layout | [architecture](architecture.md) |
| Canonical data fields | [contracts](contracts.md) |
| Model selection / download কাজ | [models](models.md) |
| Discovery (historical; default restart নয়) | [Phase 0](phase-0.md) |
| Skeleton | [Phase 1](phase-1.md) |
| Composer | [Phase 2](phase-2.md) |
| Planner / state machine | [Phase 3](phase-3.md) |
| GPU worker | [Phase 4](phase-4.md) |
| Character / keyframes | [Phase 5](phase-5.md) |
| Video clips | [Phase 6](phase-6.md) |
| Voice | [Phase 7](phase-7.md) |
| Lip-sync | [Phase 8](phase-8.md) |
| End-to-end pipeline | [Phase 9](phase-9.md) |
| Stability / desktop | [Phase 10](phase-10.md) |

প্রতিটি phase file-এ মূল plan-এর micro-step table এবং detailed tasks/gate দুটোই আছে।
এসব requirements, completion status নয়; বর্তমান অবস্থা RESUME/ledger-এ।

Generated files সরাসরি edit করবে না। Master requirements বদলালে
`python3 scripts/build_plan_docs.py`, এরপর `--check` চালাবে। RESUME ও ledger
মানুষ/agent হালনাগাদ করবে; generator completion অনুমান করে না। নতুন step শেষে
RESUME-র next phase/source/check links বদলাবে এবং ledger-এ evidence রাখবে।

পূর্ণ audit, later roadmap, report template বা official reference list দরকার হলে
[master](../../AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md)-এর সংশ্লিষ্ট heading পড়বে।
