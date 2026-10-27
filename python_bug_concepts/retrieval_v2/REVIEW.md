# Pre-audit implementation review — 2026-10-26

Self-review only; no independent reviewer was used. Mechanism attribution is
single-author. This is an engineering development check, not a publication-grade
independent annotation study.

Checked before the first audit outcome:

- `engine.search` receives query/code/filter parameters; it has no task-ID,
  gold-label, witness or reference parameter. `engine.py` and `corpus.py` do not
  import the evaluator/grader. Runtime retrieval reads the original/extended
  concept corpora and a derived FTS index, not evaluation artifacts.
- Original inputs project only public PUT source, entry point and ID/split
  metadata. The evaluator calls both retrievers with **code only** and joins
  strict labels afterwards. The task ID is a report key, not a feature.
- Separate native grading checks official input contract, official reference
  and PUT on the same manually supplied witness in bounded worker processes.
  94 confirmed cases cover 91 tasks: 78 value mismatches and 16 PUT exceptions.
  The other 22 tasks remain in the denominator. Type-only equal-valued cases,
  invalid contracts, unresolved workers and unlabeled mechanisms do not count.
- The grader loads the official JSON rows before projecting its four grading
  fields. The historical `hidden_test_cases_read=false` metadata means hidden
  test inputs were **not consulted or used**, not that the JSON parser skipped
  their bytes. No hidden test inputs are passed to the retriever or witnesses.
- Family-only hit@3 is kept separately from correct-family plus first-source-site
  and correct-family plus any of at most three returned sites per concept. Each
  returned record has at most three concepts and three source sites per concept.
  A correct line with a wrong concept, or the right concept on another line,
  does not pass the bound check.
- Annotation subscripts are excluded from runtime indexing evidence. Qualified
  module aliases are resolved and shadowed function parameters do not trigger a
  qualified-API rule. Nested-function returns are excluded from finally evidence.
- Default-argument, comprehension closure, actual consumed-mutator return and
  direct out-of-bounds tests pass. Generic `return` alone no longer suggests
  finally or special-method errors. Code input is parsed and never executed by
  retrieval.
- Original corpus stays at 132 cards. The separate 30-card semantic extension is
  sourced to the pinned CPython revision and explicitly development-informed.
  Its concepts and the manual strict labels were frozen before retrieval scores.
- Frozen baseline, inputs, strict labels, witnesses, source inventory and semantic
  extension hashes are checked. Final implementation hashes will be frozen before
  the first 40-task audit. Audit scoring refuses to overwrite an existing result.

Validation: 22 original-corpus tests and 20 v2 tests passed (42 total). Remaining
limits include heuristic AST analysis, incomplete general name/type resolution,
single-author broad-family definitions, and corpus/label design that has seen all
public task source. The 40-task split is a ranking audit, not unseen corpus design.
