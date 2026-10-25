# v69 typed writer and bounded CPU replay — 2026-10-25

User requests continuing the writer-interface/constructor fixes after v67. Prior
work: v31/v34/v35 template limitations, v47 tool-menu selection no gain, v63
weak hypotheses and witness-selection loss, v67 gate0/6 with unsupported string
ordering. v66 CrossHair and v68 symbolic generation are separate source-path
branches. This revision repairs v67 interfaces; it is not a new efficacy claim.

Changes before new CPU outcomes:
- Prospective writer sends short restricted Python conditions over arg0,arg1,...,
  plus structured operator/literal/expression edits at a source-bound site.
  The tool compiles conditions to predicate IR and simple edits to AST. Arbitrary
  prose is not silently interpreted; complex replacements can remain explicit
  pure expressions. This is not restricted to a ranked mutant menu.
- Public type profiles check trigger operator/type compatibility and Boolean
  root before search. String/string ordering implements Python lexicographic
  Unicode codepoint order, including empty/prefix/equal strings. Sequence/string
  tags remain distinct. Unsupported types/operations are explicit rejections.
- Legacy replay canonicalizes only gt/ge/ne to equivalent lt/le/not-eq, records
  transforms, and retains raw responses. No None/assignment/int-vs-string intent
  correction, inferred len(), new semantic writer, or adaptive hypothesis edits.
- Preserve public consistency, exact native realization, evidence parity,
  non-public-sensitive display requirement and ALL-six-case gate. Search domain,
  enumeration order,64candidate/256native/120second case caps stay unchanged.

First run is CPU-only on exactly the six frozen v67 writer responses and public
requests. Include all15proposals and all6cases, preserve earlier labels/results,
freeze source/inputs before replay. Recompute admission and public construction
in a fresh folder, not a model run or an independent replication. Report typed
rejects, equivalent normalizations, public checks, candidates, witness counts,
selected sensitivity, gate, actual executions and source/provenance hashes.

Authored differential tests compare symbolic strings with real Python ordering;
compiler tests cover operator rewrites, type errors, unsafe syntax and stable
native re-admission. Separate integration fixtures validate the new writer schema
through actual prepare_case; these are engineering fixtures, not paper simulation.
Owner source review before replay; independent agents are unavailable under the
current no-delegation instruction. No independent-review PASS is claimed.

No endpoint/model/API/private oracle calls, cohort enlargement, changed scoring,
or real-outcome-selected search expansion. Oracle/ref10 deferred. Fresh writer
performance remains untested until a separately frozen diagnostic.
