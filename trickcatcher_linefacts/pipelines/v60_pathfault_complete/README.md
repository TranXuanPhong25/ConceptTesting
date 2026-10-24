# v60_pathfault_complete — implementation in progress

This is the isolated implementation workspace for PLAN_PATHFAULT_COMPLETION_20261024.md. Parent source was copied from best v7, with selected v57 modules ported. V57 source/generation artifacts remain unchanged.

Current implemented entry points:

- `capability_inventory.py`: source-only syntactic overapproximation and native-route/budget inventory. It is not a complete call graph or semantic support proof. Frozen six-case matrix is `out/pipelines/v60_pathfault_complete/p1_source_inventory.json`; all six route native-first.
- `frozen_score.py`: raw-final slot preservation, parser/dedup/expectation-conflict reporting and summary primitives. Actual historical scoring is external in `analysis/v57_completion/`; its outputs remain provisional pending independent scoring review.
- `recipe_ir.py`: closed schemas for three constructors, exact source/span binding and finite budgets. This is not yet the complete compositional predicate grammar in the plan.
- `native_construct.py`: constrained input construction, exact source-bound native replay, repeatability checks, optional local-event checker, and explicit sensitivity status. `certify_case` enforces aggregate64candidate/256execution/120second bounds.
- `recipe_compiler.py`: structural AST candidates for supported len/sum/set and rounding sites. This is a behavioral heuristic, not spec diagnosis. Nested helper scope candidates are skipped explicitly. No hand-written case-ID answer table.
- `binding_graph.py`: syntactic scope/control/definition candidate evidence; not SSA or validated semantic alignment.

Current targeted regression suite:16tests pass. These tests do not establish support/efficacy on the real six cases. Independent review gates the reference-free diagnostic. No new model/endpoint call has been made for v60.

Remaining planned work includes compositional predicate IR, semantic writer/binding/ranking integration, final-input realization audit, full reporting/evaluator approval and P4 lifecycle runner. V58 remains queued and must not launch from this partial implementation.

Copied v7/v57 files and CLIs are provenance/reference material, not a declaration that those generation entry points implement the completed v60 method. Use only entry points documented above while online_enabled is false.
