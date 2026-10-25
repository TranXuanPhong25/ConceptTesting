---
name: v60-v61-qwen-open-directions
description: 2026-10-25 open directions on Qwen (Codex reviews, no Claude subagents): v60 behaviour facts no signal (concept 12 vs spec-fact placebo 13), v61 interpretation no-go (11 vs 12/12)
metadata:
  type: project
---

User 2026-10-25: try the open directions, Qwen only, no Claude subagents ("quá tốn"); review by Codex (`codex exec -s
read-only ... < /dev/null`; without stdin closed it hangs). v60 (code-blind Qwen generator + FACT lines from the PUT):
blind 5, concept 12, placebo (spec facts) 13, code 10 /33, FA 0 → no signal; generic fact-block effect, not PUT content.
v61 (v55 design on Qwen: defn reused from v49 vs interp vs formatting placebo): 12/11/12, FA 108/104/104, common-mode
2/2/2 → no-go. Both Codex reviews found freeze-scope must-fixes (hash answers + all external inputs) — apply by default.

**Why:** closes the last open concept directions for this cohort; see [[concept-effect-synthesis]], [[v59-blind-concept]].
**How to apply:** do not run Claude subagents for writers/reviewers unless the user asks; use Qwen endpoints + Codex
review. Remaining open: v55/v56 (other session, Codex). Artifact nodes for v59–v61 still to add (live version is newer;
read it fully before republishing).
