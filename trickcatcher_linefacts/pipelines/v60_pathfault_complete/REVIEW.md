# Review record

2026-10-24, independent read-only Codex `v57_review`.

Initial review: REQUEST CHANGES. Findings included event predicates not checked, weak IR/alternative validation, per-recipe rather than case budgets, PYTHONHASHSEED ignored by `-I`, unknown sensitivity conflated with false, incorrect helper bindings and scorer classification/provenance problems.

Native changes applied before diagnostic: exact source/span/kind and pure alternative validation; topology/closed predicate/ID/budget checks; explicit local snapshot predicate; unknown on unstable/failed execution; aggregate budgets; seed reset for each original/alternative execution; sanitized `-s` worker honors PYTHONHASHSEED; eager deadline/candidate construction; compiler excludes unsupported nested-helper scope; realized scope explicit. Regression tests cover site masking and local predicate failures.

Reviewer then approved **exactly one fixed reference-free six-case CPU diagnostic** via compile_public→certify_case. This approval excludes new models/private scoring and full P2/P4 completion. All compiled recipes, requests, source/config hashes and budgets were frozen before executing that diagnostic. Results are in RESULTS_ENGINEERING.md.

Remaining limitations: compiler scope/shadow checks are syntactic rather than a semantic identity proof. No solver-UNSAT claim from absent native candidates. First package has only structural recipes, not completed semantic diagnosis/compositional predicate integration.

Private scoring ran prematurely before independent review in the predecessor phase. It is preserved as provisional, with deviation and unresolved review work in analysis/v57_completion/REVIEW_STATUS.md. No fresh private scoring followed this review.
