# v23 Qwen diagnostic16 — complete, mechanism not established

2026-10-17. The user-authorized detached run finished normally:160/160 logical and
physical completion requests, no retry/transport failure or unknown token usage.
Frozen source, source-bound CPU gate, all generation hashes and unchanged parent v7
hashes verified. All raw artifact responses match their Qwen transport records and
tokenizer-bound prompt usage. Original treatment/prompts/schemas/data remain unchanged.
No relaunch, paid API call, real20, benchmark or held-out execution in this analysis.

**Result:** schema reliability improved, but concept-guided hypothesis/test reasoning
is not reliable enough to establish the intended mechanism or justify expansion.
All three arms produce correctly specified failing assertions for only2/7 buggy cases.

## Complete comparison

The16 seen authored cases contain7 buggy implementations,8 correct implementations
and1 ambiguous spec. Counts below retain the full16-fixture denominator; bug detection
is a subset of the7 declared buggy cases. No case was blocked or discarded.

| Measure | concept_chain | direct_chain | hyp_only |
| --- | ---: | ---: | ---: |
| Mechanically valid input/revision artifacts |32/32|32/32|32/32|
| Proposed candidate slots |96|96|96|
| Observed admissible candidate slots, including repeats |52|69|66|
| Unique scored inputs, deduplicated within each case |51|67|61|
| Cases with an input discrepancy under fixture oracle |4|5|5|
| Unique inputs with a fixture-oracle discrepancy |12|13|15|
| Cases with a correctly specified failing assertion |**2**|**2**|**2**|
| Unique correctly specified failing assertions |2|4|2|
| Cases containing a false assertion that fails on PUT |2|5|4|
| Of these, cases whose PUT is actually correct |2/8|2/8|3/8|
| Invalid literal/arity/prediction slots |41|25|27|
| Domain-filtered slots |3|2|3|
| Valid abstention artifacts |0|0|0|

An input discrepancy compares PUT with an independent fixture oracle. A correct
assertion additionally requires the model's expected output to match that oracle.
A false assertion here has an incorrect expected output and fails on PUT; it may
occur on an actually buggy PUT too. Wrong expected outputs that merely copy buggy
PUT behavior pass silently and are a different loss. The ambiguous case has no
invented oracle. No observed input discrepancy is counted as a bug assertion by itself.

concept_chain and hyp_only assert correctly on **f12/f16**; direct_chain on **f06/f16**.
The concept/direct result is one gain and one loss, with no net case benefit. Removing
explicit concept presentation with the same hypothesis leaves the same correct
assertion cases. Different candidate validity/counts and shared preparation costs
prevent a pure semantic-content or total-cost-matched superiority claim. All shared
public-base seeds pass, so observed discrepancies are outside that seed pool; this
is not a comparison against the full v7 fuzz-witness pool.

## All16 cases: semantic review and practical outcome

C = concept-guided hypothesis, D = direct hypothesis; I/A columns are input-discrepancy
count and correct-assertion count **within that case**. H uses C's exact hypothesis.
Semantic judgments were independently checked by root and clean-context reviewer
`v23_semantic_review`. They are model-assisted qualitative adjudication, not human gold.

| Case | Intended behavior / status | C / D hypothesis review | C I/A | D I/A | H I/A |
| --- | --- | --- | ---: | ---: | ---: |
|f01|Correct sorting preserving occurrences|Both consistent; S2 non-list error claim too strong|0/0|0/0|0/0|
|f02|Bug: returned `set` loses duplicates|Both incorrectly consistent despite correct S1 multiplicity and S2 dedup summary|3/0|0/0|3/0|
|f03|Correct inclusive threshold count|Both consistent; S2 fabricated empty limitation; generated count arithmetic error|0/0|0/0|0/0|
|f04|Bug: `>` instead of `>=`|Both identify comparison mismatch; supplied `[1,3],2` trigger passes both|3/0|3/0|4/0|
|f05|Correct subset membership|Both consistent; concept omits explicit iff/extras/duplicate invariance|0/0|0/0|0/0|
|f06|Bug: equality instead of inclusion|Both incorrectly consistent, relying on equal-set base case|0/0|2/2|0/0|
|f07|Correct minimum with empty guard|C consistent; D invents missing guard already implemented|0/0|0/0|0/0|
|f08|Bug: minimum of empty eligible group raises|Both correct mechanism and sufficient admissible trigger; assertions fail downstream|0/0|3/0|2/0|
|f09|Correct universal even predicate|Both consistent; concept loses explicit boolean iff/empty=True|0/0|0/0|0/0|
|f10|Bug: `any` instead of `all`|Both identify quantifier mismatch; all-even trigger does not distinguish|0/0|0/0|0/0|
|f11|Correct sum bound|Both invent empty-input fault; S2 limitation poisons alignment|0/0|0/0|0/0|
|f12|Bug: extra length guard|Both mismatch labels, but wrong empty/noninteger fault explanation and passing trigger|3/1|2/0|3/1|
|f13|Ambiguous suitability criterion|S1 records no uncertainty; both overclaim mismatch and neither abstains|0/0|0/0|0/0|
|f14|Correct sort; unused local set|S2 recognizes unused set; both wrongly propagate dedup to return|0/0|0/0|0/0|
|f15|Correct sort; unreachable dedup|S2 recognizes dead branch, but both invent empty-input fault|0/0|0/0|0/0|
|f16|Bug: excludes1 and loses duplicates|C uses out-of-domain noninteger issue; D correctly identifies dedup and a sufficient trigger|3/1|3/2|3/1|

