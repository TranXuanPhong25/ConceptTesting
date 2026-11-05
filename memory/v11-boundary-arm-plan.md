---
name: v11-boundary-arm-plan
description: Read-only assessment of extracting V11 BOUND/witness search as a current input arm; no implementation or run
metadata:
  type: project
---

2026-11-05 user asks which changes would be needed to bring V11 boundary-input
search into an arm. Assessment only; no source changes/model calls/benchmark.

Current extension points: `final/src/modular/arms`, `MethodInputGenerator`, and
shared freeze/reference/evaluation. Proposed scope is an isolated BOUND-only
producer returning concrete fuzz witnesses, with per-PUT trace evidence and
task-budget allocation. A separate LLM-guided producer would be a different arm.

Original implementation pointers: `trickcatcher_linefacts/pipelines/v11_fair/`
`tracer.py` (`__c`, `_probes`, `instrument`), `facts.py` (`describe`, fuzz helpers),
`v4_facts.py` (base-invariant flip + first witness). Do not invoke the whole fact
builder merely to filter BOUND afterwards: it also runs mutations/other kinds.
Trace imports change process resources/signals, so execute in a sandbox worker.
Current output cache stores oracle/evaluation results, not BOUND probe cells.

Distinguish sampler paths: legacy facts uses type-aware base variations; V4 fair
uses Hypothesis with previously mined strategy/validity. A zero-model producer
using current contracts/base variations is an explicit adaptation, not an exact
V4 reproduction. BOUND uses constant offsets -1/0/+1 (including float probes),
not nearest-float BVA. Operand-vs-operand equality is REL in the original code.

**How to apply:** preserve original sources and old artifacts; any future arm
must declare source/config dependencies, trace budgets and sampler identity.
Historical whole-V11 comparisons do not establish BOUND-only efficacy.
