# Saved-data mechanism audit: v34/v35, v47, v49/v52/v54

2026-10-24. Independent historical audit for `PLAN_CONCEPT_MECHANISM_20261024.md`. This report uses existing source, reports and exact cached outcomes. No model/HTTP calls, PUT/reference execution, historical rescore, paper reproduction, or changes to frozen artifacts.

**Finding:** the current evidence does not justify a new concept-guided input-generation run. It supports closing the old template and menu-selection packages, completing v53's validity study, and distinguishing concrete oracle-program mechanisms from input-generation mechanisms. A semantic abstraction is not disqualified because a tool computes its instance. Its correct use and extra utility remain separate questions.

**Scope and reproduction**

- `HISTORICAL_build.py` reads seven exact score/preparation files, plus v34 per-case tool/final records and existing v34/v35 reference caches. It extracts only literal parsing, input normalization and typed equality helper definitions from the historical source; it never imports a runner or executes generated programs.
- Reproduce with `python trickcatcher_linefacts/analysis/concept_mechanism_20261024/HISTORICAL_build.py`. Output is `HISTORICAL_MECHANISM_ROWS.json`, including source SHA-256s, 33 v34 records, 33 v47 records and 33 v49 records. These are task/arm summaries, not candidate-level semantic judgments.
- v34/v35/v47/v49 share the 33-task dev cohort. Mapping through v49 gives **24 distinct problems**; v34 records **32 unique PUT source hashes**. Do not count 33 tasks as 33 independent semantic transfers.
- v52 and v54 are different six-task pilots selected on Qwen failures; their results are not pooled with the 33-task cohort or with each other. v7/v11 fairness/round-novelty are contextual historical reports on 113 HumanEval tasks, not additional instances of this cohort.
- This audit hashed the cited current score bytes for reproducibility. It did not independently reverify every historical freeze/source manifest. Frozen score integrity conclusions beyond that remain those of the original reports.
- Reference-cache lookup during the v34 replay had **zero missing keys**. All 54 concept-arm confirmed-test labels, and all concept/placebo labels on the ten detection-discordant tasks, reproduce the frozen counts. Initial audit normalization omitted historical parse-call normalization; the saved script now uses the original helpers and reproduces every checked count.

**v34: evidence parity and all discordant tasks**

Source: `pipelines/v34_ftplacebo/ft_run.py`, `guidance()` and `placebo_guidance()`; frozen score: `out/pipelines/v34_ftplacebo/humaneval/faulttemplate/openrouter/vibepass_half/score.json`.

Both arms receive selected inputs and PUT outputs. `fault-template` additionally receives site/code, type/meaning, hypothesis, mutation alternatives, tool evidence, and **alternative outputs on those inputs**. Placebo contains neither alternative output nor the equivalent raw mutant evidence. This is a concept-plus-evidence package comparison, not a clean test of abstract representation with equal evidence. Alternative outputs are candidates, not normative expected values, but still supply extra concrete answer possibilities.

The frozen registered result remains 18/33 vs 12/33 confirmed tasks, eight wins and two losses, FA tests 27 vs 23; registered NO-GO remains unchanged. No retrospective normalization changes that verdict.

All detection-discordant tasks below were examined in saved final records and caches. `selected expose` means a supplied selected concept input is contract-valid and distinguishes PUT/reference. C/P tests are confirmed tests, not all emitted tests. This does not measure whether newly generated tests semantically realize the fault hypothesis.

| Task | C/P confirmed tests | Selected expose | C/P FA tests | Placebo incomplete calls | Interpretation |
|---|---:|---:|---:|---:|---|
| 36 | 1/0 | 1 | 0/1 | 0 | Win with supplied exposure, new confirmed input |
| 69 | 1/0 | 0 | 2/0 | 0 | Win without supplied exposing input |
| 70 | 0/2 | 0 | 6/0 | 0 | Loss; concept has wrong assertions as well |
| 73 | 1/0 | 0 | 1/0 | 1 | Win overlaps placebo truncation |
| 75 | 2/0 | 0 | 4/2 | 0 | Win without supplied exposure; more FA |
| 77 | 0/1 | 0 | 0/1 | 0 | Loss |
| 96 | 2/0 | 0 | 0/0 | 0 | Win without supplied exposure |
| 103 | 6/0 | 0 | 0/1 | 0 | Win without supplied exposure; concept has one schema error |
| 132 | 2/0 | 6 | 0/0 | 0 | Strong supplied exposure; new confirmed inputs |
| 168 | 1/0 | 3 | 0/0 | 2 | Win overlaps placebo truncation |

