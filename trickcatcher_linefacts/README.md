# trickcatcher_linefacts — line-level gap facts as concepts for LLM test generation

Data: TrickCatcher's EvalPlus PUTs (<https://github.com/RinCloud/TrickCatcher>, commit `a0d285a`). These are
LLM-written HumanEval solutions that pass HumanEval and fail HumanEval+. The vendored copy is gitignored; fetch it with:

```bash
git clone --filter=blob:none --sparse https://github.com/RinCloud/TrickCatcher vendor/TrickCatcher
git -C vendor/TrickCatcher checkout a0d285a && git -C vendor/TrickCatcher sparse-checkout set Datasets/EvalPlus/PUTs
```

Design, arms and metrics are in `PREREG.md`; the course mapping and concrete dev examples are in `VOCAB.md`.
Vocabulary v3 was developed on the fixed even/odd DEV split. Freeze the generator and gates before the
single pilot confirmation. Pilot tasks 108, 116 and 131 have docstring-example failures (`doc_fail`) and
will be reported separately in the pilot analysis. These flags stay outside all prompts.

V3 uses course terms: C1 statement, C2 branch, C3 sub-condition coverage, boundary values, input/output
equivalence classes, decision tables, loop coverage, def-use pairs and mutation testing. Qualified
OUTCOME-q facts are removed. Concept and placebo prompts share the same neutral terminology sentence;
coverage retains its generic hint; empty concept/placebo/toolinput sections match plain.

The fixed core pool is reached OUTCOME, STMT, MUTANT, BOUND and NUM. MUTANT-X, LOOP, LOOP-MAX, OUTPUT,
DU, REL, DECISION and SHAPE have separate dev gates. A candidate passes only if BOTH even/odd folds have
fact-level mean PF above matched base and per-task better > worse among tasks with scored reached facts.
Zero-hit facts have undefined PF; zero-fail tasks are excluded from development evaluation. Gate results
are recorded in `VOCAB.md`. Failed slots remain in fact JSON and never enter the concept/placebo display pool.
Passing MUTANT-X joins MUTANT; other passing slots follow NUM in the fixed order above. SHAPE stays out
unless it passes. All choices are development-derived; these folds are robustness checks.

Ranking retains v2's short-exit-guard blocks, one shown fact per block, boundary mutants last, seeded ties
(`random.Random(20261010 + task_id)`), G′ enabled, and K=3. K=5 is a sensitivity analysis. G′ forces the
base-seen guard outcome on reaching fuzz executions and demotes same/necessary guards; header mutants
are exempt. Fuzz uses at most 400 inputs, reserving 100 for seeded equal/order/prefix/length relations.
v3c requires EvalPlus v0.1.10 contract-valid fuzz evidence, with 2000 total draws and at most 500 draws
for the relation share; base tests are taken as given. `--validity none` reproduces the old v3f behaviour.
Extended mutations preserve the original 80-point sample and add a separate 80-point sample. Surviving
mutants with no fuzz distinction are dropped as likely equivalent. Plain PUT comparisons prevent tracing
work from creating a false mutant distinction.

Loop counts are recorded for each dynamic loop execution, including nested loops and early exits.
LOOP probes 0/1/2; LOOP-MAX probes exceeding the largest count seen in base. OUTPUT applies numeric and
structural classes to successful top-level returns. DU records bounded dynamic local def-use pairs,
including parameter definitions at entry and c-use/p-use; comprehension-local DU is outside this version.
DECISION probes at most 32 non-nested same-function condition pairs evaluated in one call. A pair may
co-occur at different loop iterations within that call. These facts report observed behaviour, with no
claim of complete coverage or input validity beyond the existing tests/fuzz evidence.

| File | Role |
|---|---|
| `tracer.py` | AST cells, loop execution counts, local reaching definitions, shared `fact_hit`, fixed step budgets |
| `facts.py` | method-visible v3 generation, fuzz confirmation, gates frozen as constants, ranking, placebo, docstring pre-check |
| `run_facts.sh` | per-task generation under `unshare -rn python3 -I` |
| `prompts.py` | five prompt arms; plain has no extra section; concept/placebo share course terminology |
| `offline.py` | evaluation-only HumanEval+ labels/reach; pilot/design excluded before worker launch and result opening |
| `evaluate.py` | sandboxed assertion scoring, shared v3 reach logic, five arms and paired comparisons |
| `VOCAB.md` | course/tool provenance, templates, dev examples and gate numbers |
| `human_eval/` | 30 seeded DEV shown facts, rating CSV, Vietnamese instructions and sandboxed literal-call checker |
| `generate.py` | fixed v3 pilot bundle, local export, optional paid Gemini runner |

