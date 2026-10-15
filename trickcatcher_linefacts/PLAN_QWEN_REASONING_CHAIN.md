# Qwen prompt chaining — direction correction, 2026-10-15

User explicitly corrects the proposed static `align(property,effect)` design: Qwen should extract concepts and identify obligation/behavior mismatches; the research direction is to break reasoning into inspectable prompt stages. This supersedes static semantic matching as the proposed main method. v20 remains a limited verification prototype, not the desired extractor/reasoner. No new implementation/GPU experiment in this correction.

## Active responsibility boundary

Qwen performs semantic interpretation, abstraction, alignment, hypothesis selection and discriminator design. Static tools provide source IDs/AST relations, input/trace observations, schema/syntax checks and executable checks where supported. No hardcoded property-name/effect-name matching, no lexical rule choosing the intended concept, no registry-prefix fault selection. Structured fields constrain the interface, not a nine-family semantic vocabulary. Unknown verifier support is recorded; it does not turn a Qwen hypothesis into a false semantic claim or erase it from coverage reporting.

## Proposed chain

1. **Spec obligations:** Qwen sees original spec and signature, extracts candidate obligations, original domain, per-element eligibility, scope/ambiguity and exact supporting spans. No PUT-derived behavior accepted as requirement truth. Quote/base agreement alone is not semantic entailment.
2. **Actual implementation behavior:** separate Qwen call sees source body/source IDs and available structural facts; produces an abstract data/control account, output-affecting operations and conditional effect claims. Spec docstring is separated from implementation evidence so intended behavior is not silently substituted for actual behavior.
3. **Alignment/discrepancy:** Qwen receives original spec/code plus both prior artifacts; identifies compatibility or a candidate violation, cites obligation/source IDs, states the condition under which behavior diverges and a plausible alternative interpretation. No tool-defined semantic matcher. Empty/no-mismatch/unknown answers allowed.
4. **Discriminator:** Qwen turns the chosen hypothesis into an executable input condition and bounded input proposals/strategy. It states the predicted local effect and observable relation, distinct from an oracle-certified full expected output. Original domain remains fixed; ineligible elements need not be domain-invalid.
5. **Execution feedback:** tools validate supported aspects and run inputs in isolation, recording actual activation, before/after effects and outcomes. A separately budgeted Qwen call may revise/reject the hypothesis from those observations. A failed concrete prediction is not hidden by content repair or unlimited retries. No MCTS.

Artifacts link by immutable IDs/hashes; stage output cites the preceding evidence it uses. These are inspectable external claims/actions, not access to internal neural reasoning or a correctness certificate. Examples and schemas must preserve Qwen's role in the semantic decisions.

## Illustration

Spec stage: candidate requirement preserves eligible duplicate occurrences.
Code stage: source `set(...)` converts a sequence to unique elements before a returned collection.
Alignment stage: Qwen identifies possible count loss contradicting preservation if eligible duplicates exist.
Discriminator stage: Qwen proposes a duplicate eligible value and predicts count2→1.
Execution stage: tools verify exact operation/argument/value/output evidence where supported; an unreviewed normative interpretation remains an unreviewed candidate.

The tool does NOT contain `if property == preserve_multiplicity and effect == collapsed_to_one` to choose this hypothesis. The same stage interface should permit Qwen to articulate other relationships, guards and temporal concepts without first writing a matching rule for each family.

## Verification/evaluation before GPU

- Audit chain prompts and role boundary with independent subagents before implementation, as user requested earlier. A fresh new pipeline/preregistration is required.
- Offline transport tests: stage IDs/spans, exact original context, structured output extraction, missing/ambiguous answers and bounded failures. Existing v19 format failures require interface checks, not post-hoc repaired scoring.
- Independently labeled cases evaluate obligation interpretation, code-behavior accuracy, alignment and discriminator success separately. Qwen self-confidence/self-grading is not correctness evidence. Include wrong specs/models, correct implementations, masked effects, unreachable operations, alternative explanations and unknown tool semantics.
- Tool check outcomes are supported/contradicted/unknown with evidence/scope; no invented semantic verification. Preserve raw Qwen proposals alongside normalized supported checks.
- Before any online outputs, freeze per-stage calls/tokens, candidate/revision limits, source/context, common discovery and full20 denominator. Report every proposal/execution cost and verifier coverage.
- Later generation comparison must distinguish chaining gain from concept gain and extra calls: matched-budget direct baseline, same-chain behavior-only ablation, plus plain/placebo/toolinput/witness-only. Shared discovery/final admissibility/selection policy; concept-only filtering would change the tested system. Original source/spec available as registered to prevent amplification of an early wrong intermediate artifact.
- Generation freezes before saved-reference/canonical scoring. Separate candidate property false alarms from D_IO. No paid fallback, held-out run or paper reproduction.

Status: user direction recorded; detailed chain prompts/contract still require independent plan audit before implementation. Existing v20 results are preserved and do not establish success of this Qwen-chain direction.
