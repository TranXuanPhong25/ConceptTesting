# SAVIOR and mutant-derived trigger concepts

Source audit: 2026-10-13. Proposal review only; no SAVIOR reimplementation or experiment was executed.

Primary source: [SAVIOR: Towards Bug-Driven Hybrid Testing, arXiv:1906.07327v1](https://arxiv.org/html/1906.07327v1).

## What the paper establishes

SAVIOR separates bug-driven prioritization from bug-guided verification. Compilation-time UBSan labels identify potentially vulnerable operations; these are candidates, not known ground-truth bug sites. Reachability analysis helps prioritize seeds. On an explored path, concolic execution solves a labeled operation's fault predicate together with the path constraints, producing a concrete witness or establishing infeasibility on that modeled path.

The paper establishes benefits for sanitizer-oriented hybrid testing. It does not evaluate concept-conditioned LLM generation. The proposed LLM system would replace or supplement a constraint-solving component with a fallible abstraction/generation process; it cannot inherit SAVIOR's solver-backed guarantees automatically.

## Candidate research contribution

The narrow hypothesis is: **a verified, structured abstraction of distinguishing input conditions improves input discovery over raw mutant feedback and an unstructured summary of the same information.**

Proposed stage contract:

1. Static analysis and mutant enumeration: candidate sites and fault hypotheses, without target-bug labels.
2. Mutant-to-trigger inference: reason backward from a program–mutant edit to input/state relations and reachability context.
3. Structured representation: retain `site_id`, `mutant_id`, `reachability_conditions`, `input_domain`, `distinguishing_relation`, and `observation_target`. Retain a candidate's uncertainty and provenance rather than asserting the original program is correct.
4. LLM input generation: generate inputs or strategies; do not generate expected outputs in this isolated experiment.
5. Execution verification: check domain validity, actual site reachability and observable original–mutant disagreement. Feedback distinguishes wrong arity/domain, missed site, reached-but-not-distinguished, and successful distinguishing witness.

For an integer comparison changed from `<` to `<=`, equality of the operands is a candidate local distinguishing relation. This is not sufficient if the site is unreachable or both alternatives subsequently produce the same observable behavior. Reachability, local divergence and propagation must remain separate checks.

## Oracle boundary

Original–mutant disagreement proves a distinguishing input, not a real bug or the correctness of either result. For known safety properties, a suitable sanitizer/checker can provide an independent signal. Functional correctness requires specification, trusted properties or other independent oracle evidence. Fixed implementations must remain evaluation-only in an experiment testing generation from genuinely buggy input.

## Closest existing repo mechanisms

- `EvalAndMitigate/m8_concept_mutants/mutate.py`: starts from C1–C8 categories and builds concept/generic mutant catalogues. This is concept-to-mutant construction, rather than a tested inverse trigger-abstraction stage.
- `trickcatcher_linefacts/facts.py::t_mutant`: renders before/after mutant differences and base-test survival. Its MUTANT text does not itself provide a structured input-domain trigger relation.
- `trickcatcher_linefacts/run_v5.py::mine_gap`: uses a fact to ask the LLM for a targeted Hypothesis strategy and verifies actual hits. It provides an existing generation/feedback mechanism for comparison, without establishing the new abstraction's value.
- `kite_concept/extraction.py::concept_extraction_prompt`: proposes input-trigger and oracle text from a historical mechanism; do not conflate that schema with a mechanically verified trigger extractor or a faithful implementation of the KITE paper.

## Minimal discriminating evaluation

Use the same programs, selected mutants, domain checks, generator model and repeat policy in every arm:

- No mutant guidance.
- Raw mutant feedback.
- Unstructured summary of the same mutant information.
- Structured trigger concepts.

Count abstraction cost in overall cost curves; keep input-generation budgets comparable. Assess distinguishing-witness rate per mutant, time/tokens to first witness, and independently verified concept delivery. Report real-bug detection and oracle errors separately if a later oracle stage is included. A held-out mutant/operator-family evaluation tests whether concepts transfer beyond the exact mutation edits used to derive them.

Mutation score and concept coverage alone do not establish improvement on real bugs. Existing negative results of concept variants should motivate this representation-level ablation rather than be treated as evidence for the proposed extractor.