Regenerate v3c for all 133 non-design tasks, preserving all older outputs and saved pilot material:

```bash
OUT=trickcatcher_linefacts/out/facts_v3c NON_DESIGN=1 VALIDITY=evalplus \
  bash trickcatcher_linefacts/run_facts.sh 12
OFFLINE_OUT=trickcatcher_linefacts/out/offline_v3c OFFLINE_SKIP_PILOT=1 \
  python3 -B trickcatcher_linefacts/offline.py trickcatcher_linefacts/out/facts_v3c
python3 -B -m trickcatcher_linefacts.run_gen --bundle-only
```

Every PUT execution runs under `unshare -rn python3 -I`. Offline batches and workers reject all 20 fixed
pilot ids and the six design ids; reports exclude their filenames before opening results. Method-visible
fact generation may include all 139 tasks. `OFFLINE_TASKS='2 3 4'` limits a dev batch; exclusions still apply.
Fact files include `rank_version="v3"`, `rank_k`, `g_prime`, `gated_slots`, `doc_fail`, and fact `tier`/`block`.
v3c adds `facts_version="v3c"` and per-task `fuzz_validity` statistics. The gen runner defaults to
`out/tasks_v3c_all.json`, records the fact version in its manifest, and is not started by `--bundle-only`.
Extended mutants retain `kind="MUTANT"` with `extended=true`; `slot()` exposes MUTANT-X separately for the
gate and counts. Only a passing aggregate MUTANT-X gate lets them join the MUTANT round-robin slot.

The final v3 freeze and one-time offline pilot confirmation are complete; see `PREREG.md` for the freeze record.
`out/pilot_tasks.json` retains its original fixed ids and v1 prompt material. `out/pilot_tasks_v3.json` rebuilds
those same 20 tasks from frozen `out/facts_v3f`. Empty-top3 tasks 77 and 151 remain in the pilot; their
concept/placebo/toolinput prompts match plain. doc_fail is stored in bundles and never added to prompts.

## Frozen v3 gate decisions

Passing candidates: MUTANT-X, DU. Failed candidates: LOOP, LOOP-MAX, OUTPUT, REL, DECISION, SHAPE.
Display round-robin: OUTCOME, STMT, MUTANT, BOUND, NUM, DU. K=3; G′ stays enabled. Full fold numbers are in `VOCAB.md`.

## Kaggle Qwen pilot (prepare locally, run after review)

This workflow reuses [student/KAGGLE_CLI.md](../student/KAGGLE_CLI.md), the T4/private/container metadata in
[ConceptCoder_placebo/kernels/k1/kernel-metadata.json](../ConceptCoder_placebo/kernels/k1/kernel-metadata.json),
and the recursive mount discovery / Hugging Face snapshot / output-log patterns in
[run.py](../ConceptCoder_placebo/kernels/k1/run.py) and [kaggle_run.py](../ConceptCoder_placebo/kaggle_run.py).
The kernel metadata sets `machine_shape: NvidiaTeslaT4`; the CLI accelerator flag was ignored in prior runs.
Wait for the prompt dataset to be **ready** before pushing. Dataset creation is private by default; use the
commands below without `--public`. The export includes only system/user prompts, without evaluation labels.

From the repository root, first build and inspect the local inputs:

```bash
python3 -B -m trickcatcher_linefacts.generate bundle
python3 -B -m trickcatcher_linefacts.generate export --k 3
python3 -B -m trickcatcher_linefacts.generate prompts --tasks trickcatcher_linefacts/out/pilot_tasks_v3.json
```

After review, the main session can run these commands (not executed during preparation):

