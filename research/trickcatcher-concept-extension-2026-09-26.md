# A fault-relevant concept layer for TrickCatcher's full pipeline

## Summary

This extends [TrickCatcher](https://aclanthology.org/2025.acl-long.20/) (ACL 2025) itself, not just its direct-input prompt. The prior pilot (`trickcatcher_pilot/`) only ran a *direct-input prompt ablation* and injected ConceptCoder's static tree-sitter syntax labels (`null_check`, `buffer_access`, ...); it found no gain (7/26 vs 7/26 on TrickyBugs C++) because those labels carry no information an LLM cannot already read from the source. This report implements the **full three-stage TrickCatcher pipeline** -- PUT-guided program variant generation, generator-based input generation, and diversity-driven differential testing -- reusing the paper's own released prompts and dataset, and adds a concept layer designed to be **fault-relevant** rather than syntactic: enumerated input-constraint rules, a selected validator, PUT-specific fault hypotheses that steer both variant repair and input generation, and independent re-execution of every reported exposure.

**Status honestly up front**: the pipeline is fully implemented, unit-tested, and validated end-to-end with real Gemini calls (a single-PUT smoke run plus an 11-task slice of the seeded subset). It is **not yet statistically conclusive** -- this Vertex project's requests-per-minute quota for the preview model turned out to be the binding constraint on wall-clock progress, not the pipeline or the paper's own generation budget, and only 11 of the planned 75 seeded-subset tasks had completed by report time. The run continues in the background and is resume-safe; see "Resuming and extending" for how to continue it and regenerate this report's numbers.

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
- **Requests-per-minute quota, not just concurrency**: an early run at `--llm-concurrency 10` (and later even at `4`) spent most of its wall-clock time in exponential-backoff retries against `ResourceExhausted: 429` -- a live check of one 221-call sample found only 100 calls (45%) succeeded on the first attempt. Lowering concurrency alone did not fix it, because the limit is a rate (requests/minute), not a concurrency cap: many threads each completing a fast call and immediately starting another can exceed a QPM quota even with few calls in flight at once. Mitigated (not eliminated) by adding an explicit token-bucket pacer (`LLM._throttle`, `--llm-min-interval`) that spaces the *start* of successive calls per `LLM` instance regardless of how many threads are waiting. At `--llm-concurrency 3 --llm-min-interval 5.0` a short check showed retries shifting mostly from `429` to ordinary occasional `500 Internal error`, but sustained operation at that setting still produced clusters of `429`s; raising to `--llm-min-interval 8.0` reduced but did not eliminate them either (a later check found 429 still the majority cause of retries). This session could not determine the project's actual quota ceiling; it is plausibly a very low default for this preview model. All failed attempts (not just the final successful call) are now logged to `<run-dir>/llm_cache/_retries.jsonl` for auditing.
- **The ceiling is a small, fixed per-project quota for `gemini-3-flash-preview`, not (mainly) contention from other agents.** During the full 325-task run (2026-09-27), three other jobs sharing this Vertex project's quota (STRUT, TestCase-Eval, KITE) were reported finished, and it was hypothesized this would free up substantial headroom. `_retries.jsonl` confirmed zero 429s for a sustained ~2-hour window at `--llm-concurrency 1 --llm-min-interval 20.0` (an effective dispatch rate of ~3 calls/minute for the generation client -- note that `_throttle` paces the *dispatch rate* globally per `LLM` instance regardless of `--llm-concurrency`, which only lets multiple in-flight requests overlap without blocking the schedule; concurrency does not multiply throughput on its own). Raising to `--llm-min-interval 10.0` (~6/min) reproduced the same heavy, sustained 429 pattern seen earlier; raising further to `--llm-min-interval 3.0` (~20/min, tried once other jobs' completion made more headroom seem plausible) produced an immediate, dense 429 flood on nearly every fresh call within seconds. This pins the real ceiling for this preview model in this project at something close to 3-4 requests/minute regardless of what else is running -- other agents' load was not the dominant factor after all, or the project's default preview-model quota is simply this low on its own. `--llm-min-interval 20.0` is the setting this report now treats as the safe operating point for `gemini-3-flash-preview`; do not assume other jobs finishing frees meaningful headroom without re-testing via a short, closely-watched bump and an immediate revert on any 429 in `_retries.jsonl`.
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

