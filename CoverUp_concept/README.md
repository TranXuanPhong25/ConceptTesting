# CoverUp + concepts (coverup / concept / concept_reason / placebo_reason / ide)

Paper: *CoverUp: Effective High Coverage Test Generation for Python* (FSE 2025), code
<https://github.com/plasma-umass/coverup> (Apache-2.0), pinned at **`d9ca25b9`** (v0.6.3) and cloned by `setup.sh`
into `vendor/coverup` (gitignored, never edited). Benchmark: the authors' CodaMosa suite
(`plasma-umass/codamosa@17a4c2a2`, sparse checkout of `replication/test-apps`), the 58-module subset in
`data/subset.csv` (rows copied verbatim from the authors' `cm_modules.csv`, 12 packages).

**Question.** CoverUp's oracle is regression (a test is kept only if it passes on the current code), so concepts
cannot copy a bug into the oracle. Can C1-C8 facts (`concept_annotator_py.functions`) steer *which inputs and paths*
the LLM tests, and does that make the kept tests better at catching faults (mutation score) than a placebo with the
same testing recipe but facts from elsewhere? The user's hypothesis: facts alone don't help because the model doesn't
know how to reason from them; a per-concept recipe should.

## Arms (differ only in the first prompt of each segment)

`GptV2Prompter.initial_prompt` is subclassed (registered as `cu-<arm>` in `coverup.coverup.prompter_registry`) and one
block is appended after the code excerpt. Error and missing-coverage follow-ups are the authors'.

| arm | appended block |
|---|---|
| `coverup` | none (stock gpt-v2 prompt) |
| `concept` | facts of the segment's functions that still miss coverage (≤12, lines of interest first) |
| `concept_reason` | the facts + a fixed one-line testing recipe per concept present (`RECIPE` in `cu_concept.py`) |
| `placebo_reason` | facts of another function/class of the same package (closest fact count, seeded), lines remapped into the segment, recipe rendered from those facts |
| `ide` | ruff warnings in the segment (same rule set as `CoSIL_concept`) |

A segment with nothing to add gets the stock prompt in every arm (`prompts.jsonl` in each workspace records every
block, donor and full prompt).

Arm-neutral settings: the authors' gpt4o-v2 configuration (`coverup-eval/config/gpt4o-v2.sh` + `run_coverup.sh`):
`--max-attempts 3 --isolate-tests --repeat-tests 5`, pytest `--rootdir . -c /dev/null`, one CoverUp pass per package,
final coverage with slipcover + `--cleanslate`. Model `vertex_ai/gemini-2.5-flash`, thinking budget 0, `seed` = run
seed, `max_tokens` 8192 (`CU_MAX_TOKENS`; Gemini occasionally loops to 65 536 output tokens, which then overflows the
conversation and 429s forever; normal replies are under 4k, p99 3190; the cap was added during seed 1 of `main` after
9 such calls spread over all arms, so earlier packages ran uncapped), every call logged to `out/<run>/ledger.jsonl`, global cap `CU_MAX_USD` (default 40). Differences from the
authors: no `--install-missing-modules` (one shared venv with the union of the packages' pinned deps; `./run.sh bench`
checks all 58 modules import), Gemini instead of gpt-4o.

**Sandbox.** The ADC JSON is read into memory, then secret-looking env vars are removed and `HOME` points to an empty
dir before CoverUp spawns pytest, so LLM-written tests never see Google credentials. `evaluate.py` runs mutmut the same
way.

## Metrics (`evaluate.py`)

- **Mutation score (primary).** mutmut 3.8 mutates the pristine benchmark source of the subset modules only
  (identical mutants for all arms/seeds) and runs each workspace's `coverup-tests/`. Test files that fail together
  on unmutated code (CoverUp checks them in isolation) are moved aside first (counted as `dropped test files`).
  Score = killed / all mutants of the module.
- Coverage (lines + branches, the paper's metric) per module from `final.json`.
- Concept sites: coverage of lines carrying a fact, and kill rate of mutants on those lines.
- Cost per arm from the ledger.
- Stats: per module mean over seeds, Wilcoxon signed-rank paired by module. **Primary contrast
  `concept_reason` vs `placebo_reason` on mutation score**; also each arm vs `coverup` and `concept_reason` vs
  `concept`.

## Runbook

```
./run.sh setup                       # vendor + .venv (uv, py3.11) + selftest
./run.sh bench                       # 58/58 modules import -> out/bench.json
./run.sh smoke                       # codetiming + sty, 5 arms, seed 1, mutate, analyze (CU_RUN=smoke_<arch>)
nohup setsid ./run.sh run all --seed 1 > work/main/run_all.s1.log 2>&1 &   # then --seed 2, --seed 3
./run.sh mutate all                  # every finished workspace, resumable (MUTMUT_JOBS=cores)
./run.sh analyze                     # out/main/{summary.md,metrics.json,per_module.jsonl}
```

Every step resumes: `gen` skips workspaces with `done.json` (CoverUp's own checkpoint resumes a half-done package),
`mutate` skips workspaces with `mut_result.json`. Budget stop exits with rc 3.

Python: `uv venv --python 3.11` (system python is 3.14). Runs fine on arm64 macOS and x86_64 Linux.