```bash
.venv/bin/kaggle datasets create -p trickcatcher_linefacts/kaggle/data
# If the dataset already exists, use this instead of create:
.venv/bin/kaggle datasets version -p trickcatcher_linefacts/kaggle/data -m "Frozen v3f pilot, five arms, K=3"
.venv/bin/kaggle datasets status xunphongtrn/conceptester-linefacts-prompts
# Continue only after status says ready:
.venv/bin/kaggle kernels push -p trickcatcher_linefacts/kaggle
.venv/bin/kaggle kernels status xunphongtrn/concepttester-linefacts-qwen-7b-pilot
# After kernel status says complete:
.venv/bin/kaggle kernels output xunphongtrn/concepttester-linefacts-qwen-7b-pilot -p trickcatcher_linefacts/out/kaggle_qwen7b
cp trickcatcher_linefacts/out/kaggle_qwen7b/gen_qwen7b.jsonl trickcatcher_linefacts/out/gen_qwen7b.jsonl
python3 -B trickcatcher_linefacts/evaluate.py \
  --tasks trickcatcher_linefacts/out/pilot_tasks_v3.json \
  --gen trickcatcher_linefacts/out/gen_qwen7b.jsonl \
  --eval trickcatcher_linefacts/out/eval_qwen7b.jsonl
python3 -B trickcatcher_linefacts/evaluate.py report \
  --tasks trickcatcher_linefacts/out/pilot_tasks_v3.json \
  --eval trickcatcher_linefacts/out/eval_qwen7b.jsonl
```

The kernel installs `vllm==0.7.3`, `transformers==4.48.2`, `tokenizers>=0.21,<0.22` and `accelerate==1.6.0` — the
pins proven on this account by the notebook `xunphongtrn/qwen2-5-coder-7b-vllm-serve` (newer transformers breaks
vllm 0.7.3's Qwen2 tokenizer caching) — uninstalls torchao, then reinstalls `protobuf>=5.29.5,<6` because the vLLM
install downgrades protobuf to 4.x and Kaggle's preinstalled code then fails with `cannot import name
'runtime_version'` (first run, 2026-10-10: vllm 0.8.4 pins, all 300 rows failed this way). V0 + XFormers for T4,
float16, all visible GPUs for tensor parallelism (T4 x2 → 2), context 8192, one batched vLLM call. If vLLM installation/import fails,
transformers uses float16 with automatic device placement, per-row seeded sampling, and splits failed batches.

`/kaggle/working/gen_qwen7b.jsonl` contains task/arm/sample/model/text plus seed, prompt hash, n_in/n_out and
optional error. `/kaggle/working/run_info.json` and the `THROUGHPUT` log line record model-load time, generation
time, GPU/library versions, sampling, token totals, output tokens/s and total tokens/s. Timed generation calls
include fallback retries; token totals count successful new requests, excluding resumed rows. Failed rows have
empty text and are retried on resume. Matching successful rows in the working output are retained atomically;
to resume in a fresh Kaggle session, mount the previous output and set `QWEN_RESUME` to its gen_qwen7b.jsonl path.
Inspect error counts before interpreting detection/delivery. No PUT execution or evaluation occurs in the kernel.

The evaluator exposes `--tasks`, `--gen`, `--eval` for separate runs and keeps its original Gemini defaults.
Qwen evaluation jobs live beside `eval_qwen7b.jsonl` in `eval_qwen7b_jobs/`; worker failures stop before replacing
the evaluation output. Gemini is optional later and requires separate authorization for paid API use.


### Full TrickCatcher arm with Qwen

`python3 -B -m trickcatcher_linefacts.tc_full gen` generates 10 PUT-guided variants
and 4 generators per non-design task using the hash-checked original prompts.
`python3 -B -m trickcatcher_linefacts.tc_full run --python "$V4_PYTHON"` is CPU-only:
base filtering, 400-input pooling, K=3 seeded 100-input samples, Algorithm 1 and
canonical/contract scoring. Results use the existing tasks.json/eval.jsonl schema
under out/tcfull_qwen7b, with paper_metrics.json, task_summary.json and report.json.
RQ2 uses `tc_full rq2 --stage gen` then `tc_full rq2 --stage run --python "$V4_PYTHON"`
in out/tcfull_qwen7b_rq2 (canonical PUTs, K=1). Only gen stages contact QWEN_BASE_URL.
Generation and CPU artifacts resume; changed code/settings require a fresh --out.
See PREREG's "tc-full (TrickCatcher re-run with Qwen)" for seeds, tie handling,
artifact-weighted metrics, operational bounds and the approved method. Use
`--ids 2,3,4,157 --out /tmp/...` only for canned smoke; full runs default to 133
non-design tasks. Main and RQ2 require 1862 calls each, 3724 total, without retries.