Coarse known-fixture verdict labels match10/16 for C and9/16 for D. These counts
overstate usable fault reasoning: a correct fault mechanism **and** admissible sufficient
trigger are present for C only at f08, and for D at f08/f16. f04/f10 have the right
mechanism but nondiscriminating triggers; f12/C-f16 have a positive bug label with the
wrong mechanism. This rubric is post-run diagnostic analysis, not a preregistered gate.

## Where the chain loses the mechanism

1. **Abstraction loses obligations/uncertainty.** S1 mainly restates spec; f09/f10 omit
   empty/boolean semantics, and f13 fails to mark undefined `suitable`. No spec/code
   leakage was found at the actual32 preparation request boundaries: concepts see
   only signature/spec, behaviors only masked code/syntax.
2. **Correct code summaries do not produce reliable alignment.** S2 recognizes the
   actual returned dedup/equality/unused/dead operations, yet S3 makes the opposite
   claim on f02/f06/f14. Unsupported `limitations` invent empty-input defects and
   out-of-domain obligations, which appear directly in f11/f12/f15/f16 hypotheses.
3. **A correct mismatch does not imply a usable trigger.** f04 supplies a base input
   without equality; f10 supplies an all-even list. Neither distinguishes the two
   candidate behaviors. Source citations and observed line hits do not fix this.
4. **Input syntax still matters despite perfect JSON.** Across288 proposed slots,
   93 have literal/arity/prediction errors (41/25/27 by arm), and8 are filtered for
   violating the original domain. Missing singleton tuples recur after feedback;
   f08 concept inputs have expected `None` but bare predicted `ValueError` rather
   than the required exception transport, so those slots are not executed. No repair
   or counterfactual rescoring was applied.
5. **Expected-output drift toward PUT suppresses assertions.** f02 duplicate inputs
   expect deduplicated lists; f04 equality inputs expect strict counts; f08 direct/H
   expect the implementation's exception rather than spec `None`. Among admitted
   candidate slots, incorrect expected outputs equal PUT on10/8/14 slots for C/D/H.
   This is an observed output pattern, not evidence of hidden-reference leakage or
   proof that native feedback caused the drift.
6. **Some successes do not substantiate the hypothesis.** C/H eventually assert
   `f([1,2,3,4],11) == True` on f12 and `f([10,10,10]) == 30` on f16. Both are genuine
   failures, but the upstream hypotheses are wrong and predicted actual outputs are
   also True/30. These discoveries cannot demonstrate the proposed causal reasoning
   chain. D catches f06 even after its hypothesis incorrectly says consistent.

All96 input/revision artifacts contain proposals; no formal abstention occurs, even
for the ambiguous spec. All stages pass schema checks, while malformed candidate
slots remain explicit invalids. Revision repeats16/5/8 previously invalid argument
or prediction forms for C/D/H. Raw evidence/contradictions remain in frozen artifacts.

## Costs and interpretation

| Group | Completion calls | Input tokens | Output tokens |
| --- | ---: | ---: | ---: |
|Shared concept/behavior preparation|32|9,647|2,473|
|concept_chain hypothesis + inputs/revision|48|60,082|9,422|
|direct_chain hypothesis + inputs/revision|48|59,985|9,496|
|hyp_only inputs/revision, reusing C hypothesis|32|45,308|6,830|
|**Total**|**160**|**175,022**|**28,221**|

153 tokenizer metadata calls,0 metadata errors. Runtime53m31s. No retries, no unknown
completion usage and no additional Qwen/oracle requests during analysis. Shared
preflight/execution costs are outside these completion-token totals.

The separate gpt-6-luna/low supplied-concept probe remains a separate null result:
both arms catch3/3 buggy cases in its5-case seen subset. It is not pooled with Qwen
and does not validate Qwen extraction or the chain's stage isolation.

**Disposition:** completed diagnostic, no promotion and no automatic benchmark.
The next proposal, if requested, needs to address semantic alignment, distinguishing
conditions and independent expected-output reasoning as well as argument transport.
Another broad benchmark run would not resolve these demonstrated mechanism failures.

Recompute/verify with `CoverUp_concept/.venv/bin/python -B
trickcatcher_linefacts/analysis/v23_qwen_diagnostic_results.py`.
[Machine-readable analysis](v23_qwen_diagnostic_results.json) preserves all16 semantic
packets and per-case scores. Original raw Qwen requests/responses, native/traced
records and source/generation snapshots remain under the unchanged diagnostic out root.
