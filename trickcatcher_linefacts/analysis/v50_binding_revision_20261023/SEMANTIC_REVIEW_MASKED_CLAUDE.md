# v50 binding revision — independent semantic review (masked arms)

Reviewer: clean-context evaluator, 2026-10-24. Inputs read: `trickcatcher_linefacts/analysis/v50_binding_revision_20261023/EVALUATION.md`
(rubric, applied literally), `review_bundle/E1.json … E8.json`, `pipelines/v50_binding_revision/revision_protocol.py` and
`identify_tools.py` (arity / check definitions only). Nothing under `out/pipelines/v50_binding_revision/`, `/tmp`, RESULTS,
CHECKPOINT, memory/ or git history was read. Arm identity (A/B) was not inferred.

## Ground rules applied

- Primary unit = episode × final. SUCCESS requires all of these: (a) a `spec_status=justified` binding with the required
  relation, correct argument roles and order, item-admitted and executable as written (correct arity, input-parameter names
  only); (b) a faithful spec justification (exact quote or faithful paraphrase); (c) the correct `implementation_judgment` with
  truthful reasoning; (d) at least one valid, relevant evidence citation and no fabricated observation claim; (e) no false
  endorsed extra requirement; (f) no contradictory implementation explanation or inconsistent normative conclusion; (g) a
  concrete concept label that is semantically compatible (rubric: "A concrete concept label must be semantically compatible").
- unknown/rejected items never supply coverage (except E8).
- Initial responses: the initial `reply_schema` contains ONLY `bindings` (no `implementation_judgment`/`reason`/`evidence`). The caller's
  brief says the initial "plus an implementation judgment", but the packets do not show that. So initial verdicts are
  **binding-level only**: required relation endorsed and executable, and no false endorsement.
- Mechanical admission (`revision_protocol.admit`) checks the schema, item budget and duplicate ids only. It does not check
  arity or argument names, so some "admitted" items are not executable as written. I flag these myself, using the
  `identify_tools.arity` definition (2 arguments for required_subset_container/equal_sets/count_ge/count_gt/sum_le_limit,
  otherwise 1).
- Parse check: for all 24 responses, `json.loads(raw_response)` equals `admission.parsed`, and none was fenced. I agree with
  every mechanical admission result. My disagreements are only about executability, which admission does not measure.
- Every `spec_quote` in all 24 responses is an exact substring of the spec, so there are no exact-quote interface errors anywhere.
  No response cites an unknown evidence id.

---

## E1 — `sorted(set(xs))` vs "sorted … Preserve the number of occurrences … including duplicates"

**Expected:** `preserve_occurrences(xs)` justified (ascending alone is insufficient); `observed_mismatch`, duplicate occurrences lost.

**Initial — FAILURE.**
- `{"relation":"preserve_occurrences","arguments":["xs"],"spec_quote":"Preserve the number of occurrences of each value, including duplicates.","spec_status":"rejected"}`. The true required relation is rejected.
- `{"relation":"required_subset_container","arguments":["xs"],"spec_status":"justified"}` is an endorsed misapplied relation. Its arity is wrong (it needs 2 arguments), and per the vocabulary it means `output == (set(arg1) <= set(arg0))`, i.e. a boolean output, which is false for a list-returning spec. Under the rule that roles are not silently reinterpreted, this is a false or non-executable endorsement.
- `ascending` with `"arguments":[]` is justified. It is true but has an arity mismatch (not executable as written).

**final_A — FAILURE.**
- Bindings: `preserve_occurrences(xs)` **rejected**; `equal_sets(xs)` rejected (arity 1/2); `ascending([])` justified (true, arity mismatch).
- `"implementation_judgment":"observed_mismatch"`; reason: "The code does not preserve the number of occurrences of each value, as it uses set(xs) which removes duplicates…"
- The judgment and mismatch explanation are correct, but the only endorsed binding is `ascending`, which the rubric calls insufficient. The reason treats occurrence preservation as the requirement while the binding rejects it. That is an inconsistent normative conclusion, which the rubric counts as a failure.
- A minor reasoning defect: "does not fully satisfy the 'required_subset_container' relation as it removes duplicates". That relation is no longer in A's bindings, and set-based inclusion is not affected by duplicates.
- False endorsed extra: none (`ascending` is a true spec requirement).

