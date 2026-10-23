# v48 end-to-end: concept-selected inputs → TrickCatcher program-variant oracle → assertions (CPU, saved LLM outputs)

Written 2026-10-22 (Claude) before any v48 code, before v46 `tc` programs and v47 picks are complete, and before any
v48 reference/oracle output. Motivation: review `analysis/v7_v47_audit_review_claude_20261022.md` (R2–R4, R7): v47
measures only whether picked instances *contain* an exposing input; the repo's matched-budget winner is TC-full
(v11: concept-hybrid 29.75 vs tc_full_v2 42.99, W/L 2/25); v46 programs are executable on any input. v48 tests
Codex's criterion #3: does concept selection improve **correct assertions with false alarms controlled**?

## Prior art
v47 (LLM picks 3 menu instances; input-side metric only), v46 (TC variants as oracle on 607 mutant questions), v44
(kinds ≈ matched random by reach), v41/v42 (CPU selection rules, no-go), v11 tc_full_v2 (HumanEval). New: the full
chain input selection → program oracle → emitted assertion, scored with false alarms, against no-concept controls
at the same input count, plus a per-task failure decomposition that names the next bottleneck.

## Material (frozen, no new LLM calls)
- `out/analysis/v47_concept_select/{prepared.json, calls/}`: menus, instances (≤ 32 shown inputs), picks (spec+code,
  spec-only). Picks parsed with v47 `parse_picks`.
- `out/analysis/v46_mutoracle_fixed/programs/tc/<task>/<i>.json`: 10 TrickCatcher PUT-guided variants per task
  (verbatim tc-full templates). Loaded and validated exactly as v46 (`program_module`, PUT preamble, entry wrapper,
  valid = same output as the PUT on every public base input). `tc_concept` programs are not used.
- v41 Hypothesis pool (`iorel.OUT/cases/<task>/put`), the no-concept sampler.
Tasks without v46 `tc` programs (v42 had no question) or with 0 valid programs get no tests in **every** arm (reported).
Records with `finish_reason = context_overflow` (task 75, v46 owner note) count as "no program", not as an invalid
variant. v46 records are read-only (their `digest` is checked by v46; never rewritten).
`pool_matched` universe: a seeded random subset of ≤ 600 v41 pool inputs per task (`random.Random('v48/pool/<task>')`),
to bound CPU; `pool_matched` draws come from this subset.

## Oracle (tc-full vote, v46 primary rule)
On an input where the PUT returns normally, valid programs whose output differs (typed `same`) from the PUT form
groups by value; if any group exists, one test is emitted with the largest group's value (ties: program order).
Secondary (reported): consensus rule (≥ 3 valid programs, all `ok`, all agree, differ from PUT).
Cap (tc-full): at most 20 emitted tests per task per arm, kept in a fixed order (sha256 of the input literal);
uncapped numbers reported.

## Arms (input sets per task; all use the same oracle and cap)
1. `llm_code`: union of shown inputs of the v47 `spec+code` picks. 2. `llm_spec`: same for `spec-only` picks.
3. `random3`: 3 random items of the `spec+code` menu (expectation over 2000 seeded draws).
4. `first3`: items M1–M3. 5. `kind_matched`: random items of the kinds the model picked (2000 draws).
6. `heuristic`: first menu item of each of the first 3 available kinds in v7's fixed priority mapped to v47 kinds
   (OUTCOME/STMT→coverage, MUTANT→mutation, BOUND→boundary, SHAPE→class, NUM→spec_range, value_biased).
7. `all_menu`: all `spec+code` menu items (no selection).
8. `pool_matched`: n random v41 pool inputs, n = `llm_code`'s distinct input count for the task (2000 draws; no concept).
Unparsed picks (0 ids) give an empty input set for the LLM arms (counted, not repaired).

## Scoring (references only here; v46 `judge_test` semantics)
A test is confirmed iff the input is contract-valid, PUT ≠ reference on the official path and the asserted value is
`same` as the reference; otherwise FA (unconfirmed counted separately). Generated (non-pool) inputs get one reference
batch per task as in v47 `score`. Per arm: confirmed tasks, tests, FA tests, FA tasks, precision.

## Decision (registered)
Concept selection is an end-to-end benefit (GO) iff for `llm_code` (capped): confirmed tasks ≥ E[random3] + 3,
≥ E[pool_matched] + 3, ≥ E[kind_matched] + 2, ≥ heuristic + 2, and FA tests ≤ E[random3 FA tests]. Otherwise NO-GO.
`llm_spec`, `first3`, `all_menu`, consensus rule: reported only.

