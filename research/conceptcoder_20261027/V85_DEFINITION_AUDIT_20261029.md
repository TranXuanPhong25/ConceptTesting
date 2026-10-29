# ConceptCoder definition versus V85 concept cards

2026-10-29. Read-only primary-paper and source audit; no paper reimplementation,
training, annotation execution or new model calls. The current cards are useful
**conditional bug-pattern knowledge**, but V85 does not establish that their
semantic conditions have been instantiated or covered. They fit the broad idea
of concept-guided testing; they are not equivalent to ConceptCoder's measured
concept labels or learned concept architecture.

## What the paper means

[§2.1](https://arxiv.org/html/2603.23470v1#S2.SS1) defines a concept as a
“human-understandable, semantically meaningful property” and, more generally, a
discrete or continuous value mapped from an input. It is above raw tokens and
less task-specific than the final label. The scope explicitly includes structure,
control/data flow, behavior, resource/API usage, and safety properties. For their
learning setting they additionally require semantics that domain tools can compute
to obtain supervised labels. **Different granularity is allowed by the general
definition; statement-level multi-hot labels are their concrete instantiation.**

Their Table1 labels include memory allocation, memory free, null check, buffer
access and bounds check. A buffer access is a concept even when the program is
correct; it is not synonymous with buffer overflow. A bounds-check label does not
certify that the check is sufficient. This distinction is central to our transfer.
[§2.2](https://arxiv.org/html/2603.23470v1#S2.SS2) defines the per-statement multi-hot
labels, sigmoid concept predictions and BCE supervision.

[§2.4](https://arxiv.org/html/2603.23470v1#S2.SS4) provides the other important
example: branch-prediction concepts abstract runtime values for a particular
input. The paper explicitly says it collects executions and maps concrete values
to abstract labels. Examples include zero, positive/negative ranges, null and
boolean outcomes. They describe program state, not a final bug verdict.

The actual method includes supervision and a particular information path:

| Setting | Evidence | Consequence for claims about V85 |
|---|---|---|
| VD sequential | [§2.3](https://arxiv.org/html/2603.23470v1#S2.SS3); local [VD forward](../../ConceptCoder_org/code/concept_learning/VD/statement_level_sequential_multi_tasking.py#L182), lines182–243 | Per-line concept logits are **averaged as raw logits**, then the task classifier consumes them. Concept BCE and task CE are jointly optimized. V85 has no such learned bottleneck. |
| BP parallel | §2.4; local [BP forward](../../ConceptCoder_org/code/concept_learning/BP/statement_level_parallel_multi_tasking.py#L175), lines175–211 | The task head consumes hidden states directly; concepts supply auxiliary supervision. Not every ConceptCoder experiment is a bottleneck. V85 also lacks this training objective. |
| Prompting | [AppendixA.4](https://arxiv.org/html/2603.23470v1#A1.SS4) | The paper tried hierarchical concept prompting and says it “does not help enough.” Prompt cards cannot inherit the training result as evidence of effectiveness. |

The author annotator is heuristic, not a sound verifier: e.g. `alloc`/`free` callee
name matching and bounds comparisons involving index/length-like variables
([VD annotator](../../ConceptCoder_org/code/design_concept/design_and_annotate_VD_concepts.py#L65),
lines65–131). Therefore the appropriate transfer is **defined, inspectable
semantic measurement**, not a claim that every concept must be perfectly proven.
The local code has eight VD categories rather than the paper's seven
(lines26–34), and fourteen BP labels rather than twelve
([BP map](../../ConceptCoder_org/code/design_concept/design_and_annotate_BP_concepts.py#L226),
lines226–240). These discrepancies reinforce the need to specify our own vocabulary
and extractor behavior rather than claim literal reproduction.

## Where current V85 is aligned, and where it is not

A reusable `where/how/what` card defines a mechanism, possible consequences and
candidate test actions. This can be a **concept definition or a family of related
concepts**. It is not automatically a measured concept instance for the target.
The existing `evidence_status=curated_hypothesis` is an honest description.

1. **The original cards often contain the right conditional semantics.**
   `py.mutable-default`, for example, states mutation and expected independent
   calls as preconditions, and explicitly allows intentional caches. That is
   stronger than merely saying a list default is a bug.
2. **The delivered representation drops those separate fields.**
   [compact()](../../python_bug_concepts/retrieval_v3/prompts.py#L22), lines22–24,
   retains title, where summary, mechanism, observable failure and trigger, but
   not `where.preconditions`, `applicability_notes`, `what.oracle_template` or
   `required_bindings`. Some summaries carry caveats themselves; the omitted
   fields are nevertheless not guaranteed to reach the tester.
3. **V85 does not bind the declared mechanism.**
   [adapter](../../trickcatcher_linefacts/pipelines/v85_retrievalhybrid/retrieval_adapter.py#L15),
   lines15–36, takes the first retrieval evidence span, attaches the first ranked
   unused v11 fact whose line falls inside it, and otherwise creates a `STMT`
   line-reachability target. It never checks whether that fact's predicate means
   the card's semantic trigger. Same location is weaker than same property.
4. **That proxy controls whether another round happens.**
   [hybrid loop](../../trickcatcher_linefacts/pipelines/v85_retrievalhybrid/run_v4.py#L219),
   lines219–248, sets `missed` from zero `shown_hit_counts`, uses its size as the
   strategy budget, and accepts candidates satisfying the chosen fact's hit.
   Executing a line can consequently suppress round2 even when no input has
   tested the card's relevant semantic distinction.

The parent's [saved-artifact mechanism audit](../../python_bug_concepts/research/v85_concept_quality_20261029/MECHANISM_AUDIT.json)
records275card bindings:206STMT fallbacks, of which204 are hit by round1;69same-line
v11 bindings, of which51 are hit.94/113tasks hit all proxy gates, including29tasks
with no primary-ref confirmed bug. Retrieval runs round2 on19tasks versus60for
v11. These are descriptive observations, not proof that stronger semantic gates
would improve detection. They do show why **fewer model calls cannot be used as
an independent measure of concept understanding**.

The parent also isolates a separate oracle failure: retrieval loss task91 has
seven saved input-only (`d_i`) bug inputs but no primary-ref confirmation; its
emitted reference oracle values are wrong. Eight other retrieval-only losses
lack a saved `d_i` bug input. This is a stage diagnosis, not a proof that the
concept representation caused those eight failures. Concept-base changes cannot
by themselves repair a shared-reference oracle failure.

Line execution is itself a legitimate control-flow property under §2.1. The
problem is not that it is “not a concept”; the problem is substituting it for a
different declared concept such as multiplicity sensitivity or sentinel handling.
Likewise, a correct program can contain a useful concept. Demanding that every
retrieved concept be an actual bug confuses concept presence with the downstream
verdict; measure risky applicability separately.

## An equivalent semantic representation for testing

The following is a proposed adaptation, **not implemented ConceptCoder code or a
claim of architectural/performance equivalence**. Retain the card as reusable
knowledge, but instantiate a named variable with a domain, scope and evidence:

`OBS = (property, bindings, value, evidence, scope)`

`REQ = (required relation, bindings, evidence from public specification, status)`

`TEST = (input partition or contrast, realization predicate, required oracle)`

OBS describes what code does or what an observed execution realizes. REQ describes
what the supplied specification requires; if unclear, mark it unknown. TEST is an
action derived from the concepts, not itself a concept label. A conflict between
OBS and REQ is a **hypothesis** until a valid test/oracle establishes a failure.

Evidence scope matters: an AST finding, one observed trace and an all-input
semantic guarantee are different claims. `unknown` must differ from false.
A natural-language requirement is not automatically tool-computable merely
because we place it in JSON; extraction reliability needs its own audit. Public
specification concepts extend the paper's code-property setting and should be
identified as our adaptation.

| Existing card | Measurable OBS concept | Separate REQ concept | TEST and faithful realization target |
|---|---|---|---|
| [`py.set-loses-multiplicity`](../../python_bug_concepts/data/concepts.json#L4106) | At a bound collection/result: `multiplicity_representation ∈ {preserved, collapsed_by_equality, unknown}`; a set conversion is static evidence of collapse at that operation, not proof that the final answer loses counts. | `required_collection_semantics ∈ {set, multiset, sequence, unknown}` for that result. | Construct legal inputs with equal support and different multiplicities. Realization means the changed multiplicity reaches the bound operation/result path, not merely executing its line. If the contract asks unique membership, collapsing is benign. Split the current card's duplicate-literal/copy-paste concern from multiplicity loss: those are different mechanisms. |
| [`py.negative-index-sentinel`](../../python_bug_concepts/data/concepts.json#L1233) | `index_origin=search_result`; on an input, `search_status=missing` and `index_value=-1`; independently record whether that value reaches a subscript. These can be multihot properties or a relation with argument bindings. | `missing_item_policy ∈ {sentinel, exception, omit, other, unknown}` from the target contract. | A missing-search case over a nonempty sequence; target `missing result reaches indexing without the intended guard`. Deliberate `seq[-1]` is a benign negative index, and line execution does not distinguish the cases. |
| [`py.mutable-default`](../../python_bug_concepts/data/concepts.json#L4) | `default_object_lifetime=shared_between_omitted_calls`; separately `default_mutation ∈ {observed, not_observed, unknown}` at a named parameter. | `call_state_policy ∈ {independent, intentionally_shared, unknown}`. | A two-call sequence omitting that parameter; realize a mutation in the first call and observation of persistent state in the second. This requires state-preserving sequence execution. A harness that only runs isolated single calls must mark the obligation unsupported, not pretend that a line-hit covers it. |
| [`py.index-origin-domain`](../../python_bug_concepts/retrieval_v2/data/extra_concepts.json#L1077) | Named coordinate has `origin ∈ {zero, one, unknown}`, `unit ∈ {position, value, ordinal, unknown}` and a separate stride phase. | Required origin/unit/phase for the quantity in the public spec. | An admissible pair on which the candidate interpretations disagree, with the specific dimension observed. Do not combine origin, rank, parity and stride into one always-true “indexing” coverage bit. |

The closest definition-level equivalence is an abstraction function
`alpha(code, input, trace) -> OBS` with explicit concept value domains. For static
properties omit input/trace; for dynamic properties retain the input and scope.
A concept-aware test planner can then consume these values and REQ relations.
This adopts ConceptCoder's interpretable intermediate-property discipline while
changing the downstream task and inference machinery. It does not reproduce its
learned representation or imply the same gains.

## Smallest evidence-driven change to assess next

First fix the **meaning of coverage**, then decide whether prose needs revision:
retain reachability as a separate diagnostic; only claim semantic realization
when the target actually measures the declared property/partition. Preserve
unknown/unsupported states and never silently turn them into covered. Split
multi-mechanism cards and render the essential applicability/benign distinction
compactly rather than append the whole card. This is a proposal; no improved
performance is established here.

Before new model calls, use independently specified positive and benign fixtures
to check concept values, relation bindings and realization predicates. Separately
measure whether the tester uses those variables. Hold the round2 budget fixed in
a diagnostic if asking whether the representation improves test quality; otherwise
extra calls confound the mechanism. Final comparison still needs an oracle audit,
since concept correctness and expected-output correctness are distinct.

Repository prior art: the earlier local ConceptCoder audit
(`research/conceptcoder_20261027/REPORT.md`) already proposed semantic variables; v5/v6 improved binding/labels without establishing downstream
gain, and the parent records the v7 compact/full-hint ablation as negative for
longer hints. Thus **renaming cards into OBS/REQ/TEST is not a new method**. The
new evidence is V85's concrete mismatch between card meaning and the executable
coverage gate. A change must actually repair/test that dependency, not relabel it.

## Source identity and unchecked scope

The live arXiv HTML v1 was fetched on2026-10-29; SHA256
`d39fec2d9da40bf11ea5e05eb5066cc6753ac59643d63446f32bfd0c97ea3cf3`.
The existing author-source copy was read without modification. Its VD annotator,
VD forward and BP forward SHA256 values remain respectively
`534d117b240795263184b704e0de800a994a023822d03b68eba4a0c42027cf9e`,
`d44095d8f104cfd5a1b76f37c0ae2a4c3133f2d02e84d0450d08522613ac2221`,
`01ec7f0dd198f8202deabc5e185a5020ef00b61405e9dc7d9c3e5c5e2a102ef0`.

No author-artifact refresh, training, dataset-split verification, controlled
representation ablation or new efficacy experiment. Proposed semantic equivalence
is definitional; it is not demonstrated computational or performance equivalence.
