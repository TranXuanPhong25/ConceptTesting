# Evidence-Based Reading Notes: LLM Testing Papers (2025-2026)

This is the full-text rewrite of the 131-paper catalog in
[llm-test-generation-2025-2026.md](llm-test-generation-2025-2026.md).

Each paper note answers five questions:

1. What method does the paper use?
2. What problem motivated it?
3. What data, subjects, and execution setting does it evaluate?
4. What result does it report?
5. Where could a structured `concept` enter the method?

## Evidence policy

`Full text` means an official open-access PDF, conference PDF, or author-hosted manuscript was read. `Abstract-only` means no lawful full paper was available during this pass. Abstract-only entries do not invent dataset cardinalities, benchmark scores, or table values.

The notes use direct prose rather than generic “method/hook” labels. Numerical claims retain the paper's source link. A publisher DOI remains the primary citation even when an author manuscript supplied the readable full text.

## Reading Batches

| Catalog papers | Notes |
|---|---|
| 1-20 | [Batch 01](fulltext-batches/batch-01.md) |
| 21-40 | [Batch 02](fulltext-batches/batch-02.md) |
| 41-60 | [Batch 03](fulltext-batches/batch-03.md) |
| 61-80 | [Batch 04](fulltext-batches/batch-04.md) |
| 81-100 | [Batch 05](fulltext-batches/batch-05.md) |
| 101-122 | [Batch 06](fulltext-batches/batch-06.md) |
| 123-131 | [Batch 07](fulltext-batches/batch-07.md) — bug-finding additions |

## What The Corpus Says About Concept-Guided Testing

The papers divide the concept question into four concrete jobs:

- **Choose the fault target.** Mutation-guided systems use a surviving mutant. Vulnerability work uses a sink, trigger guard, and reachable entry point. Fault-exposure benchmarks use a known wrong implementation.
- **Make an input feasible.** Fuzzing work turns protocol grammar, parser state, call chains, or symbolic constraints into a valid seed before mutation.
- **State the oracle.** Differential, metamorphic, and red/green systems encode expected equivalence, a transformed-input relation, or a correct-versus-buggy outcome.
- **Carry state through repair.** Strong feedback loops preserve the target concept while repairing syntax, setup, assertions, coverage, and fault exposure.

The current repo already covers target-path concepts and execution feedback on TestEval. The most defensible next metric is TestCase-Eval Task 2 Fault Exposure. Mutation score, TestGenEvalLite, VulEUT, and TestExplora each add a stricter semantic oracle after that.

## Access Limits

Some IEEE and ACM papers expose only an abstract without institutional access. Those entries stay in the report because they are relevant and linked, but they are not treated as full-text evidence. Add an author manuscript or licensed PDF later, then replace the abstract-only fields rather than extrapolating from title or venue.