The eight wins contain **16 confirmed tests, zero of which reuse a selected concept input**. Five wins (69,73,75,96,103) have no selected exposing input. Across the cohort, selected inputs expose bugs in 11/33 tasks, reproducing the existing post-hoc mechanism report.

These facts refute “the tool already supplies the final revealing tests and the model simply replays them” as the explanation of these wins. They do **not** prove that semantic framing caused the new tests, or that a hypothesis is false whenever its supplied input does not expose the bug. No executable semantic-obligation realization is logged, no equal-evidence raw arm exists, and truncation contributes a competing explanation for two wins. Obligation realization is therefore **unknown**, recorded explicitly in the JSON.

Two pairs share problem identities across opposite outcomes: tasks 69/70 and 75/77. This reinforces problem-level grouping rather than treating every PUT outcome as an independent semantic success.

**v35: keep the stop; avoid interpreting a partial repair as a causal location**

Frozen `out/analysis/v35_concept_ceiling/ceiling.json` has 33 rows: template pool exposes 17; at least one surviving mutant agrees with reference on an exposing input in 14; strict agreement on all exposing inputs in 8; any selected concept locating line in 11; rank-1 in 6. Gate `14 < 17` gives **STOP**.

This is a ceiling for this pool and mutant catalogue. It is not a proof of arbitrary-input repair correctness or true fault-location accuracy. The earlier cached whole-valid-pool audit in `analysis/fault_localization_review_2026-10-20.md` finds just four regression-free correcting-survivor tasks (46,85,121,132). That audit was read as contextual evidence, not recomputed here. Template reach is weaker than plain Qwen's 19/33 input discrepancies in the historical run, so improving ranking alone cannot cure this package.

**v47: all-task selection result, not a new-generation experiment**

All 33 frozen rows are included in the structured output. The 66 calls finish `stop`, parsed 33/33 per arm. Spec+code selects inputs exposing a bug on 16 tasks vs uniform-random expectation 18.25 and first-three 18; spec-only reaches 15 vs 17.96 and first-three 18. Perfect menu reach is 23 and 22, respectively. The registered selector is **NO-GO**.

`select_run.prompt()` supplies signature, full spec, public tests, optional numbered code, and menu lines `id: text`. It omits concrete candidate inputs, execution evidence and per-item validity summaries. Thus the model faces a weakly observed selection problem, but random-like performance is not logically inevitable: it does have task semantics. A counterfactual input/evidence-rich selector has not been evaluated. Merely supplying more text is not a supported changed hypothesis without identifying why the unavailable evidence would discriminate candidates on the saved cases.

The menu is tool-generated, with broad operators for input classes/boundaries and fixed instances bound to parameters; it is not the v43 handwritten expected-relation vocabulary. Generic templates can be legitimate reusable abstractions even when this selector fails. No obligation-driven new generation or causal use is measured here.

**Parser criticism needs version qualification.** Old v44/v47 partial-power parsing is real. `analysis/v48_e2e_oracle/menu_fixed.py` already adds AST numeric parsing, `len()` handling for supported chained inequalities, explicit unsupported bounds, per-argument range expansion, negative-value sampling fixes and menu deduplication. It remains a numeric-bound parser, not a relational-constraint solver. Do not propose reimplementing these existing fixes, and do not attribute current v53 behavior to the old parser without tracing which function it calls.

**v49: all discordant tasks and the yield mechanism**

All 33 task rows are recorded. Under the same decisive inputs, primary quorum and cap20:

| Task | defn/brute valid programs | defn/brute confirmed tasks | defn/brute confirmed tests | defn/brute FA tests |
|---|---:|---:|---:|---:|
| 103 | 2/0 | 1/0 | 20/0 | 0/0 |
| 124 | 4/1 | 1/0 | 20/0 | 0/0 |

These are **all** defn/brute detection discordants; no brute-only task exists under this endpoint. Exact raw program artifacts are under `out/analysis/v49_defn_oracle/programs/{defn,brute}/{103,124}/`, score rows under the frozen `score.json`; prompt code is `analysis/v49_defn_oracle/gen.py`. Structured records include task metadata and score paths.

