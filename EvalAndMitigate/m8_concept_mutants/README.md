# m8_concept_mutants: concept-catalogue mutants → distinguishing inputs → blind A/B arbiter → tests

## Idea (the user's)
LLM-written docs and tests invent edge cases that never occur, miss the real ones, and assert that the code works as it
is instead of hunting for bug cases. Proposed fix: a **mutant generator driven by a predefined concept catalogue**, so
the LLM sees concrete alternative behaviours at the code's real edge points and only has to say which one is intended.

## Method
1. **Concept mutants** (`mutate.py`, tree-sitter, no LLM). First-order edits of the focal method of the buggy checkout,
   each a full replacement of the focal method in a scratch copy of its source file (the shared checkout is never
   written; the d4jproj volume is mounted read-only). Operators, by the shared vocabulary:
   - C1 null: swap `== null`/`!= null`; drop a null check (→ `false`/`true`); insert a null guard on a reference
     parameter or a reference field the method reads (return each default, or throw IAE); `return null` ↔ default
     (`""`, empty array/collection); null-safe deref (`x.toString()` → `String.valueOf(x)`, `x.equals(y)` → `Objects.equals`).
   - C2 empty/blank: insert an empty guard on String/CharSequence/array/collection parameters (defaults, or return the
     argument); drop an emptiness check (`isEmpty`, `length()==0`, `size()>0`, …); empty ↔ blank (`isEmpty`↔`isBlank`,
     `.trim()` before the check).
   - C3 boundary: `<`↔`<=`, `>`↔`>=`; ±1 on `length()/size()/.length`; ±1 on indexes (array access, `charAt`,
     `substring`, …); ±1 on loop bounds; ±1 on integer constants in comparisons.
   - C4 error contract: throw → return default; literal return → throw IAE; thrown exception type swap; catch widen /
     narrow; remove a catch (or the whole try); insert `if (intParam < 0) throw IAE`.
   - C5 format/escaping: drop a char/string switch case; let a case fall through; drop a char/literal branch
     (`c == 'x'` → `false`, `.equals("lit")` → `false`); drop a transform in a replace chain (`x.replace(..)` → `x`).
   - C6 numeric: `int`↔`long` locals and casts, `float`↔`double` casts; overflow guard (`Math.addExact` /
     `subtractExact` / `multiplyExact`); rounding (ceiling division, `floorMod`, `floor`↔`ceil`↔`round`); special values
     (drop `isNaN`/`isInfinite`, insert a NaN/infinity rejection for floating parameters).
   - C7 chars/locale: add `Locale.ROOT`; remove a Locale argument; swap `Character.isX` predicates; case-fold changes
     (`toUpperCase`↔`toLowerCase`, drop a case fold, `equals`↔`equalsIgnoreCase`, `regionMatches` ignoreCase flip);
     surrogate handling (`isHighSurrogate` → `false`, `charCount` → 1, `codePointAt` → `charAt`).
   - C8 state: skip a field/state update; repeat it (idempotence); swap two adjacent expression statements.
2. **Generic control mutants** (same file): PIT-style operators unrelated to the catalogue: negate conditionals
   (`==`↔`!=`, `<`↔`>=`, …, negate a boolean if/while condition), math operator swap, return values (negate boolean,
   `x==0?1:0`, `null`/throw), void-call removal, increments, invert negatives, and PIT's non-default but standard
   remove-conditionals (if/while condition → true/false), non-void call → default, naked receiver, argument
   propagation, constructor call → null, inline constants. The catalogue's conditionals-boundary is excluded. Generic
   mutants whose method text equals a concept mutant are dropped (the overlap stays in the concept arm).
   Candidates are deduplicated by method text; at most 80 per method and arm (stratified round robin, seed 8).
3. **Phase 0 runs** (`phase0.py`, offline, no LLM): each candidate is compiled alone with javac against the checkout's
   `cp.test` classpath (exported from a scratch copy of the checkout), and the bug's trigger tests plus a smoke set (the
   developer tests that invoke the focal method, `invoking_test_cases`, located in the test dir) are run on it with a
   direct JUnit runner (`M8Runner.java`, 10 s per test). Validation (`base`): the recompiled unmodified original gives
   the same per-test results as the checkout's own classes (77/78; Lang_12's random tests are flaky), and every trigger
   test fails on the buggy original and passes on the fixed checkout.
4. **Selection / equal budget.** Usable mutant = compiled, bytecode differs from the original's, bytecode not
   identical to an earlier mutant of the same arm. Per method, n = min(usable concept, usable generic, 40); each arm
   keeps its first n usable mutants in the stratified candidate order. So both arms have the **same number of
   mutants per method**.
5. Phase 1 (only if the gate passes; it did): see "Phase 1" below.

## Pre-registered Phase 0 gate (written before any outcome was computed)
Definitions (per bug, over all focal methods of the bug; trigger tests and the fixed version are used here only, for
offline analysis):
- A test's outcome on a mutant = status (PASS / FAIL / ERROR / TIMEOUT) and normalised failure message (exception
  class + message). It is compared with the recompiled original. A test whose message differs between the two
  original runs is compared on status only; a test whose status differs between them is excluded.
