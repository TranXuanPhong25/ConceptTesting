# Owner source/protocol review before CPU replay

No independent delegation was performed under current orchestration restrictions.
No independent-review PASS is claimed. Review covers the following invariants:

- Expression compiler only traverses a closed AST subset; no eval, attribute calls,
  indexing, comprehensions, arbitrary names or prose inference. Canonical aliases
  are recorded; legacy mode never rewrites semantic content or None placeholders.
- Typed checks reject string-vs-int comparisons before public/native search and
  require Boolean roots. Unknown local types remain concrete-event unknowns until
  replay. Unsupported containers/operations are disclosed, not silently coerced.
- Symbolic strings retain their type tag and codepoints; lexicographic order uses
  first unequal codepoint or proper prefix. Tuples retain distinction from lists.
  Differential tests compare against actual Python on empty/prefix/equal/Unicode
  strings, and solver outputs are independently evaluated concretely.
- Operator edits are built from a deep copy of the exact source AST; no inferred
  variable assignment repair. Existing replacement purity/spec binding/no-op gate
  and public checks are reapplied; native re-admission remains stable.
- Compilation receipts keep original proposal indices even after rejection and
  distinguish different claims on the same site/trigger/alternative. Pipeline
  checkpoints the receipt and refuses compilation drift on resume.
- CPU replay freezes sources/config and exact saved writer/request hashes before
  any new construction. All six cases/all15proposals retained; zero model/private
  labels; fixed domains/search ordering/budgets. Writer interface efficacy cannot
  be inferred from legacy replay. No independent semantic truth check is implied.

Potential retained limits: evidence may be invalid-domain; small/early shapes can
consume the unchanged budget; alternatives may agree or be wrong; identical
public behavior does not prove the hypothesis. These are not silently repaired
or tuned after seeing replay outcomes.

Pre-replay validation:114 authored regression tests passed in16.52s; all pinned
v67 parent files unchanged. Runtime/Z3/author baseline and protocol/review hashes
join Python/config/input hashes in the pre-execution manifest. No real-case CPU
replay outcomes or fresh model responses were inspected during this review.
