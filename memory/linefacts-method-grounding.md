---
name: linefacts-method-grounding
description: v14/v15 extraction is sentence splitting, observed binding def-use and AST enclosing guards; semantic obligations remain model hypotheses
metadata:
  type: project
---

2026-10-14: User asked for an exact extraction description. Implementation audit and real task-152 evidence
are documented in [METHOD_V14_V15.md](../trickcatcher_linefacts/METHOD_V14_V15.md). No pipeline code changed.

**How to apply:** describe implemented evidence precisely. Do not claim semantic atomic spec decomposition,
complete PDG/heap dependence, causal path proofs or tool-verified spec-to-predicate entailment. Clause IDs
and executable anchors validate grounding only within their documented limits. Existing frozen experiments
remain unchanged; any extraction improvements require a separate copy and preregistration.
