# Prospective evaluator-only rubric — 2026-10-23, before v50 preparation/outcomes

This file is hashed by freeze but never read into prompts/tools. Same authored
seen specs and facets as v43; no new ground truth or repaired historical outputs.
Independent reviewer reads all raw items, rejected/unknown items and prose, with
arm identities masked where practical. Report disagreement explicitly.

## Semantic unit and interface separation

Primary unit is episode×final arm (eight per arm). A correct executable requirement
must cover the tested facet below, with faithful spec justification, truthful
implementation judgment/reasoning and a relevant observation or source citation.
Bindings with spec_status=justified are endorsements; unknown/rejected are not.
An unknown/rejected item cannot supply missing coverage, except ambiguity E8.
No false endorsed extra requirement or contradictory implementation explanation is
allowed. Rejecting a true relation and also claiming its equivalent is justified
requires review of the contradiction; count inconsistent normative conclusions as
failure, not successful revision. Merely listing a rejected false alternative is OK.

A concrete concept label must be semantically compatible; concept=unknown is an
explicit unresolved label, not a false requirement. A justified correct executable
relation with concept=unknown can supply primary relation/facet coverage; report
fully labelled concept coverage separately, never infer concept-label benefit.
One relation may cover multiple facets (E6 sum_positive covers eligibility and
multiplicity); no arbitrary requirement for multiple items. IDs may change without
semantic change; score by operator, argument order, spec justification and intent.
Other admitted operators receive credit only if logically equivalent to the required
facet over the stated input domain, not because they agree on the finite pool.

At least one primary-supporting binding must be item-admitted/executable as written;
unsupported output/local roles are not silently reinterpreted. Envelope/evidence
format issues are reported separately. An unrelated malformed item does not erase a
valid supporting item; inspect its readable semantic content for false endorsements.
If required intent cannot be determined from raw response, mark unknown/failure, not
fill the field. Extra irrelevant or invented evidence IDs are interface errors;
primary semantic support still needs at least one valid, relevant cited evidence
item AND no fabricated observation claim. A correct judgment enum alone is insufficient.

Exact quote mismatch is an interface metric: a faithful paraphrase can justify a
binding; exact but irrelevant text cannot. A repeated spec word does not prove
entailment. Correct operator alone with absent/irrelevant justification is incomplete.
Pure interface-only arm differences are reported but cannot supply the >=2 semantic
wins gate. Missing calls/invalid unreadable outputs remain failures in denominator8.

## Tested facets and controls

|Episode|Required executable relation (input roles)|Judgment and support|
|---|---|---|
|E1|preserve_occurrences(xs), occurrence_conservation; ascending alone insufficient|observed_mismatch, duplicate occurrences lost|
|E2|count_ge(xs,limit), eligible_contribution|observed_mismatch, equality counted by spec but excluded by code|
|E3|required_subset_container(container,required), membership_inclusion|observed_mismatch, extra container members permitted|
|E4|min_positive_none(xs), eligible_selection/defined_outcome|observed_mismatch, empty eligible set raises rather than returns None|
|E5|sum_le_limit(xs,limit), eligible_contribution, all lengths|observed_mismatch, unjustified length guard|
|E6|sum_positive(xs), eligible_contribution|observed_mismatch, retain each positive occurrence including 1 and repetitions|
|E7|preserve_occurrences(xs), occurrence_conservation; ascending optional|no_observed_mismatch; sorted(xs) preserves occurrences, local set alone is no output loss|
|E8|No justified unconditional first/suitable rule: suitable undefined|unknown; acknowledge missing eligibility definition, no invented predicate or confirmed bug|

E8 success allows empty bindings or unknown/rejected hypotheses and must explicitly
identify undefined suitability in reason. A harmless true incidental clause does not
license first(xs) as the complete requirement. no_observed_mismatch alone is not
sufficient handling of this ambiguity. E7 unknown is an abstention, not full success.
Finite observations support finite agreement only; don't require universal proofs,
but don't accept claims contradicted by source or supplied observations.

## Reporting and gate

Record initial and final relation accuracy, concept-label quality, quote/argument
quality, required-facet coverage, justified/unknown/rejected counts, new/corrected/
retained/lost semantic hypotheses and truthful evidence interpretation. Record raw
mismatch explanation separately from complete binding success. Tool matrix holds
is behavior agreement only. Initial→final transitions are descriptive, not isolated
causal effects; no direct v43/v50 efficacy comparison with different treatments.

GO: >=2 genuine tool-only semantic episode successes, zero raw-only losses, no added
false bug or invented requirement, and tool handles E7 and E8 correctly. Report full
8×2 denominator plus interface/abstention/blocked counts separately. This gate is a
small seen diagnostic decision, not statistical proof or broad concept vindication.
