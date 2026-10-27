# V6 retrieval repair: user-authorized iterative development

2026-10-27. User explicitly requests autonomous implementation audit and
improvement based on returned results/error analysis. Copy v5 in a new folder;
preserve v2/v5 sources and their frozen outcomes. This is project code, not paper
reimplementation. No model/paid inference or hidden-test use in retrieval.

The old113 sources/labels and old audit have been inspected; all iterations below
are development-informed. Preserve each iteration source/config hashes, outputs,
wins/losses and quality tradeoffs. Never overwrite a run or call it held-out.
The user-authorized adaptation supersedes v5's own no-retuning instruction only
for this separate v6; v5 itself remains frozen. Labels are grading only.

Audit findings to address: requires/excludes largely not consumed; opaque large
legacy priorities dominate weak facts; syntactic context returns generic risks;
atom-level comparisons/first occurrence choose wrong sites; predicates on local
state masquerade as input shortcuts; inferred domains and first-index semantics
need support/contradiction checks; alternative ASCII syntax and unique-domain
membership are missing from eligibility; local origins miss outer-scope bindings
inside comprehensions. Several primitive-only negative fixtures did not test the
actual competing rankings seen in full functions.

Generic mechanisms, not task-ID rules: relative loop/index bounds; sentinel
initialization flowing to offset index use; unique-domain membership losing sorted
input multiplicity; ASCII literal-range guards; input-vs-local shape shortcuts;
public examples and neutral singleton/empty identities; early return versus
optimum in unordered iteration; selected-value .index versus current-index misuse;
coefficient value times length versus sequence allocation; compound/ternary
branch sites; unsupported rejection thresholds versus public requirements.

Rank by explicit semantic-support tier, then legacy relevance, not operation
presence alone. Emit ranking reasons and condition statuses; duplicate same-site
weak descriptions should not fill slots. Report modes with a stated coverage /
precision tradeoff. Do not describe static support as confirmed bug proof.

Before scoring each version: meaningful engineering regressions for false
positives, renamed functions/variables, correct versions, nested scope and data
flow; record review limits. After generation joins unchanged frozen labels,
report top1/family/site hits, returned-card label matches, fallbacks and per-task
changes. Expand evaluation only through separately reported native/manual quality
audits; do not silently backfill gold. No old40 utility result attributed to v6.

## Before iteration03 outcomes

Iteration02 correct-program controls reveal that the previous precise fallback
returns weak hypotheses on99/113canonical sources. Keep it as explicit `balanced`;
new `precise` returns only tier>=2 and moves unsupported suggestions to review.
This is abstention, not a safety declaration. Report all three policies.

Additional implementation corrections from review: branch-local definitions are
usable within the same dominating branch, not after its join; tuple assignments
retain component provenance; annotation builtin identity must be resolved;
comprehension-generator metadata needs its real containing source span. Operation
roles are checked for non-capturing/immediately-invoked lambdas, boolean-state
short circuits, scalar set cardinality, numeric position comparisons, deliberate
integer iteration bounds, non-half rounding, and encoding used for hashing.
Nonempty output requirements must not become input restrictions. Paired positive
and correct controls exercise these rules before scoring. No old labels edited.