- **bug-touching**: ≥1 selected mutant changes ≥1 trigger test's outcome (status or message). A timeout counts as a
  change (sensitivity without timeouts reported).
- **fix-direction**: ≥1 selected mutant makes ≥1 trigger test that fails on the original pass.
- Sets: the selected concept and generic sets (equal n per method, step 4). All usable concept mutants are reported too.

**Rule: go to Phase 1 only if the selected concept mutants are bug-touching on ≥ 30% of the 60 bugs (≥ 18 bugs).**
The concept vs generic difference (bug-touching, fix-direction; per bug and cross-tabulated with
`m2_concept_diag/manual_labels.json`) is reported either way. If the gate fails, the work stops there.

## Phase 1 (arms `m8_concept`, `m8_generic`; same probe, same call budget, differ only in the mutant set)
1. **Probe** (`probe.py gen/check/run`, 1 LLM call per method, shared by both arms). Prompt = the Advanced docstring
   + m6's blind evidence pack (`render_pack`, which includes the declaration); never the body, the fixed version or the
   trigger tests (asserted with m5's `body_leaks` on everything except the inherited Advanced docstring; Lang_36,
   Lang_3, Lang_44 docstrings quote the body, as in the baseline). The LLM writes `static void cases()` with 10-20
   `probe("label", () -> expr)` calls. The harness runs each case in its own thread (5 s) and prints `returns <repr>`
   or `throws <class>: <message>`. A probe that does not compile against the buggy classes (sandbox) is re-asked with
   the compiler errors, at most 3 attempts in total (T=0; T=0.5 only after an unparsable reply, e.g. a repetition loop).
   The probe runs on the original twice (cases whose output differs are dropped as nondeterministic), on every
   selected mutant of both arms, and on the fixed checkout (offline, for the arbiter-accuracy analysis only).
2. **Items** (`arbiter.py items`): (case, original output, mutant output) where a selected mutant differs on a
   deterministic case, timeouts dropped, deduplicated; at most 10 per method and arm (round robin over cases, most
   frequent difference first); A/B order per item from a seeded RNG.
3. **Arbiter** (`arbiter.py ask`, 1 LLM call per method and arm): the same spec as the probe plus the items as
   "Implementation A: P / Implementation B: Q"; answers A, B or UNDETERMINED with a verbatim quote (no evidence counts
   as UNDETERMINED). It never learns which side is the current code. The body-window guard covers the whole prompt except
   the observed outputs: an output can repeat a string literal of the method (an exception message, e.g. Csv_2), which
   any caller observes.
4. **Tests** (`arbiter.py tests`, no LLM): one JUnit test per decided item from a template: the case (with the local
   declarations that precede it in `cases()`, e.g. a shared `HelpFormatter`) inlined as an anonymous `Callable` in the
   test method, then `assertEquals(<chosen repr>, m8repr(result))`, or for an exception `assertEquals(<class>, ...)`
   (plus the message when both sides threw the same class). Compiled in the sandbox with the project's test source
   level; then a **self-check on the buggy code** (a test asserting the original's output must pass, one asserting
   the mutant's must fail); a test that does not reproduce its probe record is dropped (time- or state-dependent
   cases; 9 generic tests: Lang_26 FastDateFormat, Lang_33, Lang_55 StopWatch; 0 concept). Only the buggy code is
   used for this, no oracle.
5. **Evaluation**: `eval_parts.py` (m7's, paths moved here, `NO_ADC=1`), arms `m8_concept` and `m8_generic` = "m8
   tests alone". "Advanced + m8" = the union of each method's Advanced-Doc baseline run and the m8 run (the m8 tests
   are separate test methods, so per-test outcomes add up); computed in `analyze.py`, not re-evaluated.

