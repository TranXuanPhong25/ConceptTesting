# Held-out MBPP+ v7 adapter

This package runs the final dev v7 recipe on the 58 tasks frozen in
`out/heldout_mbpp/puts.json`. All tasks have split `heldout`, with no pilot or
design exclusions. Manual labels are read only by reporting: primary results
use all 58 PUTs, secondary results use the 12 labelled real bugs. The original
pipeline modules, `run_v4.py`, `vendor/`, and `EvalAndMitigate/` are unchanged.
**Existing module changes: none.**

Run from `/home/phong/dev/ConceptTester`. Set `V4_PYTHON` to the existing dev v4
venv interpreter. On this machine its path is:

```bash
export V4_PYTHON=/tmp/claude-1000/-home-phong-dev-ConceptTester/2dddac78-7845-4887-9c28-b6313bcf7c52/scratchpad/codex_v4/venv/bin/python
```

The v4 worker retains its exact dependency checks: hypothesis 6.169.0,
mutmut 3.8.0, coverage 7.16.2, libcst 1.9.0. `--python` overrides `V4_PYTHON`;
every v4 sandbox uses that interpreter, including gen-plain. The wrapper does
not choose a new model, endpoint, temperature, seed, gate, draw count or K.
LLM stages construct the original `llm_client.Client`, which reads
`QWEN_BASE_URL`, `QWEN_MODEL`, and optional `QWEN_API_KEY` as before. Configure
these privately for your endpoint; do not print them. Use the repository's
`source scripts/research_env.sh` when loading API credentials.

## Commands in order

Dataset build and tests are offline. The dataset has already been built and
verified; rebuilding is deterministic. No production mining or generation has
been run by this implementation task.

```bash
python3 -B -m trickcatcher_linefacts.heldout.dataset build
python3 -B -m unittest trickcatcher_linefacts.heldout.test_heldout -v

# GPU endpoint required: unchanged B5 mining + v4c domain strategy worker
"$V4_PYTHON" -B -m trickcatcher_linefacts.heldout.run mine

# CPU only: original facts.py --validity mined --precond-dir ...
"$V4_PYTHON" -B -m trickcatcher_linefacts.heldout.run facts

# CPU only: original spec_facts.worker, only tasks with empty code facts
"$V4_PYTHON" -B -m trickcatcher_linefacts.heldout.run specfacts

# CPU only: v7 all-task and v4 hybrid bundles, with original mutant_source
"$V4_PYTHON" -B -m trickcatcher_linefacts.heldout.run bundle

# GPU endpoint required: original seven-arm run_v4.run, fixed K=3
"$V4_PYTHON" -B -m trickcatcher_linefacts.heldout.run arms

# CPU only: original v4 evaluation workers and metrics
"$V4_PYTHON" -B -m trickcatcher_linefacts.heldout.run evaluate

# CPU only
"$V4_PYTHON" -B -m trickcatcher_linefacts.heldout.run oracle collect

# GPU endpoint required: original B1/B2/B3 prompts and settings
"$V4_PYTHON" -B -m trickcatcher_linefacts.heldout.run oracle llm

# CPU execution; GPU endpoint required for uncached B4 judge calls
"$V4_PYTHON" -B -m trickcatcher_linefacts.heldout.run oracle score
```

For an explicitly provisional CPU-only oracle score, use
`oracle score --no-llm`. This reuses cached judge responses if present, otherwise
omits B4 judge decisions; run the normal score later for the full result.
Do not treat that provisional score as the final `full` confirmation.
Default worker counts are 12 for facts/specfacts, 16 for mining/arms/oracle LLM,
and at most 12 execution workers plus 16 judge workers for oracle score.
`--workers` is available on each stage. There is deliberately no task subset or
K override on production commands.

## Artifacts

All paths below are relative to `trickcatcher_linefacts/out/heldout_mbpp/`:

| Stage | Outputs |
| --- | --- |
| dataset build | `he/humaneval_mbpp.jsonl`, `he/humaneval_mbpp_plus.jsonl`, `he/PUTs/HumanEval_<n>/put0.py`, `he/tasks.txt`, `he/tasks.json`, `he/manifest.json`, `he/verification/<n>/{job,result}.json` |
| mine | `precond_qwen7b_v4/<n>/`, `strategy_qwen7b_v4c/<n>/`, original prompts, responses, caches, verification and summaries |
| facts | `facts_v6/<n>.json` (original v3m schema/validity provenance); failures produce `<n>.err` and abort the stage |
| specfacts | `spec_facts_v7/<n>.{job.json,json}` for tasks without code facts |
| bundle | `tasks_v7_all.json`, `tasks_v7hyb_v4.json` |
| arms | `gen2_qwen7b_v7hyb_v4/{manifest.json,tasks.json,gen.jsonl,cache/,artifacts/}`; 58 × 7 × 3 = 1218 rows |
| evaluate | generation directory: `eval.jsonl`, `eval_jobs/`, `eval.metrics.json`, `report.txt` |
| oracle collect | `oracle_v7hyb/calls.json` |
| oracle llm | `oracle_v7hyb/{b1,ref,post}_responses.json`, `cache/` |
| oracle score | `oracle_v7hyb/exec/`, `judge_responses.json` when requested, `report.txt`, `metrics.json` |