## Failure decomposition (diagnostic; decides the next direction, no gate)
Per task, for `all_menu` and `llm_code`: (a) no exposing input in the set (selection/reach); (b) exposing input present
but every valid variant equals the PUT there (common-mode: variants copy the bug); (c) a variant has the reference
value on an exposing input but the vote emits another value (vote); (d) emitted but value wrong; FA split into invalid
input / valid input with PUT right (spurious disagreement) / PUT wrong but wrong value; (e) no valid program.

## Amendment 1 (2026-10-22, before any v48 code/output; must-fixes from Codex's read-only verification)
- **Freeze before scoring:** score refuses to run unless all planned v47 call records and all planned v46 `tc` records
  (31 tasks × 10) exist; it writes the sha256 inventory of every input artifact into the score file. Missing planned
  records = `incomplete`; a complete task with 0 valid programs = legitimate abstention.
- **All 33 tasks visible:** tasks without planned programs (6, 103) abstain in every arm; the 31-task common subset is
  reported separately. No substitute programs (never reference-informed).
- **Order and cap:** the same reference-blind order (sha256 of the input literal) and ≤ 20 tests/task apply to every
  arm; uncapped results reported.
- **Input-count matching:** natural 3-instance results plus count-matched controls: `menu_matched` = n random inputs
  from the union of the task's `spec+code` menu inputs (separates selection from v47's generators), and
  `pool_matched` (v41 pool, no concept). n = `llm_code`'s distinct input count. Both by exact enumeration where
  feasible, else 2000 seeded draws.
- **random3 exact:** enumerate all menu triples through the full union → order → cap → oracle → score procedure.
  `kind_matched` likewise enumerates over items of the picked kinds.
- **Decision rule** (replaces the original): GO iff `llm_code` (capped) confirmed tasks ≥ E[random3] + 3,
  ≥ E[menu_matched] + 3, ≥ E[pool_matched] + 3, ≥ E[kind_matched] + 2, ≥ heuristic + 2, and FA tests ≤ E[random3 FA tests].
- **Vote/equality semantics frozen (v46):** largest differing group including singletons, ties by program order,
  typed `same`, unparsable/timeout outputs excluded; inputs where the PUT raises or times out emit no test (v46/tc-full
  comparison semantics) and are counted per arm; a program returning `None` normally is a value, not abstention.
- **Reported per arm:** correct assertions (confirmed tests), confirmed bug tasks, FA tests, FA tasks, unconfirmed
  (counted as FA), precision, PUT-exception inputs. Upstream LLM calls/tokens per arm (v47 picks; v46 programs shared)
  are reported; `pool_matched` + tc is TC-full-style, not the complete TC-full baseline (its LLM input generators are
  not run).
- **Generality fixes (separate, no effect on this run):** `menu_fixed.py` = v47 tool side with the audited defects fixed
  (Python `**`/`len()` bounds parsed or reported unsupported, per-argument range comparison, set-based menu dedupe,
  log-uniform over negative ranges, kind errors make the case incomplete, digest-checked cache reuse). CPU tests, plus a
  report of which current33 menus would change (expected: the 5 order-duplicate tasks). For future fresh cohorts only;
  v48 scoring uses the frozen v47 menus/picks.

## Amendment 2 (2026-10-23, after an independent read-only Opus code review; before any full execute or reference read)
Engineering/reporting only; arms, oracle, cap and decision unchanged.
- Inventory keys outside the repo (pytest tmp paths) are absolute; 2 previously failing tests now pass (45 total).
- “PUT-exception inputs” → `put_no_test_inputs`: every input where the PUT does not return a parsable value
  (exception, timeout, batch `skipped`, unparsable) — all emit no test.
- Failure decomposition: every exposing input gets one class (`put_not_ok`, `vote_right`,
  `vote_wrong_variant_had_ref`, `vote_wrong_value`, `common_mode`, `variants_failed` = no variant returns a parsable value
  different from the PUT); each task gets one `primary` failure in a fixed order (e no valid program → a no exposing
  input → confirmed → lost to cap → c vote wrong although a variant had the reference value → d vote wrong value →
  b common-mode → b2 variants failed → PUT not ok); summary totals per arm.
- Official-path checks for reach only on the decomposed arms' inputs (`all_menu` ∪ `llm_code`); emitted tests of every
  arm are still judged on the official path (lazily), as registered.
- Reference batch for generated inputs: on a sandbox failure, rerun in chunks of 100; a failed chunk is
  `reference_skipped` (reported, FA split bucket `reference_skipped`, not `invalid_input`).
- Known limits of `menu_fixed.py` (future cohorts only, not used here): negative log-uniform gives 0 a large share;
  the unsupported-form check can flag prose lines with one-letter parameter names; `prepare_case` omits
  `universes`/`pool_max` needed by a v47-style score.
