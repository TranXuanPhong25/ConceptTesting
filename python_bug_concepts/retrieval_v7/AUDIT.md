# Implementation and returned-result audit

Development-informed; user explicitly requests repair from returned results.
Preserve v2/v5 and each v6 iteration, including negative results. No paper model
or algorithm is reproduced. Runtime never reads task IDs, labels or references.

## Confirmed implementation/design weaknesses in v5

1. Requires/excludes mostly declared strings. Only a small subset is executable;
   unknown candidates still inherit large hand-assigned structural priorities.
2. Pair ranking is effectively the old rule ordering: output dependency adds6
   against priorities76–230. It need not reorder competing mechanisms at all.
3. Atomic comparisons are selected independently of their enclosing decision.
   Assertions, internal-state guards and neutral empty/singleton paths can beat
   the actual invalid offset, consumed sentinel or compound decision.
4. Eligibility misses ASCII character-range comparisons, unique-domain membership
   used as a replacement for sorting occurrences, and ternary direction choices.
5. Most occurrence-position evidence does not distinguish a legitimate
   index(minimum) lookup from first-index/current-position confusion.
6. Local origins key by lexical AST scope; a comprehension's outer symbol can
   lose its definition. Comprehension iterators were not traversed as dependencies.
7. Primitive fixtures often have no competing candidates, so passing tests does
   not demonstrate full-function ranking quality.

## Iteration01, preserved

Semantic support tiers and relation-specific sites improve coverage-mode first
site74→88/113, with one family/site regression. Precise mode returns133cards
versus275; old-label matches60.9%, firstsite79. Loss analysis shows overly broad
rules for signed modulo, normalization, numeric coercion and early return.
These are real quality risks, not simply weight-selection problems.

## Iteration02, preserved

- Modulo equals zero is divisibility, independent of remainder sign.
- int(square-root) used as prime-loop bound is deliberate floor conversion.
- First matching item in a right-to-left scan can be the intended positional
  optimum; distinguish this from a global minimum over unordered inputs.
- Membership tables, text/classification normalization and aggregation units
  have different roles; do not conflate operation presence with mismatch.
- New syntax recognizers must upgrade an existing same-node candidate instead
  of discarding stronger semantic support during deduplication.
- Fixed escaped-regex control bytes introduced in development; regression scans
  all implementation files for accidental non-whitespace control characters.

Iteration02: coverage family91/site90; precise family90/site89,135cards with
68.9%old-label matches. One remaining precise loss is an internal filtered bucket
whose definition is dominated within an else branch but the conservative origin
resolver rejects every branch-local assignment. Correctness review continues
with paired benign cases and correct-program controls; no accuracy claim from
label-match rate alone.

## Final integrity checks

A full113-query fact-reference audit found one dangling reference: the newly
recognized compound frequency decision had a source span but was not inserted
into the exported fact graph. The supplemental builder now registers its fact;
a regression checks exported IDs. This is an output-integrity repair, not a rank
weight change. Final iteration06 preserves/re-evaluates the exact shipped code.
Earlier iteration03–05 results remain unchanged; all final numbers come from06.

Additional robustness fixes: undocumented nested helpers inherit enclosing public
purpose, while input-type assumptions still use their own declaration; module
fragments no longer crash when no enclosing function exists. Correct native
outcomes are reused only with unchanged input/reference hashes. One malformed
manual input proposal is preserved and corrected separately, never counted valid.