**final_B — FAILURE.**
- Bindings: `preserve_occurrences(xs)` **rejected**; `required_subset_container(xs)` rejected; `ascending([])` justified.
- `observed_mismatch`; reason: "…uses set(xs) which removes duplicates. It does not fully satisfy the requirement to return a list containing every integer from xs, including duplicates."
- The reason explicitly calls duplicate preservation "the requirement" while the binding rejects it: an inconsistent normative conclusion. False extra: none.

**Interface:** both finals have a valid envelope, valid evidence and exact quotes. Both cite all 15 ids as a blanket citation; O1 and O2 have no duplicates and do not witness the bug, which is minor. Endorsed `ascending([])` is non-executable as written (arity).

**Transitions (identical in effect for A and B):**
- `preserve_occurrences` rejected → rejected: error retained.
- Misapplied endorsed `required_subset_container(xs)` → withdrawn. A replaced it with `equal_sets(xs)` rejected; B re-marked it rejected. This corrects a false endorsement.
- `ascending` retained.
- No gain on the required facet.

---

## E2 — `sum(1 for x in xs if x > limit)` vs "greater than or equal to limit"

**Expected:** `count_ge(xs,limit)` justified, concept eligible_contribution; `observed_mismatch`, equality excluded by code.

**Initial — FAILURE (strict; relation-level SUCCESS).**
- `{"concept":"quantified_decision","relation":"count_ge","arguments":["xs","limit"],"spec_status":"justified"}`. The relation, argument order and quote are correct and executable.
- `count_gt` is rejected (a correct rejection), plus an unknown/unknown item.
- The concrete concept label `quantified_decision` is incompatible. The vocabulary maps `count_ge` to `eligible_contribution`, and `quantified_decision` is the all/any boolean family, while counting is not a decision. The mechanical check also says `concept_relation_vocabulary_compatible:false`.

**final_A — FAILURE (strict; relation-level SUCCESS).**
- Bindings are identical to the initial, including the incompatible `quantified_decision` label, even though the shared packet's candidate_checks showed `concept_relation_vocabulary_compatible: false` for this binding.
- `observed_mismatch`; reason: "counts … strictly greater than limit, whereas the spec requires … greater than or equal to limit." This is correct. Evidence includes `source_return` (relevant) and O3–O7 (true witnesses).
- The only defect is the concept-label clause. If the caller scores relation/facet coverage only, with labels reported separately, this is a SUCCESS.

**final_B — FAILURE (strict; relation-level SUCCESS).**
- Same bindings and label.
- Reason: "…This is evident from the observations where the output is incorrect for cases where elements are equal to the limit." This is true: O3, O4, O5, O6 and O7 each contain an element equal to the limit and are undercounted, while O1 and O2 are correct.

**Interface:** both clean. Blanket citation of all ids (O1 and O2 are non-witnesses, minor).

**Transitions:** all bindings retained verbatim in both; the concept mislabel was retained. A correct judgment was added in the final (it did not exist in the initial).

**Rubric note:** the rubric's E2 row lists "eligible_contribution". I apply "concrete label must be semantically compatible" as a success condition. A relation-only reading flips E2 to SUCCESS for initial, A and B alike, so it creates no arm difference.

---

## E3 — `set(required) == set(container)` vs "every value in required is present in container. Extra values … allowed"

**Expected:** `required_subset_container(container,required)` justified; `observed_mismatch`, extra container members permitted.

**Initial — FAILURE.**
- `{"relation":"required_subset_container","arguments":["container","required"],…,"spec_status":"unknown"}`. The correct relation and argument order are given (set(required) <= set(container)), but the status is unknown, so it is not endorsed.
- `equal_sets` is rejected (a correct rejection), plus an unknown/unknown item. Nothing is endorsed.

**final_A — FAILURE.**
- Bindings identical to the initial: the required relation is still `"spec_status":"unknown"`.
- `observed_mismatch` is correct, but the reason contains a **fabricated observation claim**: "Observations O3, O5, O6, and O8 show that the code incorrectly returns False when required is a subset of container with extra values in container."
  - Only O3 (`([1,2],[1])`→False) fits.
  - O5 `([1],[1,2])`, O6 `([1],[1,2,3])` and O8 `([1,2],[1,2,3])` have `required ⊄ container`, so False is spec-correct.
  - The true witness O7 `([1,2,3],[1,2])`→False is omitted. The argument roles were evidently reversed when the observations were read.
- The reason asserts the subset requirement while the binding says unknown, which is an inconsistent normative conclusion.

