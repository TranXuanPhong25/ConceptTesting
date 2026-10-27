# Retrieval v2 engineering protocol — 2026-10-26

Registered before baseline or improved HumanEval retrieval outcomes are computed.

## Scope and earlier work

The user requests autonomous improvements until retrieval covers at least half
of HumanEval. Default cohort: the existing 113 DEV HumanEval PUTs used by
TrickCatcher. An optional clarification has been sent about the denominator and
whether bug-mechanism accuracy rather than conditional applicability is intended.
Until clarified, the target is conditional applicability hit@3 >= 57/113.

Earlier v17 and v31–v35 tested concepts/templates without robust test-generation
gain; v44/v47 also showed that generic concept/tool selection did not beat random.
This is a local retrieval engineering task, not a repeat of those efficacy runs.

## Input and leakage boundary

`evaluation/inputs.json` contains only task ID, entry point, original public PUT
source (including its specification docstring), and the deterministic development /
audit designation. No canonical solutions, HumanEval+ cases, hidden outcomes,
mined facts, existing witnesses, reference labels or other pipeline outputs enter
retrieval or relevance annotation. Existing upstream files are read-only.

The current 132-card corpus and lexical retriever are saved in
`evaluation/baseline_snapshot/`; hashes and input provenance are in `INPUTS.json`.
No paid model calls, benchmark paper reimplementation, or target program execution
is needed for retrieval.

## Relevance definition and labels

Before retrieval outcomes, manually annotate an acceptable concept set for every
task from public source/spec alone. A label needs a concrete operation/site and
a reason why the card's trigger gives a meaningful test question for this spec.
An operation that merely shares a token is insufficient: `return` does not make
finally handling relevant, and a statement-level `append` does not imply that
its None return was consumed.

Labels describe **conditional test relevance**, not a verified fault. A card may
identify a risk whose failing precondition still needs checking. Record this
distinction in labels and reports. Tasks without a defensible card remain in
the denominator as misses; do not force a generic fallback label. Annotations
are authored in a separate file and never loaded by the retriever.

## Development and audit

The fixed hash split in `INPUTS.json` determines development versus audit tasks.
Use development results to inspect defects. Freeze code, configuration, corpus
and labels before computing final audit scores. These are previously used DEV
tasks, so the audit is an internal engineering check, not a fresh held-out claim.
After the audit, report failures rather than tuning on audit outcomes.

Primary score: fraction of all 113 tasks whose top 3 contains a manually labeled
concept. Report development/audit separately, top-1/top-3, annotated ceiling,
unlabeled tasks, per-task ranks, and unfiltered lexical baseline on the same
inputs and labels. Always return at most 3 candidates for this comparison.

Also report a same-API search mode that uses only source-derived information;
do not use task IDs, an expected-card lookup table, gold labels, or grading
evidence as retrieval features. Cross-check changed function/variable names and
negative controls for obviously absent constructs. Preserve old smoke probes.

## Planned implementation

Implement in a new `retrieval_v2/` folder. Prefer standard-library AST inspection,
separate code/spec query channels and applicability gating over paid services.
Suppress cards requiring syntactic constructs or APIs absent from the source.
Add structural retrieval evidence for indexing, range bounds, comparisons,
numeric operations, mapping and string APIs. Evidence is explanatory and should
state uncertainty; it is not a bug diagnostic. Freeze generic rules without
HumanEval task IDs. Preserve lexical-only access for comparison.

Changes to the corpus require dated amendments and independent language/source
grounds, not one card per task. Report corpus expansion separately from ranking.

## Validation and success

Run relevant engineering tests and review applicability rules, query input
separation, scope handling and score computation before evaluation. Required
checks include preservation of the previous failure `values[len(values)]`,
scope-sensitive evidence, no execution of target source, and corpus provenance.

Success requires >= 57/113 applicability hits@3 and an honest score on the fixed
audit portion. It does not imply 50% bug detection, test generation or correct
root-cause identification. If corpus relevance limits the target, document that
ceiling instead of treating arbitrary candidates as successful retrieval.

## Amendment A — 2026-10-26, before any retrieval outcomes

Public code/spec inspection reveals corpus gaps: the original 132 cards mostly
describe linter pitfalls while these functions also need Python semantic contract
questions about character/byte domains, normalization, stable order and ties,
duplicate positions, empty reductions, rounding and numeric casts. Add a compact
generic extension from the same pinned CPython revision, including its built-in
functions documentation. These are explicitly **synthesized API/contract risk
cards**, not upstream bug-fix examples or confirmed bug categories.

Keep original corpus untouched. The extension and its provenance live under v2.
Report three comparisons: original corpus + original BM25, extended corpus +
BM25, extended corpus + structure-aware ranking. Per-task annotations record a
concrete source site and spec-based test question; no numeric outcome is used
to write them. Corpus design has seen public task source, including audit-task
source. Thus all cohort relevance results are development-informed engineering
results; the audit checks frozen ranking only, not unseen corpus design.

## Amendment B — user clarification, 2026-10-26, before retrieval scoring

The user explicitly selects **113 PUTs, and the concept must describe the actual
bug**. This overrides the conditional-applicability target above. Success is now
strict bug-mechanism hit@3 >= 57/113. The prepared applicability labels are kept
as `applicability_gold.json` and cannot establish success.

Ground truth must include concrete bug-mechanism bindings and a public-contract
witness. Execute witnesses in bounded isolated processes and compare with the
original HumanEval reference in a grading-only path. References, witnesses,
labels and outcomes never enter retrieval. A mere code-context match or a test
that happens to fail for a different reason is not a correct mechanism label.
Value-equal type-only cases, disputed input validity, timeouts and unclassified
mechanisms are reported separately rather than forced into positive labels.

The fixed 73 development / 40 audit designation remains. Freeze labels, corpus
and engine before final audit scoring; all 113 remain in the denominator.
Relevance labels are single-author and development-informed, so report that
limitation alongside reproducible witnesses. The strict label set is frozen
before either baseline or new HumanEval retrieval rankings are scored.

Additional generic cards may address genuine mechanism gaps exposed in public
source: occurrence/frequency state, index origin/stride/domain, selecting the
first candidate instead of the optimum, observing state after transformation,
literal chunks versus maximal runs, regex full-match boundaries, digit places,
and recursive base/progress handling. Their language/API sources must be pinned
and their design influence disclosed. Do not encode task IDs in the retriever.

## Amendment C — 2026-10-26, after first development score, before audit

The first 73-task development run yielded family-only hit@3 53/73 for v2,
20/73 for extended BM25 and 0/73 for original BM25. Preserve that first result.
These counts match concept IDs only and do not ensure that the returned source
binding is at the faulty operation. Add a stricter binding check: a positive v2
retrieval must return the labeled bug family and cite at least one manually
recorded faulty expression/site from the same confirmed witness. Records with
several sites remain review hypotheses, so separately report the first cited
site and any cited site. Bindings are authored from source and witness rationale,
never used by the engine. Keep initial ID-only metrics as secondary results.

The unscored audit set still has 40 tasks. Inspect and improve generic ranking
rules only using development failures, freeze implementation and binding labels
before audit, and do not tune after seeing audit results. Do not claim unseen
corpus generalization: corpus/labels have seen all public source, as already
disclosed in Amendment A. No independent agent review has been performed; final
results must identify single-author mechanism attribution as a limitation.
