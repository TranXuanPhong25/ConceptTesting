# Independent v23 terminal semantic and assertion review

Fresh clean-context luna_v23_output_review inspected all16 saved cases, native frozen
report and236 cached candidate slots.1092/1092generation hashes verified. No model,
endpoint, worker, new code execution, raw/source repair or output rescoring by reviewer.
Qualitative model-assisted review, not independent human semantic gold.

C/D/H are concept_chain/direct_chain/hyp_only. Full16fixtures include7bug cases:
f02/f04/f06/f08/f10/f12/f16;8correct and1ambiguous. Correct bug assertion inputs:

|Case|Source/actual output finding|C /D /H|
|---|---|---:|
|f01|Correct sorting with multiplicities; all concepts/behavior/hypotheses faithful.|0/0/0|
|f02|Returned set loses duplicates; all arms expose it.|3/3/4|
|f03|Correct inclusive count, occurrence counts preserved.|0/0/0|
|f04|Strict > should be >=; raw concept hypothesis reasons correctly but malformed JSON blocks C/H.|blocked/4/blocked|
|f05|Correct required subset, extras allowed, duplicates irrelevant.|0/0/0|
|f06|Equality should be subset; all arms expose it.|2/2/3|
|f07|Correct positive min/None fallback.|0/0/0|
|f08|Empty eligible list raises min error instead of None; all expose it.|2/4/3|
|f09|Correct universal evenness, empty=True.|0/0/0|
|f10|Existential any should be universal all; all expose it.|3/3/4|
|f11|Correct inclusive sum limit and unrestricted length.|0/0/0|
|f12|Wrong length guard; all expose it, C also adds one false alarm.|2/3/3|
|f13|Undefined suitable: C/H preserve unknown/abstain; D invents first-element semantics.|unscored|
|f14|Unused local set does not affect returned sorted list; all understand it.|0/0/0|
|f15|Dedup branch under ifFalse unreachable; all understand it.|0/0/0|
|f16|Excludes1 and deduplicates positives; raw C hypothesis correct but malformed JSON blocks C/H.|blocked/6/blocked|

Native correct-assertion/detected bug tasks: C5/7,D7/7,H5/7. False-alarm cases1/0/0,
blocked2/0/2. Input/revision stage failures0 for all scheduled calls. C/H each have2valid
abstention stages atf13.152received responses: concept16/16,behavior16/16,hypotheses
30/32valid, inputs44/44, revision44/44. No claim that blocked8generation calls happened.

All16 concepts retain central requirements, domains, boundaries/quantifiers and
multiplicity. All16behavior summaries match returned semantics. f04 raw C hypothesis
correctly finds equality counterexample but ends with malformed comma/quote. f16 raw
C hypothesis correctly finds exclusion of1/dedup but repeats trigger and ends malformed.
Both remain rejected; no fence/JSON/field repair. Thus blocked failures are serialization,
not evidence that concept made fault reasoning worse.

f12 C revision input([1,2,3],5) expectedTrue is wrong: sum6>5, goldFalse and observedFalse.
This is a genuine false alarm from a model-authored expected value, despite other
correct bug assertions in that arm. f06 H revision([1,2],[1,1]) expectedTrue is correct
but predicted_actualTrue is wrong (observedFalse); test assertion remains useful.

All236slots observed: C74,D88,H74. Expected-value correctness C73/74,H74/74,D84/84
scorable plus4undefined f13 values. Predicted-actual correctness C74/74,D88/88,H73/74.
f13 direct verdictconsistent invents a first-value requirement; its4generated expected
values have no authoritative normative basis and remain unscored. FA0 there is not
semantic correctness. Concept/hyp-only show a qualitative ambiguity-handling benefit,
not extra detected bug tasks.

Hyp_only uses exact same concept_chain hypothesis for16/16cases, removing explicit
concept only at generation. Therefore both inherit f04/f16 block and f13 uncertainty.
C adds no bug-case gain over H and adds f12 false alarm. D has best observed scorable
assertion coverage but unsupported ambiguity assumptions. No general concept benefit,
causal harm theorem, matched-total-cost or benchmark/D_IO claim.

All152native request messages retain system/user content; CLI flattens their roles
under Codex base instructions. Concept sees spec/signature only; behavior code/syntax
only; downstream sees relevant model claims/public bases. No top-level evaluator or
hidden-witness fields found. Fresh CLI contexts, requested model/low only unless server
ID emitted; schemas exposed, executionhostdisabled,0recorded task tool attempts.

Cumulative old+new authoritative cost153CLIinvocations/152responses/1unknown quota
attempt, known1,176,568input/31,383outputtokens. Native report costs cover imported old
transport only and must not be interpreted as total. Reused73accepted outputs are
same trajectory, not new independent samples;79newresponses complete it after quota.
