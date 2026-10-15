# v17 templates and separate interface probe

Frozen 20-task design-dev gate, followed by predeclared six synthetic interface cases. No D_IO evaluation.

Concept gate: **2/20**, required 10: failed. Representation 17/20; 44 CPU tests pass.
Proposed 12; base-compiled 4; checked/shown cards 2.
Generation stopped; D_IO unmeasured.

| Task | Proposed | Base-compiled | Shown |
|---|---:|---:|---:|
| 27 | 1 | 1 | 1 |
| 31 | 1 | 0 | 0 |
| 51 | 1 | 0 | 0 |
| 56 | 0 | 0 | 0 |
| 57 | 1 | 0 | 0 |
| 59 | 1 | 0 | 0 |
| 63 | 1 | 0 | 0 |
| 76 | 1 | 0 | 0 |
| 78 | 1 | 1 | 1 |
| 85 | 0 | 0 | 0 |
| 91 | 0 | 0 | 0 |
| 94 | 0 | 0 | 0 |
| 98 | 0 | 0 | 0 |
| 110 | 0 | 0 | 0 |
| 118 | 1 | 0 | 0 |
| 126 | 0 | 0 | 0 |
| 136 | 2 | 2 | 0 |
| 144 | 1 | 0 | 0 |
| 149 | 0 | 0 | 0 |
| 152 | 0 | 0 | 0 |

Costs: {"logical_proposal_requests": 40, "successful_new_requests": 40, "failed_attempts": 0, "cache_hits": 0, "input_tokens": 38891, "output_tokens": 4116}.
Rejections: {"base_unknown": 6, "unknown_proposal": 13, "unknown_spec_unit": 18, "base_contradiction": 2, "no_replayed_discriminator_with_anchor": 1}.

Qualitative audit of the two shown cards: task 27 uses MAP swapcase with an alternative lower-case map. Its replay has a candidate Unicode behavior discrepancy and source anchor, but its rationale copies all three prompt placeholders. No canonical confirmation was run. Task 78 counts membership in the prime-digit alphabet; the source does equivalent per-digit counting, so the LLM claim that membership is inapplicable is unsupported. Its witness does not violate the candidate requirement. Neither card establishes explicit fault reasoning.
Primary gate remains 2/20 exactly as frozen validators returned; this audit does not silently redefine it. One accepted placeholder rationale demonstrates that length/schema checks are insufficient for reasoning quality.

## Separate synthetic interface probe

Six hand-authored requirements, with declared models/examples and randomized candidate ID positions, registered before these calls. No HumanEval PUT or gold code. Parameter synthesis and candidate-ID selection each have one request/case, temperature 0, max 512 output tokens. Prompts intentionally differ; this is a small interface probe, not an isolated causal test of output format.

| Synthetic case | Compiles | Example semantics correct | Evidence schema valid | Choice correct |
|---|---|---|---|---|
| character_filter | True | True | False | True |
| bidirectional_order | True | True | False | True |
| indexed_sum | True | False | True | True |
| paired_absolute_difference | False | False | False | True |
| filtered_multiplicity | True | True | False | True |
| empty_safe_minimum | True | True | True | True |

Probe counts: {"synthesis_compiles": 5, "synthesis_semantics_on_declared_examples": 4, "synthesis_evidence_schema_valid": 2, "choice_valid": 6, "choice_correct": 6, "synthesis_both_schema_valid_and_example_correct": 1}.
Probe costs: {"successful_new_requests": 12, "input_tokens": 9364, "output_tokens": 370, "failed_attempts": 0, "cache_hits": 0}.
Uniform-choice expected correct count: 1.83/6; always-C0 baseline: 3/6. No generalization claim from six selected synthetic cases.

Observed direction: parameter/evidence construction remains brittle, while choosing among supplied compiled models succeeds on all six declared cases. This supports investigating tool-built/base-filtered model candidates and LLM selection/ranking, with tool-generated execution evidence rather than free-form rationale. It does not prove bug-detection improvement or entailment on real specs. No v18 benchmark run is part of these results.
