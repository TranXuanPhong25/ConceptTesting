# v17_templates

Compiler-owned semantic concepts, copied from v16_behavior_ready. Earlier results remain frozen.
See root PREREG (2026-10-15 v17), CHANGELOG, CPU_VALIDATION.json.

LLM call 1 sees only spec-unit IDs, parameter names and nine reusable template definitions.
It chooses template parameters and supporting unit IDs. Tool assigns raw source spans, verifies
all captured public base cases (cap 200), and compiles typed semantic alternatives. LLM call 2
chooses proposal/fault/source-block IDs and an explicit gap rationale. Tool compares model outputs
to obtain discriminators, checks actual PUT execution and requires an observed source anchor.
No expression-tree generation, copied quotes, or implementation mutant prerequisite.

The registry has no task IDs/function names. Models are candidate spec interpretations, not oracle
proofs. Source units are paragraphs, not claimed atomic obligations. The finite observed behavior
machine remains an under-approximation; this run does not implement complete symbolic execution
or MCTS. No MOVE-CHECK semantics or author-paper reproduction is claimed.

Nine templates cover map, filter, reduce, order/multiplicity, balance, segmented counting,
count comparison, neighborhood selection and containment. Unsupported requirements abstain.
The first-order semantic mutations include filter bypass, boundary/aggregate/index/member changes,
duplicate removal, guard omission, order/selection and subset/equality alternatives.

CPU: 44 tests pass; representation gate 17/20. A manual compiler-only positive control on task 152
passes all four base inputs; it is not an LLM proposal or accepted-card result.

```bash
python3 -B -m trickcatcher_linefacts.pipelines.v17_templates.behavior_experiment all --online --workers 2
```

Use only the user's live Qwen environment. Two proposals/task, gate >=10/20 qualified tasks before
seven-arm generation. Same strategy/domain/selection budget for all LLM arms. Concept activation
is measured after selection. Common 12-input witness pool is shared by toolinput/witness-only.
Witness-only has no generation LLM calls; proposal/discovery costs are shared and must still be reported.
Primary contrast behavior+concept vs behavior; D_IO uses unchanged saved spec-only refs. Canonical
property validation is separate and enters only after generation freezes. Invalid candidate properties
must not be counted as confirmed bugs. Full gate/cost/score records are under out/humaneval/behavior_smoke.
