# Final semantic artifact audit

Independent recomputation found no blocking artifact inconsistency. All38runtime,
12evaluation and9judgment-join file hashes match. Old/new prediction seals pass;
all28queries retain exactly the old candidate objects in every A–D arm. The
source-binding-exact24prior judgments plus1fresh blinded judgment join correctly,
and final REVIEW_SUMMARY counts reproduce independently.

On12buggy queries, consistently graded supported binding occurrences are9for
both old V7 and vr13 in every arm, versus8for vr11. The fresh fixed-chunk judgment
also applies to the old identical binding, so9versus8 cannot be presented as a
new gain over V7. No old supported buggy binding is lost. Reviewed contradicted
occurrences fall22→14(A),20→15(B),22→13(C),20→15(D), with returned occurrences
falling36→26/28/25/28. All12buggy queries still return at least one proposal.

Canonical contradicted occurrences fall34→18/22/18/22, while query coverage falls
12→9. Old canonical outputs additionally have2ungraded occurrences per arm.
Those unknowns are not false positives. The remaining proposals are often still
contradicted by source, so operation screening has not solved applicability.

Frozen-label first-site hits remain8→7in every arm; the remaining loss is
HumanEval/109. This historical line metric differs from semantic support and
must be reported alongside the supported-binding preservation result.

Coverage detail: the original semantic queue contains132rows, of which117have
old judgments. Fifteen old rows remain ungraded globally; within each old A–D
arm these include4buggy and2canonical occurrences. Current vr13 selected
bindings are fully graded after the25-row join. The initial RESULTS artifact's
new_ungraded counts are a pre-review snapshot; final coverage comes from the
sealed join and REVIEW_SUMMARY. Do not describe the entire old queue as graded.

These are development-informed agent source judgments and binding occurrences,
not independent human labels, unique bug counts, formal applicability proofs or
test-generation utility. This audit executed no target or inference code.
