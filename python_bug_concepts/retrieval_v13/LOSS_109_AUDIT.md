# HumanEval/109: recognized operand rejected, concept rebound to an empty guard

The remaining known-first-site loss is a **binding regression**, shared by
vr11 and vr13. It is not a failure to retrieve `py.quantifier-scope`, a dense
candidate-recall loss or top-three concept ranking loss. In every A/B/C/D arm,
that concept remains the first candidate and first returned concept. Its selected
site changes from the relevant line33 operand to the correct empty-array guard
at line29.

This audit only reads frozen outputs, labels and source. It performs no model
inference, retriever rerun, target execution, tuning or runtime-source change.
All38 implementation and12 evaluation-input hashes match; the retrieval output
seal also matches. Query SHA256 is
`43ff23be7b283fce68049af5f0bbae1a0f84efcd6809c0ab9323137c9034deab`.

## Visible requirement and causal site

The public source asks whether any number of right shifts can make the entire
unique-element array nondecreasing. It also explicitly says an empty array must
return True. Relevant source, with manifest line numbers:

```python
# 29
if len(arr) == 0:
    return True
if len(arr) == 1:
    return True
# 33
if arr[0] > arr[1]:
    return False
```

The existing gold card is `py.quantifier-scope`, with accepted line33. Its stated
mechanism is treating one adjacent inversion as proof that no whole-array
rotation can sort the list. Source reasoning alone gives a valid distinguishing
class: unique-element descending two-item arrays, e.g. `[2,1]`. A right shift
produces `[1,2]`, so the required answer is True, while the cited comparison
immediately returns False. This is not an executed test or a new hidden label.
Conversely, the selected line29 empty-array guard implements an explicit public
requirement and does not establish that quantifier fault.

## Saved outputs and unchanged concept recall

| Saved system | Returned rank1 concept | First selected site | Known line33 hit |
|---|---|---|---|
| Original V7 A/B/C/D | quantifier-scope | line33 `arr[0]` | yes |
| vr11 A/B/C/D | quantifier-scope | line29 `len(arr) == 0` | no |
| vr13 A/B/C/D | quantifier-scope | line29 `len(arr) == 0` | no |

For this concept the candidate fusion scores are exactly unchanged across those
three saved systems: A/C `0.03252247488101534`, B `0.04641136376990423`, D
`0.046035988394528854`. Structural rank is1 and BM25 rank2 in all arms; dense
rank is12 in B and14 in D. All26 source sites are retained, with zero site-budget
omissions. Family diversity is off in the vr11/vr13 regression, and the frozen
evaluation verifies full candidate-list identity against the original V7 run.
Thus embeddings, candidate budget, source truncation and family deduplication
do not explain this specific loss.

The original V7 binding uses a recognized `arr[0]` Subscript at line33, semantic
support tier1 and legacy priority149. The selected node need not itself be the
whole erroneous condition to participate causally; its parent comparison makes
the incorrect early rejection.

## Operation role and site selection chain

1. `operation_binding.py:164` groups quantifier-scope with several comparison
   concepts and accepts only an `ast.Compare` for this card. The recognized
   line33 `arr[0]` node is an `ast.Subscript`, so the role function returns False.
2. `operation_binding.py:220` checks `role is False` before consulting the
   existing semantic-support tier. It returns `unbound_operation_mismatch`.
   Every saved vr11/vr13 arm explicitly records this rejection in
   `screened_bindings`, at fact ID
   `43ff23be7b28:Subscript:33:7:33:13`.
3. `hybrid_engine.py:206` removes such screened sites before options are sorted.
   The original recognized priority149 therefore cannot compete. Other
   Compare nodes are eligible under the card AST schema, including the correct
   empty and singleton guards and the causally relevant compound comparison.
4. `hybrid_engine.py:214` chooses one surviving site per concept by existing
   support tier, legacy priority, lexical site score, then source line/column.
   The returned replacement is line29 `len(arr) == 0`, with tier0, priority0,
   recognition `similarity_only_unknown`, and status
   `grounded_test_opportunity_contract_unknown`.

This establishes both the exact role rejection and the saved replacement. The
packets do **not** persist every surviving alternative's numeric lexical score,
so this read-only audit cannot distinguish a lexical advantage for line29 from
a lexical tie settled by its earlier source position. It would be inaccurate to
claim measured equality of those missing site scores. The underlying limitation
is nonetheless concrete: the operation predicate discards a causal operand
binding, then the replacement selector lacks a source-grounded preference for
the parent mismatch over a benign same-AST-kind guard.

vr13 adds fixed-chunk and direct-recursion operation roles but leaves this
quantifier predicate unchanged. Its total bound candidates for this query rise
from vr11's4 to5, while the selected quantifier site and top-three results remain
the same. The missing site is therefore not newly introduced by vr13; vr13
preserves this earlier regression while restoring other operation mechanisms.

## Metric and interpretation limits

`evaluation_development/evaluate.py:115` defines known-site hit by accepted card
ID and **first evidence line**, not a full causal proof. V7's operand and the gold
compound comparison share line33, so V7 receives a hit. vr13 retains the right
card but its first evidence is line29, so the hit is lost. This is a real loss of
the old labeled location, while the hit metric alone must not be equated with a
new confirmed bug or downstream test utility.

All four vr13 buggy-arm totals are7known first-site hits versus V7's8, and this
task is the remaining loss. The source and labels are development-exposed; this
audit is neither an independent human annotation nor held-out evaluation. It
does not change any frozen role/ranker or recommend claiming efficacy from
restoring a single label. A future implementation would need a separately
registered general relation policy and benign-guard controls, not a task109
line-specific exception.

Implementation-freeze SHA256:
`c258ac2c4c80985df62642e0a195da7dd348c59a2780bc1031238bc2b34e4a7a`.
Sealed vr13 retrieval SHA256:
`db316dd0f4403b7837b6b807539ec7362394f0968852cb657430adf3def88d91`.

## Separate VR12 lifecycle check

From local saved artifacts only, VR12 remains `blocked / RuntimeError`, without
COMPLETE or a completion-attempt ledger: zero saved completion attempts. Saved
controller PID63414 is absent from `/proc`, and its existing run lock is free.
No endpoint poll, launch, retry or kill was performed for this check. The prior
separate metadata404 observation remains separate from the controller's coarse
saved error and was not repeated here.