**Status at report time: the 75-task seeded subset is complete (50 C++ + 25 Python, 0 errors on the final resumed pass); the full 325-task run has now been launched against the same run directory (see "Full dataset" below).** Exact per-task, per-k numbers for the finished subset are archived in [`research/results/trickcatcher-concept-subset-interim/`](results/trickcatcher-concept-subset-interim) (`results_75of75_final.jsonl`, `report_75of75_final.json`, `bootstrap_75of75_final.json`; earlier `results_11of75.jsonl`/`results_27of75.jsonl` snapshots kept for the progression record); regenerate the summary at any time with:

```bash
.venv/bin/python -m trickcatcher_concept.report --results /home/phong/dev/trickcatcher-concept-data/runs/subset-v1/results.jsonl
```

### Why progress was slow: a Vertex requests-per-minute wall shared with other concurrent work, not a pipeline problem

Real wall-clock progress on this Vertex project has been dominated by `ResourceExhausted` (429) responses for `gemini-3-flash-preview`, which this session could not fully characterize (no access to the project's quota console), and which got *worse* once other unrelated agents in this same repo/project (`testcase_eval`, `strut_concept`) began running concurrently against the same Vertex project quota. Concretely:

- At `--llm-concurrency 10` (no pacing), an early sample showed only 100/221 calls (45%) succeeding on the first attempt.
- Reducing concurrency alone (`4`) did not help -- confirming a requests-per-minute limit, not a concurrency limit.
- Adding explicit inter-call pacing (`--llm-min-interval`, see Infrastructure notes) reduced but did not eliminate 429s even down to an aggregate ~7.5 requests/minute across both model clients combined.
- On resuming this run in a later session, `--llm-concurrency 2 --llm-min-interval 12.0` still produced near-100% 429 rates on fresh (non-cached) calls because several other agents were simultaneously issuing unpaced requests against the same project; dropping to `--llm-concurrency 1 --llm-min-interval 20.0` (i.e. this run alone contributing at most ~3 requests/minute) reduced the failure rate enough to make steady, if slow, forward progress (roughly 1 task per 5-10 minutes of wall-clock time once past the already-cached prefix).

This means the *pipeline* is not the bottleneck -- it is fully implemented, tested, and (per the smoke run and this 27-task sample) producing sane, mechanistically explicable results -- but *this specific Vertex project's default quota for a preview model*, shared across multiple concurrent agents' workloads, limits how fast either arm's calls can land. This is disclosed rather than worked around by, e.g., silently shrinking the paper's own generation budget (10 variants, 100 inputs) to fit the quota.

An unrelated operational note from this resume: the previous run's process had been killed externally, but 14 of its sandboxed exec/generator child processes (`_bin/*.bin`, one Python `generator.py`) had been orphaned (reparented to the user's systemd, still consuming a full CPU core each) rather than cleaned up, apparently because their parent was killed before it could reap them; they were spinning uselessly for hours with no supervisor left to read their output. These were killed manually before restarting; a future hardening item is to have `sandbox.py`/`pipeline.py` place child processes in a killable process group so an interrupted run cannot leak them.

### Seeded subset, final (75 of 75 PUTs: 50 C++ + 25 Python)

