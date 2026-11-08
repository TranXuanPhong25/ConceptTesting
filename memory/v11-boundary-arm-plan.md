---
name: v11-boundary-arm-plan
description: User rejected V11 BOUND trial and deleted its worktree/code/outputs;historical10PUT result13valid/1bug
metadata:
  type: project
---

2026-11-06 latest user says to discard this worktree. Verified controllers were
terminal, then removed `/home/phong/dev/ConceptTester-v11-boundary` using
`git worktree remove --force`. Worktree registration, uncommitted trial code,
reports, execution cache and all trial outputs are deleted; only parent main
remains. No branch/commit/merge/push was created. Existing main code, BVA runs
and sealed plain baseline were not changed by removal. This direction is stopped;
do not recreate/resume it without a new user request. Paths in the historical
notes below refer to deleted artifacts; retained metrics are historical memory.

2026-11-06 latest user correction: intended dataset is existing BVA known-bug10,
not the earlier smoke6. Exact cohort274e5251... mapping2/6,11/1,16/4,23/7,72/4,
76/0,99/1,124/0,140/7,157/3. Unchanged V11BoundaryArm run COMPLETE10/10 in
worktree:13valid inputs/1bug task76 ((1,0)value disagreement and(0,12)timeout,
both repeat-stable),0new LLM/plain calls.40gaps/16reached,2007candidate traces.
BVA v5 earlier64inputs/4bugtasks comparison is descriptive/outcome-selected,
not efficacy. Replay with native execution forbidden passes;63sources/10freezes,
312prior BVA+113smoke files and1375baseline hashes verify. Nothing active or
committed/pushed. Worktree report:`final/review/v11_boundary_known_bug10_2026-11-06.md`;
outputs:`final/out/v11_boundary_known_bug10_20261106`. Use this10PUT cohort for
the user's current boundary test set. Earlier wrong-scope smoke history follows.

2026-11-06 latest user requests scoring/retry. Scored smoke6 COMPLETE using the
4previously frozen witnesses and corrected HumanEval+v0.1.10 with two repeats:
4valid novel inputs/0detected PUTs;0rejections/instability/errors.16native
reference/evaluation executions,0model/tokenizer/keepalive calls, no new plain
or generation. Read-only replay passes with execution forbidden;30extraction
files,exactfreeze and1375parentbaseline hashes verify. No expansion/commit/push.
Worktree report:`final/review/v11_boundary_scored_smoke_2026-11-06.md`;
outputs:`final/out/v11_boundary_scored_smoke_20261106`. Earlier extraction follows.

2026-11-06 user authorizes a new worktree trial. Implementation is uncommitted in
`/home/phong/dev/ConceptTester-v11-boundary`, detached from main/a7bda92b; parent
main has independent ongoing changes and must not be reset/overwritten. New
`v11_boundary` arm uses original V11 kernels unchanged in a dedicated sandbox,
legacy base variations/current public contracts, fixed task-budget shares,
two fresh witness replays and instrumentation-fidelity checks. No LLM/keepalive.

220 modular checks and17 safety/development checks pass;7 development checks
skip because their local cohort/build is absent from the worktree. Existing
source-selected6PUT smoke extraction completes:4inputs on tasks0/99;5/18 have no
observed BOUND probes,81/120 have gaps but no witness.12gaps/4reached,1118candidate
traces.0model/reference/scoring calls, not an efficacy result. Read-only replay,
63source/6freeze hashes and1375sealedbaseline files verify. Report in worktree:
`final/review/v11_boundary_arm_2026-11-06.md`; artifacts under
`final/out/v11_boundary_extraction_20261106`. Original assessment follows.

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