**final_B — FAILURE.**
- Same bindings (required relation unknown).
- The reason has a **false implementation explanation**: "…set equality … will only return True when both lists contain exactly the same elements, including duplicates." Set equality ignores duplicates. The source `set(required) == set(container)` and O2 `([1,1],[1])`→True and O4 `([1],[1,1])`→True contradict this.
- The judgment enum is correct.

**Interface:** both clean, with blanket citations (only O3 and O7 are witnesses).

**Transitions:** all three bindings retained verbatim in both. There was no move from unknown to justified (no correction). The two finals' reasons differ only in which false claim they make.

---

## E4 — `min([x for x in xs if x > 0])` vs "…or None if no strictly positive integer exists"

**Expected:** `min_positive_none(xs)` justified, eligible_selection/defined_outcome; `observed_mismatch`, empty eligible set raises.

**Initial — SUCCESS (binding-level).**
- `{"concept":"eligible_selection","relation":"min_positive_none","arguments":["xs"],"spec_quote":"Return the smallest strictly positive integer in xs, or None if no strictly positive integer exists.","spec_status":"justified"}`. This is correct and executable.
- The two extra items use the local variable `ys` (`required_subset_container(["ys","xs"])`, `any_even(["ys"])`). Both are `unknown`, so they are not endorsements and not false requirements. Their argument names are invalid (non-executable).

**final_A — SUCCESS.**
- Only the binding above, justified.
- `observed_mismatch`; reason: "raises a ValueError when there are no strictly positive integers … does not match the spec requirement to return None … Observations O1, O2, O5, O6, and O7 demonstrate this mismatch."
- All five cited observations have no positive element and `execution_status: exception, ValueError`. Evidence is selective and accurate. No false extra.

**final_B — SUCCESS.**
- Identical binding. The reason is the same in substance ("raises a ValueError when no strictly positive integer exists … O1, O2, O5, O6, and O7"). It cites the same evidence, all accurately.

**Interface:** both clean, with selective citations.

**Transitions:** the correct binding was retained. Both finals dropped the two unknown local-role items, which removes non-endorsed noise and is not a semantic loss.

---

## E5 — `if len(xs) > 2: return False; return sum(xs) <= limit` vs "no restriction … on its length"

**Expected:** `sum_le_limit(xs,limit)` justified (all lengths); `observed_mismatch`, unjustified length guard.

**Initial — FAILURE.**
- `{"relation":"sum_le_limit","arguments":["xs","limit"],"spec_quote":"Return True exactly when the sum of xs is at most limit.","spec_status":"unknown"}`. The relation and arguments are correct, but the status is unknown.
- Two `quantified_decision`/`unknown` items, both unknown.

**final_A — FAILURE.**
- `sum_le_limit(xs,limit)` still has `"spec_status":"unknown"`, so it is not endorsed.
- `observed_mismatch`; reason: "imposes a length condition … returning False when the length of xs is greater than 2, which is not specified". This is correct. Evidence O6–O9 is selective and accurate: each has length > 2 with sum == limit and returns False.
- The mismatch explanation is correct, but there is no endorsed requirement. Not a false extra.

**final_B — FAILURE.**
- `sum_le_limit(xs,limit)` is now `"spec_status":"rejected"`, while the reason says the length guard "is not specified in the original spec".
- This rejects the true relation while the reason endorses it in substance: an inconsistent normative conclusion. The judgment and explanation are correct.

**Interface:** **envelope invalid in both** (`bindings` maxItems: 4 items). In both, item 4 (`binding4`, a duplicate of binding2) is not admitted (`item_budget_exceeded`). Item 1 is admitted in both but is not endorsed. A's citation is selective; B's is a blanket citation.

**Transitions:**
- A: `sum_le_limit` unknown → unknown (retained, unresolved), plus a duplicate unknown item that overflows the budget.
- B: `sum_le_limit` unknown → **rejected**. This is a regression: an unresolved correct hypothesis became an explicit rejection of the true requirement. B also has the same overflow item.

---

## E6 — `sum(set(x for x in xs if x > 1))` vs "sum of all strictly positive … Include repeated positive occurrences"

**Expected:** `sum_positive(xs)` justified, eligible_contribution; `observed_mismatch`, 1 and repetitions dropped.

**Initial — FAILURE.**
- All three items are rejected: `sum_gt_one(xs)` (a correct rejection), `equal_sets(xs)` (arity 1/2), and `preserve_occurrences(xs)`.
- `sum_positive` is absent, so nothing is endorsed.

