# A fault-relevant concept layer for TrickCatcher's full pipeline

## Summary

This extends [TrickCatcher](https://aclanthology.org/2025.acl-long.20/) (ACL 2025) itself, not just its direct-input prompt. The prior pilot (`trickcatcher_pilot/`) only ran a *direct-input prompt ablation* and injected ConceptCoder's static tree-sitter syntax labels (`null_check`, `buffer_access`, ...); it found no gain (7/26 vs 7/26 on TrickyBugs C++) because those labels carry no information an LLM cannot already read from the source. This report implements the **full three-stage TrickCatcher pipeline** -- PUT-guided program variant generation, generator-based input generation, and diversity-driven differential testing -- reusing the paper's own released prompts and dataset, and adds a concept layer designed to be **fault-relevant** rather than syntactic: enumerated input-constraint rules, a selected validator, PUT-specific fault hypotheses that steer both variant repair and input generation, and independent re-execution of every reported exposure.

Code: `trickcatcher_concept/` (new package). Tests: `tests/test_trickcatcher_concept.py` (all passing; see Testing section).

## Paper and artifact provenance

- Target paper: Liu et al., *LLM-Powered Test Case Generation for Detecting Bugs in Plausible Programs*, ACL 2025. <https://aclanthology.org/2025.acl-long.20/>
- Released artifact: <https://github.com/RinCloud/TrickCatcher>, pinned at commit `a0d285a77efff7c93fc280d606497d9de5e1defe` (`trickcatcher_concept/provenance.py::ARTIFACT_COMMIT`, same commit the prior pilot used).
- Prompts reused **byte-for-byte** from the artifact, verified by SHA-256 before every run (`provenance.py::read_template`):
  - `Datasets/TrickyBugs/PromptTemplates/genprog_tc` (PUT-guided variant generation, the paper's Figure 3) -- SHA-256 `f61bcecb70f7ec8f5c0e7e63799d749406af93759e07bcd7a6abc7f1a7a9f15c`.
  - `Datasets/TrickyBugs/PromptTemplates/geninput_generator` (generator-based input generation, Figure 4) -- SHA-256 `57e1da60da6f2ac745519f735317ffc62ad379cb1b7c4a30d883b573928c8a0a`.
  - The concept arm's fault hypothesis is appended **after** the paper's own repair instruction in `genprog_tc`, and the concept arm's rules/hypotheses block is appended **after** the paper's own generator instruction in `geninput_generator`; the baseline arm uses both templates completely unmodified (`prompt_lineage: "verbatim_original"` vs `"paper_prompt+hypothesis"` / `"planned_extension"` recorded per call).
  - Oracle construction (diversity-driven differential testing, Algorithm 1) and the recall/precision/F1 formulas are ported from the artifact's own `Analysis/utils.py` (`get_trigger_df` + `compute_res_df(method_type='tc')`) into `trickcatcher_concept/oracle.py`, not reimplemented from the paper text alone.
- Dataset: TrickyBugs (Liu et al., MSR 2024), obtained as `/tmp/TrickyBugs.zip` (the published Zenodo v2 release, MD5-verified in the prior pilot) plus the artifact's own `Datasets/TrickyBugs/PUT_cpp` and `PUT_python`. The task list (`trickcatcher_concept/tasks.json`) is every PUT whose pid appears in the artifact's own result files (`Data/chat_res.pkl`, `Data/tc_suball.pkl` for C++; `Data/chat_res_py.pkl`, `Data/tc_trigger_py.pkl` for Python) -- i.e. exactly the PUTs the paper's own analysis notebook scored, not a fresh re-selection. This yields 250 C++ and 115 Python PUTs (the paper reports 251/115; our C++ derivation from the released result files is 1 short of the paper's stated count, plausibly a PUT that appears in the paper's raw generation logs but not in the analysis-ready `.pkl` files the artifact ships).

## What was reused vs. added

| Component | Source |
| --- | --- |
| Variant-generation prompt (`genprog_tc`) | TrickCatcher artifact, verbatim |
| Input-generator prompt (`geninput_generator`) | TrickCatcher artifact, verbatim |
| Variant filtering by existing tests | TrickCatcher paper Sec. 4.1, reimplemented |
| Diversity-driven oracle + P/R/F1 | TrickCatcher artifact `Analysis/utils.py`, ported |
| Gemini/Vertex client | `magma/llm_client.py` (existing repo code), reused unchanged |
| Paired statistics | Same exact-McNemar approach as `trickcatcher_pilot/paired.py` |
| Enumerated constraint rules | New (justified by Specification Grounding, #126) |
| Selected validator | New (justified by AutoCode #125 / CodeHacker #124) |
| PUT-specific fault hypotheses | New (justified by CodeHacker #124 / KITE #123) |
| Independent re-execution ("verify") | New (justified by AnyPoC #129) |

## Method

### Baseline arm

Unmodified TrickCatcher: for a PUT, 10 calls to `genprog_tc` (temperature 1.0) produce candidate variants; each variant is compiled/run and kept only if it reproduces every one of the PUT's own existing tests (paper Sec. 4.1, "Filtered"). One call to `geninput_generator` produces a Python input generator (using `cyaron`, the artifact's own suggested library), executed to emit up to 100 inputs; if fewer than 10 inputs are produced or parse, up to 2 more generator calls are attempted (`MAX_GENERATOR_ATTEMPTS`). The PUT and every kept variant run on every generated input; the diversity-driven oracle (`oracle.py`, Algorithm 1) selects, for each input where the PUT disagrees with some variant subset, the most-frequent disagreeing output as the test oracle -- the paper's key departure from majority voting.

### Concept arm

Before the paper's own two generation prompts, one call produces a **card**: atomic enumerated input-constraint rules (`C1`, `C2`, ...) and 3-5 PUT-specific fault hypotheses (`H1`, ...), each grounded in a quoted code excerpt, naming the mechanism, the violated specification property, a trigger condition on a *valid* input, and the required oracle behavior (`prompts.py::CARD_PROMPT`). Two more calls produce three candidate Python validators and a set of LLM-written near-valid illegal/boundary-valid cases (`prompts.py::VALIDATOR_PROMPT` / `CASES_PROMPT`); the validator that accepts every one of the PUT's own known-valid tests and scores best on the labelled cases *and* on mechanical truncation negatives (empty input, and the PUT's own valid inputs with the last line or last token dropped -- the exact shape of the prior pilot's false win) is selected (`validator.py::select_validator`). The card's hypotheses are then: (a) appended to `genprog_tc` for a rotating share of the 10 variant calls (`--steer-fraction`, default 100%), asking the model to check the specific hypothesis in addition to any other bug it finds; (b) appended to `geninput_generator`, asking the generator to devote part of its 100 inputs to each hypothesis's trigger condition while still respecting every enumerated rule. Every generated input is filtered through the selected validator before being run at all. After oracle scoring, every discrepancy between the PUT and a variant is independently re-executed from scratch (fresh process, fresh compiled binaries) and only discrepancies whose PUT output *and* whose supporting variant output both reproduce count toward "verified" exposure (`pipeline.py::ArmRunner.verify`, AnyPoC-style).

### Evaluation validator (independent of both arms)

To avoid the earlier pilot's mistake -- treating reference-program agreement alone as proof of input validity -- every generated input is additionally checked by a **separately built** evaluation validator: a different model (`gemini-3.1-pro-preview` vs. the generation model `gemini-3-flash-preview`), no concept card, built once per PUT from the same AutoCode-style candidate/case/negative selection process but never shown to either arm's generator. `strict` validity requires both this evaluation validator's acceptance *and* agreement of all (up to 5) TrickyBugs reference programs; `refs` validity requires only reference agreement, reported alongside `strict` to show how much the earlier pilot's flaw (reference agreement without constraint checking) would have overstated exposure.

### Exclusions

TrickyBugs PUTs are "plausible": they are claimed to pass their own existing/original test suite. Recompiling and re-running all 365 PUTs (250 C++ retained after task-index derivation, 115 Python) under our toolchain (`g++` 16.2.1, `-std=gnu++17 -O2 -DONLINE_JUDGE`, Python 3.8 runtime, ASLR disabled -- see below) found 40 PUTs (29 C++, 11 Python) that do not reproduce at least one of their own existing tests, or do not compile at all. These are recorded, with the exact pass/fail counts, in `trickcatcher_concept/exclusions.json` and excluded from every arm; they are never silently scored against ground truth the harness itself cannot reproduce. The final task set is **221 C++ and 104 Python PUTs (325 total)**.

Manual inspection of a sample (`p03076`, `p02585`) showed the two dominant causes are (a) genuine undefined behavior in the buggy program itself -- e.g. an uninitialized local array whose zero-vs-garbage contents depend on stack layout, which is often *part of the tricky bug the dataset is about* -- and (b) toolchain drift from the README's recommended GCC 9.2.1/Clang 10.0.0 to the GCC 16.2.1 available here (a newer default `-std`, stricter `_FORTIFY_SOURCE`/`_GLIBCXX_ASSERTIONS`, both of which we explicitly disable to match likely original-judge compilation). Disabling ASLR (`personality(ADDR_NO_RANDOMIZE)`) measurably reduced the excluded count (e.g. one Python PUT went from 26/42 to 37/42 passing existing tests), confirming that some of the remainder is address-layout-dependent UB rather than a hard toolchain incompatibility -- but it does not eliminate it, and it cannot reproduce the *original* online judge's memory layout either way. This 11% exclusion rate is reported as a limitation, not hidden.

## Infrastructure notes worth recording

- **gRPC + fork() hazard**: the pipeline runs LLM calls (gRPC/Vertex) and PUT/variant execution (subprocess) concurrently in the same multi-threaded process. `subprocess`'s `preexec_fn` (used for `setrlimit`/ASLR/`setsid`) forces CPython to `fork()` the whole interpreter for every single execution; forking while another thread is inside a gRPC call corrupted gRPC's c-ares resolver and aborted worker processes with a fatal `Check failed: channel_ != nullptr` during a live run. Fixed by wrapping the child command with `setarch <arch> -R` (ASLR) and `prlimit --as=... --fsize=... --core=0 --stack=...` (resource limits) plus `subprocess`'s `start_new_session=True`, so CPython never needs `preexec_fn` and uses its safer `vfork()`-based path (`sandbox.py`). Verified with a fresh 325-task `put_existing_check` (0 failures, matching `exclusions.json` exactly) and a subsequent concurrent run with no further crashes.
- **LLM call watchdog**: a small number of Vertex calls were observed to hang far past the client's own 180s timeout; `llm.py` now runs every call on a dedicated watchdog pool with a 240s hard deadline so one stuck call cannot starve the shared concurrency budget.
- **Requests-per-minute quota, not just concurrency**: an early run at `--llm-concurrency 10` (and later even at `4`) spent most of its wall-clock time in exponential-backoff retries against `ResourceExhausted: 429` -- a live check of one 221-call sample found only 100 calls (45%) succeeded on the first attempt. Lowering concurrency alone did not fix it, because the limit is a rate (requests/minute), not a concurrency cap: many threads each completing a fast call and immediately starting another can exceed a QPM quota even with few calls in flight at once. Fixed by adding an explicit token-bucket pacer (`LLM._throttle`, `--llm-min-interval`) that spaces the *start* of successive calls per `LLM` instance regardless of how many threads are waiting. At `--llm-concurrency 3 --llm-min-interval 5.0` (per-instance ≤12 requests/minute, two instances -- generation and evaluation -- so ≤24/minute combined) essentially all retries switched from `429` to the ordinary occasional `500 Internal error`, and task throughput increased accordingly. All failed attempts (not just the final successful call) are now logged to `<run-dir>/llm_cache/_retries.jsonl` for auditing.
- **Resume safety**: every pipeline stage (card, validator, variants, inputs, outputs, verify) and every LLM call is persisted as its own JSON file keyed by task/arm/stage; a killed and restarted run skips everything already on disk. `run.py --score-only` re-scores from existing stage output without any further LLM calls.

## Protocol

1. Reproduce the paper's own metric machinery on the paper's own dataset with Gemini 3 Flash (native Vertex, `gemini-3-flash-preview`, via `magma/llm_client.py`, `source scripts/vertex_env.sh`) as the baseline arm, using TrickCatcher's unmodified prompts.
2. Add the concept layer (concept arm) with the same generation model and the same number of program-variant/input-generation calls per PUT (plus the concept-specific card/validator calls, counted separately in cost accounting).
3. Compare recall/precision/F1 (paper's own formulas, `k = 10` matching the paper's best-F1 row for TrickCatcher) and paired per-task exposure (exact McNemar, ties excluded) on:
   - a fixed seeded ~75-task tuning subset (50 C++ + 25 Python, `data.py::seeded_subset`, seed `20260926`, drawn before any model call);
   - the full 325-task set (221 C++ + 104 Python) once the subset run is validated.
4. Report `strict` input-validity rates (evaluation-validator acceptance among *usable*, validator-filtered inputs) for both arms, and the `refs`-only comparison to show the gap the earlier pilot missed.

EvalPlus (AI-generated buggy programs, the paper's third dataset) is **not** run under the new full pipeline in this report; it remains covered only by the prior pilot's direct-input ablation (`trickcatcher_pilot/`). Extending the full three-stage pipeline to EvalPlus is listed as an open item below.

## Results

<!-- FILLED IN AFTER THE RUNS COMPLETE. See the accompanying JSON in research/results/ for exact per-k tables. -->

### Seeded subset (~75 PUTs)

_[to be filled in]_

### Full dataset (325 PUTs)

_[to be filled in]_

### Validity

_[to be filled in]_

### Cost

_[to be filled in]_

## Testing

`tests/test_trickcatcher_concept.py` (unit-level, no network): the diversity-driven oracle (disagreement voting over majority voting, tie handling, error-output exclusion, the paper's exact recall/precision/F1 aggregation formula), prompt construction (concept prompts keep the verbatim paper prompt as a strict prefix; card prompts do not mangle braces already present in the PUT's own C++ source), parsing (validator/case extraction, mechanical negative construction, lenient generator-output shapes), the resume-safe LLM cache (no duplicate calls, token accounting recorded), report aggregation (paired exposure counts, McNemar, validity rates, cost summation), and the sandbox fix itself (an over-`RLIMIT_AS` allocation is still rejected without `preexec_fn`; the module contains no `preexec_fn` call). All tests pass (`.venv/bin/python -m pytest tests/`).

A single-PUT smoke run with real Gemini calls (`p03076`, both arms) additionally validated the whole pipeline end to end: the concept card correctly identified the PUT's actual fault condition (an `if (a % 10 && ...)` guard that never fires when every input is a multiple of 10) and the generator targeted it explicitly, but the independent oracle correctly reported **no** exposure for that specific case because the PUT's arithmetic happens to cancel out and produce the right answer anyway on that input shape -- i.e. the harness does not rubber-stamp the concept card's own hypotheses, only genuinely observed disagreements.

## Limitations and open issues

- The task list is 250 C++ / 115 Python before exclusions vs. the paper's reported 251/115; the 1-PUT C++ discrepancy traces to the artifact's own released `.pkl` result files rather than to our selection code (see Provenance).
- 40/365 PUTs (11%) are excluded because they do not reproduce their own existing tests under our toolchain; this is disclosed, not hidden, but it means the reported metrics are conditioned on toolchain-reproducible PUTs, which the paper's own environment (GCC 9.2.1) may not have needed to exclude.
- ASLR-disabling and ONLINE_JUDGE/`_FORTIFY_SOURCE` compile-flag choices are principled (they intentionally undo debug/local-only code paths and reduce address-layout non-determinism) but still cannot reproduce the *original* online judge's exact runtime.
- EvalPlus is not covered by the new full-pipeline package in this report.
- [Further items to be added once the full run's results and any additional failure modes are known.]
