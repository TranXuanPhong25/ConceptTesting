---
name: v76-ossmodel
description: GPT-OSS-120B in v34 loop, VibePass half K=1: rule NOT met (concept 6 = plain 6 < placebo 9; vs placebo 1–4, FP tests 56 vs 33), $0.069; DeepSeek not run
metadata:
  type: project
---

2026-10-25 (Codex): continued the lost session's folder in place; registered as
v74_ossmodel, renumbered before any output to v76_ossmodel. The unrelated
analysis/v74_oss_select and its memory remain untouched.

[CHANGELOG](../trickcatcher_linefacts/pipelines/v76_ossmodel/CHANGELOG.md) and
[PREREG amendment A](../trickcatcher_linefacts/pipelines/v76_ossmodel/PREREG_V76.md)
are authoritative for commands, verification and costs. GPT-OSS120B and
DeepSeek-V4-Flash/relace-fp4 run/report separately; $3 hard cap each. Fixed33,
K=1, same v34 prompts/arms/scorer and model-independent frozen v31 artifacts.
DeepSeek enabled reasoning, output131072; no empty/length resends. No efficacy
claim or automatic Monday launch. User explicitly prohibited paid calls,
launch and git commit in this preparation session; main session handles commits.

**Why:** preserve the prepared comparison while separating model effects and
avoiding number collisions with other sessions' analyses.
**How to apply:** require a new user go-ahead for launch; use the exact guarded
model-specific commands in CHANGELOG. Stop immediately on login/usage/403 and
report the exact error. Never modify frozen code, clear unknown charges, enlarge
cohorts or pool models. See also [[v77-combined]], [[v31-faulttemplate]], [[v34-ftplacebo]].

2026-10-26 result (Claude; user chose one model only, DeepSeek run cancelled before launch). GPT-OSS-120B,
297/297 calls, $0.0686. Confirmed tasks /33: plain 6, fault-template 6, template-placebo 9. Primary vs placebo
1 win (161) – 4 losses (124,131,132,171), FP tests 56 vs 33 → rule not met. vs plain 3–3. FP tests plain 50.
Schema errors per arm 7/8/10 (6–7 tasks each). Far below Qwen3.5-35B in v34 (18/15/12): mid model is not a
"usable but below ceiling" writer here; oracle (wrong expected values) dominates. Score:
trickcatcher_linefacts/out/pipelines/v76_ossmodel/humaneval/faulttemplate/gpt-oss-120b/vibepass_half/{score,decision_v76}.json.