**final_A — FAILURE.**
- `sum_gt_one` rejected, `preserve_occurrences` rejected, plus a **new** `{"concept":"eligible_contribution","relation":"sum_positive","arguments":["xs"],…,"spec_status":"unknown"}`. The correct relation is proposed but not endorsed.
- `observed_mismatch`; reason: "sums only integers greater than 1, excluding 1 and all non-positive integers, which does not match the requirement to sum all strictly positive integers including 1."
- The reason is true but incomplete: it does not mention the `set()` deduplication (the multiplicity facet). It also states the requirement normatively while the binding is unknown.

**final_B — FAILURE.**
- `sum_gt_one` rejected, `preserve_occurrences` rejected, and `{"concept":"unknown","relation":"unknown","arguments":[],…,"spec_status":"unknown"}`. There is no `sum_positive`.
- Reason: "sums only integers greater than 1, excluding 1 … does not match the spec that requires summing all strictly positive integers including repeated occurrences." This mentions the spec's multiplicity clause but does not say the code deduplicates. No false claim.

**Interface:** both clean, with blanket citations (only O2 `[2]`→2 is a non-witness).

**Transitions:**
- Both: `sum_gt_one` and `preserve_occurrences` rejections retained; `equal_sets(xs)` dropped (harmless).
- A **added** the correct `sum_positive(xs)` hypothesis, but as unknown. This is a semantic step toward the facet, but it gives no coverage.
- B added only an unknown placeholder.

---

## E7 — `temporary = set(xs); return sorted(xs)` vs "sorted copy … preserving every duplicate occurrence" (control: no bug)

**Expected:** `preserve_occurrences(xs)` justified (ascending optional); `no_observed_mismatch`; the local set causes no output loss.

**Initial — FAILURE (binding-level; no false bug).**
- `preserve_occurrences(xs)` is `"spec_status":"unknown"`, so it is not endorsed.
- `ascending([])` is justified (true, arity mismatch); `equal_sets(xs)` is unknown (arity 1/2).
- The required relation is unresolved. Ascending alone does not cover the facet.

**final_A — SUCCESS.**
- `{"relation":"preserve_occurrences","arguments":["xs"],"spec_quote":"Return a sorted copy of xs, preserving every duplicate occurrence.","spec_status":"justified"}` (executable). `ascending([])` is justified (true, optional, non-executable arity). `equal_sets(xs)` is unknown (not endorsed).
- `"implementation_judgment":"no_observed_mismatch"`; reason: "The code sorts the list xs and returns it … The observations show that the duplicates are preserved…"
- This is true: O2–O9 retain all duplicates. No false bug is attributed to `temporary = set(xs)`.
- The reason does not explicitly mention the unused local set. I accept this, because the rubric's "local set alone is no output loss" is satisfied by not claiming a loss and by correctly locating the output at `sorted(xs)`. A stricter reading requiring explicit mention would fail both finals equally.

**final_B — SUCCESS.**
- Identical bindings. `no_observed_mismatch`; reason: "The code sorts the list xs and returns it … The observations show that the function preserves duplicate occurrences and maintains the correct order." This is true. The same note about the local set applies.

**Interface:** both clean (all ids, all relevant to the agreement claim). The endorsed `ascending([])` is non-executable as written; this does not matter, because the primary-supporting `preserve_occurrences(xs)` is executable.

**Transitions (same in both):** `preserve_occurrences` unknown → **justified** (a correction/upgrade); `ascending` and `equal_sets`-unknown retained.

---

## E8 — `xs[0] if xs else None` vs "Return the first suitable value from xs" (ambiguity control)

**Expected:** no justified unconditional `first`; `unknown`; the reason must identify that "suitable" is undefined.

**Initial — FAILURE.**
- `{"concept":"eligible_selection","relation":"first","arguments":["xs"],"spec_quote":"Return the first suitable value from xs. xs is a list of integers.","spec_status":"justified"}` endorses the unconditional first.
- The unknown hedges (`defined_outcome`/unknown and unknown/unknown) do not cancel this endorsement, and the initial has no reason field in which to acknowledge the ambiguity.

**final_A — FAILURE.**
- The only binding is `first(xs)` justified, which is a **false endorsed requirement**.
- `"no_observed_mismatch"`; reason: "The code correctly implements the requirement to return the first suitable value … returns the first element of the list if it is not empty, and None if the list is empty, which aligns with the spec."
- This silently equates "suitable" with "any element", which is an invented predicate. It does not acknowledge that suitability is undefined, and it uses the wrong judgment (unknown was required).