Best-F1 row (`k = 10`, matching the paper's own best-k for TrickCatcher on TrickyBugs), `strict` validity (independent evaluation validator + reference agreement both required). Reported per language (the paper's own convention, since C++/Python are disjoint PUT sets) and pooled overall (this report's own additional statistic, not a paper convention):

| Split | Arm | Recall | Precision | F1 | Tasks exposed |
| --- | --- | ---: | ---: | ---: | ---: |
| C++ (n=50) | Baseline | 48.5% | 86.6% | 62.2% | 25/50 |
| C++ (n=50) | Concept | 47.8% | **91.8%** | **62.8%** | 25/50 |
| Python (n=25) | Baseline | 67.5% | 76.7% | 71.8% | 17/25 |
| Python (n=25) | Concept | **73.0%** | **79.3%** | **76.0%** | 19/25 |
| Overall pooled (n=75) | Baseline | 54.8% | 82.3% | 65.8% | 42/75 |
| Overall pooled (n=75) | Concept | **56.2%** | **86.0%** | **67.9%** | 44/75 |

Paired per-task exposure (overall, n = 75): 38 tasks exposed by both arms, 4 baseline-only (`cpp/p02581`, `cpp/p03089`, `cpp/p03561`, `python/p02992`), 6 concept-only (`cpp/p02599`, `cpp/p02900`, `cpp/p02938`, `python/p02900`, `python/p03452`, `python/p04012`), exact McNemar p = 0.754 (per-language: C++ p = 1.0 with 3 vs. 3 splits; Python p = 0.625 with 1 vs. 3). **Not statistically significant at this sample size.** A paired bootstrap (5000 resamples of tasks, with replacement, recomputing both arms' recall/precision/F1 on each resample; seed `20260926`, script and full output in `bootstrap_75of75_final.json`) gives 95% CIs for the concept-minus-baseline difference, overall pooled: recall +1.3 pp [-6.0, +8.5], precision +3.7 pp [-0.1, +9.1], F1 +2.1 pp [-4.3, +8.6] -- every interval still spans zero, though the precision interval is the closest to excluding it (lower bound -0.1 pp).

**Honest reading**: across every checkpoint taken during this run (n=11, n=27, n=75), the concept arm has led baseline on precision, F1, and task-exposure count every single time, and on recall in 2 of 3 (Python consistently, C++ essentially tied). That consistency of direction is suggestive, but no single checkpoint's paired test reaches conventional significance, and the checkpoints are not independent samples (n=75 is a superset of n=27 which is a superset of n=11), so this is one trend observation, not three corroborating ones. The full 325-task run (below) is needed for a claim stronger than "consistent favorable direction, not yet significant."

### Validity, final (n = 75)

| Arm | Generated | Usable (validator-filtered) | Independent-validator-invalid rate (of usable) | Reference-invalid rate (of usable) |
| --- | ---: | ---: | ---: | ---: |
| Baseline (no concept validator) | 7106 | 7106 (unfiltered) | 14.55% | 5.01% |
| Concept (own validator applied) | 6361 | 6257 | 14.58% | **2.86%** |

This is the most consistent finding across every sample size checked (n=11: 0.0% vs 9.5%; n=27: 1.6% vs 7.8%; n=75: 2.86% vs 5.01%): the concept arm's own AutoCode-style validator keeps letting through noticeably fewer reference-disagreeing inputs than baseline's unfiltered generator output, even as the gap narrows somewhat with more tasks (partly because the n=11/27 samples were all-C++, and C++'s gap, 1.2% vs 4.4% at n=50, is smaller than the early all-C++ samples suggested, while Python's gap is essentially zero, 6.5% vs 6.4% at n=25 -- the concept validator's advantage is concentrated in C++). The *independent* evaluation-validator invalid rate stays essentially tied between arms at every sample size (14.58% vs 14.55% overall) -- the concept arm's validator and the independently-built evaluation validator are not simply agreeing with each other more; the concept arm specifically wins on reference-agreement validity, not on the independent evaluator's separate criterion.

### Cost, final (75 tasks, both arms, plus their evaluation-validator calls)

1980 LLM calls, 1,933,161 input tokens, 1,271,901 output tokens across `gemini-3-flash-preview` (1830 calls, generation) and `gemini-3.1-pro-preview` (150 calls, independent evaluation validator); this aggregate is in `report_75of75_final.json`. The full per-call records (prompt, response, token usage, latency, cache hit) live in `<run-dir>/llm_cache/` and are kept outside git (per instructions) since that directory grows large over a full run.

### Full dataset (325 PUTs)

Launched after the subset finished cleanly (0 errors), reusing the same run directory (`/home/phong/dev/trickcatcher-concept-data/runs/subset-v1`, `--split full`); it skips the 75 subset tasks already scored (their stage files and LLM cache entries are reused unchanged) and processes only the remaining ~250 PUTs. See "Resuming and extending" for the exact command and current pacing. Given the subset's consistent-but-not-yet-significant direction, the full run is worth the wall-clock cost: it is the only way to either confirm the trend at a power the 75-task subset lacks, or reveal that it washes out. Results will be added to this report once a meaningful fraction has completed; see the run's live `results.jsonl` and `trickcatcher_concept.report` in the meantime.

## Resuming and extending

The subset run (`/home/phong/dev/trickcatcher-concept-data/runs/subset-v1`, PID varies per restart, logs at `/tmp/trickcatcher_subset_run.log` as of the most recent resume) is resume-safe: every LLM call and every pipeline stage is cached as its own file, so killing and rerunning the identical command only fills in what is missing. **Note (2026-09-26, second resume): when other agents in this repo are concurrently issuing unpaced Vertex calls against the same project, `--llm-concurrency 3 --llm-min-interval 8.0` was no longer conservative enough (near-100% 429 rate on fresh calls); `--llm-concurrency 1 --llm-min-interval 20.0` was needed to make steady forward progress.** Check `<run-dir>/llm_cache/_retries.jsonl`'s tail for the current error mix before picking concurrency -- if it's still almost all `ResourceExhausted` at `concurrency=1`, the bottleneck is other processes' load on the shared project quota, not this run's own settings, and there is no further knob here to turn besides waiting or getting a quota increase.

```bash
source /home/phong/dev/ConceptTester/scripts/vertex_env.sh
cd /home/phong/dev/ConceptTester   # or this worktree
.venv/bin/python -m trickcatcher_concept.run --split subset --arms baseline,concept \
    --run-dir /home/phong/dev/trickcatcher-concept-data/runs/subset-v1 \
    --task-workers 2 --llm-concurrency 1 --llm-min-interval 20.0 --procs 6
```

(If the Vertex project is not under contention from other concurrent agents, the earlier, faster settings -- `--task-workers 6 --llm-concurrency 3 --llm-min-interval 8.0 --procs 16` -- can be tried first and only backed off if `_retries.jsonl` shows sustained 429s. As of 2026-09-27, however, this did **not** hold -- see the quota-ceiling infrastructure note above: even after the other three agents sharing this project's quota finished, `--llm-min-interval 10.0` still reproduced sustained 429s and `3.0` flooded immediately. Treat `20.0` as the safe default and only test faster settings briefly, watching `_retries.jsonl` in real time.)

The subset is done; the run now in progress is the full 325-task set, launched by pointing `--split full` at the **same** run directory (it skips the 75 subset tasks already scored, resuming from their cached stage files, and processes the remaining ~250). `--task-workers` and `--procs` can be set much higher than `--llm-concurrency` without affecting Vertex request rate -- they only control how many tasks/local subprocess executions run concurrently and let already-cached tasks replay in parallel while a few genuinely-new tasks are paced through the shared LLM throttle; raising `--task-workers` was necessary in practice because the "full" split's task order interleaves cached and new tasks (unlike "subset", "full" is `task_index()`'s natural order, not the seeded-subset's order), so a low `--task-workers` could leave cached, instant-replay tasks queued behind a couple of slow new ones. The command actually running as of this report:

```bash
.venv/bin/python -m trickcatcher_concept.run --split full --arms baseline,concept \
    --run-dir /home/phong/dev/trickcatcher-concept-data/runs/subset-v1 \
    --task-workers 12 --llm-concurrency 3 --llm-min-interval 20.0 --procs 12
```

If the actual Vertex quota turns out to be higher than empirically found here (e.g. after an explicit quota increase -- other agents' workloads finishing was tested and did **not** raise the effective ceiling, see above), lower `--llm-min-interval` cautiously (test a smaller step than 20.0 -> 3.0) and watch `<run-dir>/llm_cache/_retries.jsonl` in real time for the error mix (`ResourceExhausted` should disappear first; occasional `InternalServerError`/`DeadlineExceeded` are normal and already retried) -- revert immediately on any 429 rather than waiting to see if it's transient, since every tested value between the known-safe and known-unsafe points has so far turned out unsafe, not intermediate. Before restarting after any external kill, always check `pgrep -f <run-dir>` for orphaned sandbox/generator child processes (see the operational note in Results) and kill them first -- this run's own resumes have left such orphans twice now.

Re-run `trickcatcher_concept.report` at any time against the growing `results.jsonl` to get updated recall/precision/F1, paired McNemar, validity and cost numbers without any further model calls.

## Testing

`tests/test_trickcatcher_concept.py` (unit-level, no network): the diversity-driven oracle (disagreement voting over majority voting, tie handling, error-output exclusion, the paper's exact recall/precision/F1 aggregation formula), prompt construction (concept prompts keep the verbatim paper prompt as a strict prefix; card prompts do not mangle braces already present in the PUT's own C++ source), parsing (validator/case extraction, mechanical negative construction, lenient generator-output shapes), the resume-safe LLM cache (no duplicate calls, token accounting recorded), report aggregation (paired exposure counts, McNemar, validity rates, cost summation), and the sandbox fix itself (an over-`RLIMIT_AS` allocation is still rejected without `preexec_fn`; the module contains no `preexec_fn` call). All tests pass (`.venv/bin/python -m pytest tests/`).

A single-PUT smoke run with real Gemini calls (`p03076`, both arms) additionally validated the whole pipeline end to end: the concept card correctly identified the PUT's actual fault condition (an `if (a % 10 && ...)` guard that never fires when every input is a multiple of 10) and the generator targeted it explicitly, but the independent oracle correctly reported **no** exposure for that specific case because the PUT's arithmetic happens to cancel out and produce the right answer anyway on that input shape -- i.e. the harness does not rubber-stamp the concept card's own hypotheses, only genuinely observed disagreements.

## Limitations and open issues

- **Not yet statistically conclusive.** The full 75-task seeded subset (50 C++ + 25 Python) is now complete; the paired McNemar test at n = 75 (p = 0.754 overall) is not significant, and the paired bootstrap 95% CIs for every metric (recall, precision, F1) span zero. The concept arm has nonetheless led baseline on precision, F1, and exposure count at every checkpoint taken during this run (n = 11, 27, 75) and on recall in 2 of 3 language splits -- a consistent direction, not yet a significant effect. The full 325-task run is in progress (see "Full dataset" above); the honest conclusion of this report remains "the full pipeline and concept layer are implemented, tested, and behaving as designed, with a consistent favorable trend that has not yet reached significance" rather than a confirmed claim that the concept layer improves TrickCatcher's recall/precision/F1 -- that needs the full-dataset numbers.
- **Vertex quota, not compute, is now the critical path.** This session could not determine or raise the project's actual requests-per-minute ceiling for `gemini-3-flash-preview`; empirically, pacing down to ~7.5 combined requests/minute across both model clients reduced but did not eliminate `ResourceExhausted` responses. Whoever continues this run should check the Vertex AI quota console for `gemini-3-flash-preview` / `gemini-3.1-pro-preview` in the configured project and consider requesting a quota increase before the full 325-task run, which at the current rate would take on the order of a day of wall-clock time.
- The task list is 250 C++ / 115 Python before exclusions vs. the paper's reported 251/115; the 1-PUT C++ discrepancy traces to the artifact's own released `.pkl` result files rather than to our selection code (see Provenance).
- 40/365 PUTs (11%) are excluded because they do not reproduce their own existing tests under our toolchain; this is disclosed, not hidden, but it means the reported metrics are conditioned on toolchain-reproducible PUTs, which the paper's own environment (GCC 9.2.1) may not have needed to exclude.
- ASLR-disabling and ONLINE_JUDGE/`_FORTIFY_SOURCE` compile-flag choices are principled (they intentionally undo debug/local-only code paths and reduce address-layout non-determinism) but still cannot reproduce the *original* online judge's exact runtime.
- EvalPlus is not covered by the new full-pipeline package in this report; only the prior pilot's direct-input ablation covers it.
- The concept card's fault hypotheses are exactly that -- hypotheses. The `p03076` smoke-test example in Testing shows the harness correctly declining to count a plausible-sounding but ultimately incorrect hypothesis as an exposure; this is evidence the oracle is not rubber-stamping the concept arm, but it also means a task-level win is not guaranteed just because the model produced a well-reasoned card.
- `--steer-fraction` (share of the 10 variant calls that receive a hypothesis), the number of card hypotheses (3-5), and generation temperature (1.0, matching the paper) were set from first principles and the batch-07 paper guidance, not swept on the subset, due to the quota constraint above; a real hyperparameter sweep is future work.
