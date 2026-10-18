---
name: linefacts-v21-flowtools
description: v21_flowtools done 2026-10-18 — P1 tools + Qwen diag16/pilot20 all 10 arms; negative/inconclusive, no concept gain; expected values are the bottleneck
metadata:
  type: project
---

2026-10-18 (Claude): implemented all of `trickcatcher_linefacts/PLAN_FLOW_HYPOTHESIS_TOOLS.md` in
`pipelines/v21_flowtools/` (P1 CFG/trace/tool dispatcher/packages + `flow_run.py` online runner). Report:
`trickcatcher_linefacts/analysis/v21_flowtools_results.md`; PREREG amendments 1–3 in the folder.

- diag16: ceiling, toolinput = concept+input+hyp = 7/7 buggy (11 vs 4 false alarms).
- pilot20: confirmed tasks 1–4/20 per arm, false alarms 19–38; agent-tools 4, flow+input 4, toolinput 3, plain 2.
  No concept arm beats toolinput+plain+placebo → negative/inconclusive, not promoted over v7.
- Lessons: Qwen fences nested JSON (accept one fenced object); 7B writes bare argument literals (normalize
  arm-neutrally or the no-example arms lose ~40% inputs); cache slots must include the prompt digest; concurrent
  writers need unique temp names. Protocol fingerprint hashes all *.py → any .py edit invalidates ledgers.

**Why:** user asked "implement đi" then "làm nốt đi" with an endpoint.
**How to apply:** do not rerun these cohorts; next idea must target expected-value correctness (oracle side),
not more structural evidence. Related: [[linefacts-v23-diagnostic]], [[abstract-concept-direction]].