**final_B — FAILURE.**
- Identical binding and judgment. Reason: "The code correctly implements the requirement to return the first suitable value … returns the first element of the list or None if the list is empty, which aligns with the specified behavior."
- Same false endorsement and no acknowledgment of the ambiguity.

**Interface:** both clean. The observational claims (first element / None on []) are true; the normative claim is not.

**Transitions (same in both):** `first` justified retained (error retained). Both unknown hedges were **dropped**, so the finals are more overconfident than the initial.

---

## Summary table

| Ep | Expected | Initial | final_A | final_B | A false extra | B false extra | Mismatch explanation A / B | Interface A / B |
|---|---|---|---|---|---|---|---|---|
| E1 | preserve_occurrences(xs) | FAIL (rejected; misapplied subset endorsed) | FAIL (rejected + reason treats as req.) | FAIL (same) | no | no | correct / correct | clean; blanket ids; ascending([]) arity / same |
| E2 | count_ge(xs,limit) | FAIL* (label) | FAIL* (label) | FAIL* (label) | no | no | correct / correct (obs claim true) | clean / clean |
| E3 | required_subset_container(container,required) | FAIL (unknown) | FAIL (unknown; fabricated obs O5/O6/O8) | FAIL (unknown; false "including duplicates") | no | no | judgment right, reason false / judgment right, reason false | clean / clean |
| E4 | min_positive_none(xs) | SUCCESS | SUCCESS | SUCCESS | no | no | correct / correct | clean, selective / same |
| E5 | sum_le_limit(xs,limit) | FAIL (unknown) | FAIL (unknown) | FAIL (rejected; inconsistent) | no | no | correct / correct | envelope invalid, 4 items / same |
| E6 | sum_positive(xs) | FAIL (absent) | FAIL (added as unknown) | FAIL (absent) | no | no | true but omits dedup / true, partial | clean / clean |
| E7 | preserve_occurrences(xs); no_observed_mismatch | FAIL (unknown) | SUCCESS | SUCCESS | no | no | correct / correct | clean / clean |
| E8 | no justified first; unknown | FAIL (first justified) | FAIL (first justified, no ambiguity) | FAIL (same) | **yes** | **yes** | wrong / wrong | clean / clean |

\* E2 fails only the "concrete concept label must be semantically compatible" clause (`quantified_decision` on `count_ge`). If relation/facet coverage is scored alone, E2 is SUCCESS for initial, A and B.

**Counts (strict):**
- Initial: 1/8 SUCCESS (E4), 7 FAIL, 0 ABSTAIN.
- final_A: 2/8 (E4, E7), 6 FAIL, 0 ABSTAIN.
- final_B: 2/8 (E4, E7), 6 FAIL, 0 ABSTAIN.
- With E2 scored relation-only: 2 / 3 / 3.

**Required relation endorsed (justified) in finals:** E2, E4, E7 in both arms. It was present but unknown in E3, E5 (A), E6 (A); rejected in E1 (both) and E5 (B); absent in E6 (B). E8: false `first` endorsed in both.

**Judgment enum correct:** 7/8 in each arm (all except E8). A correct enum alone is insufficient; E1, E3, E5 and E6 have the right enum without endorsed coverage.

**Interface counts per arm:**
- Envelope invalid: 1 (E5).
- Non-admitted items: 1 (E5 item 4).
- Unknown evidence ids: 0. Exact-quote mismatches: 0.
- Endorsed but non-executable (arity) items: 2 episodes (E1 and E7 `ascending([])`). None of these is a primary-supporting item.

**A vs B semantic differences:**
- No episode has one final succeeding and the other failing, so there are zero semantic wins in either direction.
- Secondary, non-primary differences: E5 (one final rejects the true relation, the other leaves it unknown); E6 (one final adds `sum_positive` as unknown); E3 (different false reason claims); E1 (one swaps the rejected `required_subset_container` for a rejected `equal_sets`); E7 (reason detail).
- Regardless of which final received the extra feedback, the pre-registered GO conditions "≥2 tool-only semantic successes" and "handles E8 correctly" are not met.

**Initial → final pattern (both arms):**
- Corrections: E7 (unknown → justified) and E1 (false subset endorsement withdrawn).
- Retained errors: E1 (preserve_occurrences rejected), E3 (unknown), E8 (first justified).
- Regressions: E5 in one final (unknown → rejected) and E8 in both (hedges removed).
- Recurring failure mode: the model writes the correct mismatch explanation in `reason` but leaves the corresponding binding unknown or rejected. It appears to confuse "violated by the code" with "not a requirement", despite the instruction saying otherwise.
