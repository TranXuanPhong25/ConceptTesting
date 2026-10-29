# Blinded semantic binding review

Read only assigned queue files derived from SEMANTIC_REVIEW.json, this rubric,
and public Python semantics as needed. Do not open RESULTS.json, RETRIEVAL.json,
REVIEW_KEY.json or method/rank/machine-label summaries before freezing judgments.
Reviewers may know the preregistered task distribution, but not arm attribution.
No code execution, source rewriting, model calls or new benchmark labels.

Each queue row supplies a standalone public source, a canonical concept card and
one selected source binding. Revised retrieval descriptions are intentionally not
shown. Review concept/site proposal quality, not the quality of hidden overlay text.
Do not infer support from the mere presence of an operation.

Assign one status:

- `supported_fault`: the cited expression participates in this card's actual
  mechanism, and the public contract/domain plus source show a behavioral error.
  State a contract-valid distinguishing input class and its required relation.
- `contradicted`: the proposed binding/mechanism conflicts with visible source or
  public requirement, or the operation is demonstrably appropriate for the stated
  behavior. Cite the concrete contradiction. This is proposal confusion, not an
  emitted false bug report: the original engine may mark the proposal unknown.
- `unknown_or_conditional`: operation/context may warrant testing but required
  contract, causal flow, domain or source binding is not established. A useful
  testing opportunity on correct code may belong here.

For every row report review_id, status, useful_conditional_hypothesis (bool),
source_quotes (exact short snippets), reason, mechanism_family (short description),
and distinguishing_input_class (null unless justified). Do not promote a generic
boundary card solely because the function has some different bug. An exact AST
location need not be the first faulty line, but its causal involvement is needed.
Do not force an answer for ambiguity; preserve unknown.

Same operation can be correct under a distinct-cardinality contract and incorrect
under an occurrence-cardinality contract. Old engineering fixtures have been seen
and remain exploratory. Judgments are source reasoning by Codex agents, not a new
independent human annotation or a formal proof. Root will unblind only after each
review file is complete, record coverage, and test the preregistered GO condition.