Aggregate: defn 12/33 tasks, 93/165 valid programs, precision .59, FA145; brute 10/33, 78/165 valid, precision .62, FA100. The registered concept rule is **NO-GO** (+2 not +3; two not three problems; more FA). The original registered manual audit of the two wins passed; this audit did not re-prove the generated algorithms on their full domains.

The observed gain is associated with executable-program yield. This can be a valid treatment mechanism: headings/decomposition may help the writer produce a usable oracle. Restricting to tasks where both arms produced enough valid programs conditions on a post-treatment variable; equal detection there does not establish zero total concept-package effect. It does limit a stronger claim about better oracle judgment given capable programs. No line-by-line/untyped decomposition control isolates the categories from planning/formatting effects.

This is an **oracle-program** experiment using shared inputs, not evidence that concepts cause better input generation. Preserve that boundary. The brute-family vs TC differences also combine oracle family, PUT visibility, number of programs and decision rule; they are not a semantic-concept ablation. The 3–5% vs28% common-mode pattern is relevant engineering evidence, not a universal model-strength explanation.

**v52 and v54: the narrow mechanism signal and its scope**

- v52 frozen score: six Qwen-failure-selected tasks, Sonnet defn5/6 vs brute4/6; all 18/18 programs in each arm valid. Task65 is the only detection discordant. Inspected all six saved program texts for task65: defn enumerates valid run/group structures (one program also memoizes suffix optima), whereas brute enumerates arbitrary 26-letter strings and filters for valid runs. Existing execution report attributes brute's miss to timeout. This is a concrete **feasible enumeration-space mechanism**. It is associated with the definition prompt; it is not a clean proof that its concept labels, rather than planning, produced the gain.
- v52's report/cached score classify all56 FA per arm as invalid inputs, and task141 as abstention. Those statements concern this universe/pilot; “strong oracle correct on all valid inputs” must not be generalized beyond it. Completing v53 validity checks is the existing next experiment for this failure class.
- v54 has six different Qwen-failure-selected tasks: both arms6/6; tc18/18 right programs vs tc_concept16/18, FA3 vs0. One common-mode facet remains on task101 in the concept arm. No measurable task-detection gain under the registered gate. Ceiling and selected cohort constrain the question; the result does not prove concepts are redundant for every strong writer. Approximate non-application of shown edits does not prove absence of all semantic influence.

**v7/v11 context: avoid repeating witness rediscovery**

The fair v11 report has concept61.0 vs placebo57.7 vs toolinput64.3 per run on dev113. The later registered round-novelty analysis (`analysis/round_novelty_20261023/RESULTS.md`) reports matched R2-new35.5 vs20.5, p=.15, and concept beyond-witness11 vs placebo23; 28/39 concept R2-new events are on tasks already found by witness-only. The registered verdict is NO SIGNAL. These are contextual results read from reports, not rerun here. A new method must establish discovery beyond supplied witnesses and count actual verified input yield.

**G1 decisions for the current plan**

| Proposed continuation | Decision from this historical evidence |
|---|---|
| More fault-template runs/ranking on v34/v35 | STOP: registered ceiling and weak attribution; no new mechanism |
| Same v47 selector with another label taxonomy | STOP: failed selector; no new discriminatory evidence identified |
| Refix old numeric parser bugs | Already addressed in menu_fixed for supported forms; review current callers and residual gaps instead |
| Finish v53 validity comparison and then inspect relational-validity losses | CONTINUE existing work: concrete invalid-input failure, registered controls, saved answers; no new calls authorized by this report |
| Bounded semantically valid enumeration for oracle programs | Passes identification of a concrete failure mechanism on v52 task65; only oracle-side feasibility evidence. Not sufficient for a new concept-guided input-generation experiment |
| Joint construction that respects verified relational constraints | Conditional engineering hypothesis: independent argument sampling demonstrably breaks relations; require v53 grounding/safety result and saved-data reach/retention evidence before implementing/launching a new generation arm. Validity improvement alone is not concept gain |
| New generic semantic-contract input pipeline | Not yet G1-ready from these historical results alone. Need a supported gap, correct binding and a discriminating generation mechanism beyond the failed versions; v50 review may inform binding feasibility but cannot substitute for input evidence |

The next justified actions are the existing v50 semantic review, v53 scoring review/result, and a concept contract specifying supported roles and realization checks. Neither larger cohorts nor a stronger writer is proposed as a remedy for the same null treatment. Fresh-cohort confirmation remains conditional on the plan's later gates.
