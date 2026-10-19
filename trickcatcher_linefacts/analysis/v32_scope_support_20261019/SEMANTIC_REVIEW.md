# Clean-context actual-output review — PASS with a material f06 caveat

Independent v32_semantic_review, no history, read-only. No model/network/worker calls,
no rejected-code execution, adaptation, repair or historical rescore.

| Case | Independent conclusion | Pool evidence | B |
|---|---|---|---|
|f02|Full sorted multiset obligation correct; dedup behavior/duplicate trigger correct, target3. Nested comprehension capture valid.|14 witnesses,11 passes,0 unknown/counterexamples|admitted supported|
|f04|Exact >= count obligation, strict > behavior and equality-boundary trigger correct, target3.|14 witnesses,11 passes,0 unknown/counterexamples|admitted supported|
|f06|Subset membership obligation, set-equality behavior and strict-subset fault condition correct. Trigger has wrong function signature; evidence explanation contains a false sentence.|8 obligation violations,17 passes;0 trigger evaluations|rejected unverified|
|f14|Reachable unused set does not affect returned sorted original list; consistent correctly recognized.|25 obligation=True,0 false flags|admitted consistent|
|f13|Undefined suitability remains unknown; first-element/None behavior does not establish normative correctness.|24 native observations,24 unknown-contract/undefined-oracle rows|admitted unknown|

f06 says supplied cases lack its distinguishing condition, but all6 selected common
examples are discriminators: five empty-required/nonempty-container and one nonempty
strict subset, container=[2,-2,-1,2], required=[-2,-1,-1]. This is an evidence-grounding
error, despite correct conceptual condition. Explicit request requires trigger(arguments);
raw trigger(container, required) is properly rejected as predicate_signature. Empty
unknown_indices does not imply coverage: trigger_results empty, complete_coverage false,
combined hypothesis failed. No trigger was executed, renamed or wrapped.

Fresh f04/f14 predicates reuse x in sibling comprehensions and are accepted/evaluated
unchanged. Fresh f02 nested comprehensions capture outer names correctly. Four finite
banks238/510/2028/238 all match (3014 probes); this exercises lexical-scope acceptance,
not a controlled efficacy estimate or universal semantic proof. f14 relation predicate
checks serialized value; actual source makes the sorted-copy behavior clear, while the
predicate alone does not establish alias identity.

No provisional candidate admission, input request, generation file or cumulative model
update occurred. Support promotion has CPU authored regression evidence only (48 tests
reported passed; reviewer did not rerun). All5 C slots blocked, not five generation
failures. No generated contrast, final input abstention, novelty, task gain or assertion
performance measured. Witness-only already covers3/3 bugs. f13 metadata/hypothesis
abstention is observed; input abstention is untested.

Full original pool124 observations:100 defined-oracle/known-contract,36 true flags
(14+14+8),0 false flags/missed bugs;24 f13 undefined/unknown remain separate. Mismatch
support NA for f14/f13. Calibration finite and authored; not reference-free proof.

All22 raw response/request/final/stdout linkages matched;22 unique threads,163666 input/
4463 output known tokens,0 unknown usage.902 run-frozen and177 raw-transport hashes,
protocol/suite sources matched. Main248 PUT calls/3164 predicate evaluations, no failed/
unresolved workers. Requested CLI model/low only, server identity not emitted. Schemas
exposed/host disabled, role flattening/Codex instructions/unmatched sampling limitations
remain. No comparison arms or causal concept gain claim.