The primary oracle comparison is concept-hybrid versus plain-hybrid under ref.
Secondary comparisons are concept versus plain, concept-hybrid versus
toolinput, and concept-hybrid versus placebo-hybrid. Reports include ref and
full for the full held-out set and separately for the real-bug set.
Released HumanEval dpp/tc programs are never looked up: their pools are empty
and their report columns are omitted explicitly.

## Adapter boundaries and preserved settings

`bindings.bound()` rebinds data paths and definition-time path defaults inside
a scoped context and restores them afterward. `run_v4.task_sources` reads the
normalized task list without the dev design filter; all bundles stay heldout.
`run_v4.safe_path` permits only dedicated paths under the held-out root and
outside its `he/` input directory. Original source roots stay unchanged so
source hashes, templates and sandbox scripts still identify the dev code.
Workers receive data as explicit filenames or payloads; they do not inherit
in-process rebinding. The v6 child command explicitly carries the normalized
HE/PUT paths, mined validity mode and held-out B5 directory.

MBPP ids are aliased to `HumanEval/<n>` solely for existing consumers that parse
numeric ids or construct HumanEval filenames; the plus rows and manifest also
retain `Mbpp/<n>`. The HumanEval stub uses the canonical signature and decoded
MBPP prompt, including its example. Canonical continuations close the stub
with `pass`, then include the complete original program (imports/helpers
included). Contracts are dedented/reindented under the same stub. PUT
normalization splices only the entry docstring, with an executable-AST equality
check; its own signature and all other source bytes stay unchanged. The
manifest records the source pass/path and original/normalized SHA256 values.

Base checks call the candidate once per contract-valid input and compare
canonical outputs with the selection worker's recursive numeric comparison:
`math.isclose(rel_tol=1e-6, abs_tol=atol or 1e-6)`, with matching list/tuple
types. Canonical errors are reported rather than discarded. Verification runs
`unshare -rn <python> -I -B` with a clean environment, a 600-second outer timeout,
3-second input calls and 20-second check calls. It scans plus inputs until the
first contract-valid, canonical-scored failure; recorded `plus_tested` is the
number scanned, not a full plus-set rescore. Failed tasks remain in the
manifest/task list, build exits unsuccessfully, and pipeline entry refuses the
dataset. The plus file additionally provides an evaluation-only loop check
compatible with `offline.plus_check_src`.

The recipe keeps B5 evidence_filter=False, mining seed `20261010 + task`,
temperature 0/top_p 1/max_tokens 4096; v6 facts retain seed 20261010, 400 fuzz
inputs, original ranking/gates/K=3. Spec facts keep LARGE/DUP/NONASCII/SPACE,
threshold 1000, deterministic transformations, B5 acceptance, and the 1000-char
witness-call cutoff. Arms retain `v4_prompts.seed`, seven arms, K=3, cached
shared round one, all retry rules, 100 round-two draws and per_fact=2.
Oracle B2 keeps ten Qwen programs and the SHA-checked TrickCatcher DPP prompt;
B1 has three samples and B3 five postconditions. Reference survivors must pass
the generated check, and emission still requires at least three survivors and
unanimous output. B4 retains the original prompts/seeds and decisions.

`worker.py` adapts only the AST used to extract trusted base pairs in the
original oracle worker: the new tolerant assertion representation is viewed
as an equality for pair extraction. Actual reference screening executes the
original tolerant check. Oracle execution, agreement and `decide()` logic are
unchanged. v4 evaluation reports run on temporary reporting copies with the
cohort mapped to dev (the original report only recognizes dev/pilot), then
relabel results; saved bundles/evaluation rows retain heldout. Oracle reports
reuse original counting/decision/sign-test rules, omitting unavailable dpp/tc
columns and applying reporting-only cohorts. No label enters a prompt or a
generation bundle.

The offline suite builds tasks 99/264 in `/tmp`, verifies provenance,
contract rejection and float tolerance, blocks original HumanEval data reads,
runs real facts/specfacts/bundle with synthetic mining fixtures, compares
bundle keys with the dev bundle, runs actual v4 evaluation, and scores ten
synthetic reference responses per task with no LLM. It deliberately empties
one test fixture's top3 to exercise v7 fallback. Tests patch Client construction
to fail if any LLM stage is accidentally entered. Scratch directories are
removed after the run. Production facts and mining outputs are never faked.
