# Handoff (2026-10-07): state of all running work, for a Claude session on `thinkbook`

Repo: this one (`~/dev/ConceptTester` on thinkbook). Read `AGENTS.md` first. Its rules:
- no Co-Authored-By;
- push to main;
- don't edit vendored paper code;
- arm64/x86, no emulation;
- one folder per paper;
- keys via `scripts/*_env.sh`, never printed.

User preferences:
- Talks in Vietnamese.
- Vertex AI spend is fine (log cost).
- **Always take a 2025-26 paper with a public artifact as the base method and improve it.** Don't design standalone studies.
- The thesis topic is **LLM test-case generation**.

## Big picture (what has been learned)
- Replication of EvalAndMitigate (ISSTA'26) plus methods m1-m10 and a 146-method subset are all in `EvalAndMitigate/`
  (`RESULTS.md`, `subset150/`, `m*/RESULTS.md`). Concepts (C1-C8 bug-category facts) never beat a length-matched
  placebo when the LLM must **guess the test oracle**, and as an oracle they copy the bug.
- m9 (concept checklist in the Advanced prompt) showed concepts steer **attention** to the bug's category
  (strict count 44% vs 17%, p=7e-7; RESULTS.md reports the loose count 69% vs 44%). But they don't improve the
  fix or the tests.
- Single runs are noisy: an A/A re-run flips about 18/135 methods. Use K≥3 samples or paired designs.
- Current direction: concepts may help **where to look / which inputs**, not oracles.

## Running now (as of 2026-10-07 22:20)
### 1. JitVul_concept (ACL'25 vulnerability detection; mechanism evidence, not test-gen)
- Code `JitVul_concept/`, run on thinkbook. Arms base/concept/placebo/callee_code/ide; primary metric P-C (pair correct).
- **Result so far (874 pairs):** base 16.4%, concept 13.0%, placebo 13.0% (concept vs placebo p=1; both < base,
  p=0.036). The extra block makes the model flag more. 55% of pairs have an identical concept block for the
  vulnerable and patched sides (ignoring line numbers).
- Running: `run ide` (started 22:19) and `run "base callee_code"` (restarted because the base arm hung for
  3.5 h on its last ~10 calls: there is no per-call timeout. If it hangs again, `pkill -f "harness.py run"` and
  rerun; responses are cached).
- Logs: `JitVul_concept/out/run_all.log`, `out/run_ide.log`. When done: `./run.sh analyze`, then commit `out/`.

### 2. CoSIL_concept (ASE'25 fault localization; mechanism evidence)
- 4 arms (stock/concept/placebo/ide) on SWE-bench-Live, 225 post-2025-02 issues, launched about 19:10:
  `nohup setsid ./run.sh run all swebench_live > work/run_all_live.log`.
- Per-arm logs in `work/swebench_live/run_<arm>.log` (about 20/225 done each at 22:17; Vertex 429s slow it).
- When done: `./run.sh eval swebench_live && ./run.sh analyze swebench_live`, then commit `out/`.

### 3. ConceptCoder_placebo (does ConceptCoder's gain come from concept content? Kaggle T4)
- `ConceptCoder_placebo/README.md` and `RESULTS.md` (partial). k1 done: conceptcoder F1 55.5 / AUROC .855 vs
  placebo F1 0 / AUROC .637 (placebo collapses through the concept bottleneck).
- **k2 (regular ‖ regular_paperhead) was pushed 11:53 UTC, about 4.6 h.** Kaggle quota left about 6.7 h this week.
- Fetch it with the kaggle CLI (`~/.kaggle/access_token` is needed on this machine; it was on the Mac).
  Commands are in `student/KAGGLE_CLI.md` and the README. Then `python analyze.py out` and finish RESULTS.md.
- LoRA weights (`out/**/adapter_model.safetensors`) are gitignored and stay on the Mac.

## Next (the user's main line): CoverUp_concept (test-case generation)
- Base paper: **CoverUp** (FSE'25, github.com/plasma-umass/coverup, Apache-2.0). Its oracle is regression
  (tests must pass on the current code), so concepts only steer which uncovered lines/inputs to test.
- Arms:
  - coverup: stock, Gemini 2.5 Flash;
  - concept: C1-C8 facts for the uncovered lines;
  - concept_reason: facts + a per-concept testing recipe (the user's hypothesis: the model doesn't know how to
    reason from concepts);
  - placebo_reason: same recipe, facts from another segment;
  - ide: ruff warnings.
- Primary metric: **mutation score** (mutmut or cosmic-ray), plus CoverUp's coverage. K=3. Primary contrast
  concept_reason vs placebo_reason (Wilcoxon, paired by module).
- **Status: work in progress, the builder agent was stopped mid-way** (it had just started the first live test
  of the coverup arm on the `codetiming` package). Done so far: `cu_concept.py`, `run.sh`, `setup.sh`, data
  list and `.gitignore`. Still to do: smoke test of all 5 arms (2 packages × K=1), the mutation-tool step,
  `analyze.py`, `README.md` runbook; then the full run.
- Python: use `uv venv --python 3.11` (system python3 is 3.14). No tmux, so use `nohup setsid`. LLM-written
  tests must run without gcloud credentials in the environment.

## Warning
- **Never `git stash` or `git checkout` result files on thinkbook while runs are active.** Responses are written
  to tracked files (`JitVul_concept/out/responses/*.jsonl`); a stash at 22:25 wiped them. They were restored by
  merging from `stash@{0}` (still kept as a backup). The files are now uncommitted on thinkbook: commit them from
  there when the runs finish.
- JitVul: base is complete (879 pairs). As of 22:30 `run callee_code` and `run ide` are running in parallel.

## Abandoned / ignore
- `RegTest_concept/`: a self-designed study, cancelled at the user's request; not committed.
- `concept_annotator_py/functions.py` is committed and used by CoSIL and CoverUp.