Changes after the smoke (idx 3, 33, 53), all before the full run and applied to both arms:
- The probe lambdas may use locals declared earlier in `cases()` (Cli_32's `formatter`); items and tests carry that
  prelude. The 6 smoke arbiter calls were redone with the prelude in the item text (first answers in
  `out/discarded/smoke_v1/`, their cost is in the log).
- Test template: the first version used lambdas, which Codec's build rejects (`-source 1.7`); a static helper method
  was rejected by the pipeline, which keeps only `@Test` methods that invoke the focal method themselves
  (`utils/output_analyzer.contains_focal_method_invocation`). Final: the anonymous `Callable` above. The first, aborted
  evaluation of `m8_concept` (lambda template) is in `out/discarded/eval_lambda_template/`.
- Self-check mismatches are dropped (point 4).
- Infrastructure: paths below the `/repo` bind mount are flaky on Docker Desktop (transient ENOENT, and once a
  read-only fallback for the nested `out` mount). `dock8.sh` therefore mounts the checkouts also at `/d4j` and `out`
  also at `/m8out`, and the scripts use those. The first 1085 Phase 0 records, run through the nested mount, were
  rerun (`out/discarded/phase0_runs_nested_mount.jsonl`; identical except 2 timeout-vs-OOM records).

## Security
Everything that compiles or runs mutated or LLM-written code runs through `dock8.sh`: no gcloud credentials (the
`NO_ADC=1` equivalent), `--network none`, repo read-only except `m8_concept_mutants/out`, checkouts read-only, scratch
in the named volume `m8scratch`. LLM calls (Phase 1) run in a separate container through `run/dock.sh` and
`run/gemini_shim.py`.

Spend: every billed response is logged in `out/llm_calls.jsonl` (tokens, USD at 0.30 / 2.50 USD per 1M input / output
tokens); `probe.Chat` refuses to call when the logged spend reaches the 8 USD cap minus 0.25. Calls are sequential;
429s are retried with backoff by `run/gemini_shim.py`. `out/no_adc_inspect.txt`: `docker inspect` of an evaluation
container (no gcloud mount, no credentials variable) and of the sandbox (network none, repo and checkouts read-only).
At the end, `phase0.py checkouts after` is compared with `out/checkouts_before.json` (main sources unmodified).

## Files
- `dock8.sh` sandbox wrapper; `mutate.py` operators (`mutate.py selftest`); `M8Runner.java` JUnit runner;
  `phase0.py` env / base / run / checkouts; `analyze0.py` Phase 0 numbers → `out/phase0_analysis.txt` and
  `out/selection.json`.
- `probe.py` (LLM wrapper with the spend log and cap, probe prompt, harness, runs), `arbiter.py` (items, arbiter,
  tests, completions), `eval_parts.py`, `analyze.py` (Phase 1 numbers → `out/analysis.txt`).
- `out/mutants.jsonl` (per method: candidates with edit, operator, concept), `out/env.json` (classpaths, trigger and
  smoke tests), `out/phase0_base.json`, `out/phase0_runs.jsonl` (per candidate: compiled, bytecode hash, per-test
  outcomes), `out/probe_gen.jsonl` / `probe_check.json` / `probe_runs.jsonl`, `out/items.json`,
  `out/arbiter_<arm>.jsonl`, `out/tests_<arm>.json`, `out/m8_<arm>_parts.json`, `out/llm_calls.jsonl`, consoles,
  `out/discarded/`.
- Written outside this folder (new files only): `data/prompts/rq1/*m8_*`, `data/rq1/logs/*m8_*`,
  `data/rq1/results_test/chatgpt/*m8_*`, `run/out/eval_m8_*`; the docker volume `m8scratch`.

## Reproduce (from `EvalAndMitigate/`)
```bash
docker volume create m8scratch
bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/mutate.py selftest
bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/mutate.py          # out/mutants.jsonl
bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/phase0.py env      # rerun until 60 bugs (transient ENOENT)
bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/phase0.py base
bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/phase0.py checkouts before
M8_WORKERS=7 bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/phase0.py run   # resumable, ~20 min
python3 m8_concept_mutants/analyze0.py > m8_concept_mutants/out/phase0_analysis.txt      # gate; writes out/selection.json
# Phase 1 smoke (idx 3 33 53), then the same steps without indexes for the full run
bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/probe.py prompts           # leak check of the probe prompts
bash run/dock.sh -- python3 m8_concept_mutants/probe.py gen 3 33 53                   # LLM (credentials, no code run)
bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/probe.py check 3 33 53    # compile; repeat gen/check (<=3 attempts)
M8_WORKERS=7 bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/probe.py run 3 33 53
python3 m8_concept_mutants/arbiter.py items
for a in concept generic; do bash run/dock.sh -- python3 m8_concept_mutants/arbiter.py ask $a 3 33 53; done
for a in concept generic; do bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/arbiter.py tests $a 3 33 53; done
for a in concept generic; do python3 m8_concept_mutants/arbiter.py completions $a 3 33 53; done
NO_ADC=1 FILE_POST_FIX=m8_concept_smoke bash run/dock.sh eval_env      # then m8_generic_smoke; never two at once
# full run
for r in 1 2 3; do bash run/dock.sh -- python3 m8_concept_mutants/probe.py gen; bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/probe.py check; done
M8_WORKERS=7 bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/probe.py run
python3 m8_concept_mutants/arbiter.py items
for a in concept generic; do bash run/dock.sh -- python3 m8_concept_mutants/arbiter.py ask $a; done
for a in concept generic; do bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/arbiter.py tests $a; python3 m8_concept_mutants/arbiter.py completions $a; done
python3 m8_concept_mutants/eval_parts.py m8_concept && python3 m8_concept_mutants/eval_parts.py m8_generic   # NO_ADC=1 inside
bash m8_concept_mutants/dock8.sh python3 m8_concept_mutants/phase0.py checkouts after
python3 m8_concept_mutants/analyze.py > m8_concept_mutants/out/analysis.txt
```
