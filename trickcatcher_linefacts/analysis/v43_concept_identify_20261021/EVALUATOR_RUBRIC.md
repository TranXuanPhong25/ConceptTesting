# Prospective manual rubric — evaluator only, before any v43 completion

Readiness metadata is not model output. This rubric operationalizes original
registered normative-binding/implementation-judgment metrics; it is never imported
by prompt builder. Same8cases, arms,24callceiling and>=2tool-onlywins/0loss rule.

Unit episode×finalarm. Initialinvalid =>bothfinalsblocked/fail, not omitted. Shared
initialproposal lacks required candidate =>both arms lack candidate coverage; do
not add/repair a correct candidate. Record sourceaccuracy of ALL initialbindings
and ALL selectedbindings, missingfacets/falseextras, exactquote quality, arguments,
vocabularycompatibility, toolrequests/errors and realized tooltreatment separately.

Primary episode success requires valid selected/evidenceIDs, a semantically correct
executablebinding covering the testedfacet, no semantically false selectedextras,
correct observed implementation judgment with truthful explanation. Exactquote
format is reported separately: faithful paraphrase can be semantically correct,
while an exact but irrelevant quote does not justify a binding. Unknown/unsupported
argumentroles cannot be repaired by interpreting modelintent. Relation labels and
roles matter; executableagreement with PUT alone is not normativecorrectness.

Tested facets (authored seen diagnostic gold, evaluation only):
- E1: preserve_occurrences(xs), occurrence_conservation; ascending may also hold
  as spec requirement but alone does not cover duplicate obligation. observed_mismatch.
- E2: count_ge(xs,limit), eligible_contribution; count_gt is implementation behavior
  and not correct requirement. observed_mismatch.
- E3: required_subset_container(container,required), membership_inclusion; equal_sets
  is overly restrictive. observed_mismatch.
- E4: min_positive_none(xs), eligible_selection and/or defined_outcome; raise variant
  describes code fault, not requirement. observed_mismatch.
- E5: sum_le_limit(xs,limit), eligible_contribution, all lengths. observed_mismatch.
- E6: sum_positive(xs), eligible_contribution; include1 and repeatedpositive occurrences.
  Distinct/gt_one variants describe faults, not requirement. observed_mismatch.
- E7: preserve_occurrences(xs), occurrence_conservation, ascending optional legitimate
  companion. no_observed_mismatch; unusedlocalset is not outputloss.
- E8: eligibilityundefined; emptyselected or explicitunknown eligible_selection binding
  +unknown judgment, no inventedpredicate/confirmedbug. Unconditionalfirst is not a
  justified complete normativebinding for undefined suitable.

A correct judgment enum with reasoning asserting behavior contradicted by usable
observations fails semanticintegration. Do not conflate exception/output:null with
normalreturnNone, or desiredspecvalues with observedvalues. Finite samples alone
do not prove universalcorrectness; source reasoning on these simple fixtures may
support implementation descriptions.

Report separate bindingcorrectness, facetcoverage, observationsreadcorrectly,
implementationjudgment and interfacevalidity; no opaque pooledaccuracy. Paired
tool-onlywins/raw-onlywins use full8denominator; pureformat-only differences
reported separately and do not count as the >=2 semanticwins gate. Toolarmfinal
valid8/8 plus E7/E8noaddederrors still required. Passing onlysupports this reused
seen-pool selectionpackage, no newinputdiscovery/assertion/transfer/concepttaxonomy
effect claim. Independent reviewer adjudicates rawtext without repairing it.
