# Held-out final runbook — v11_fair_vp

Prepared 2026-10-14; implementation/CPU checks only. No online run was started.
Run from `/home/phong/dev/ConceptTester`. Wait for the current v11_fair dev sanity
run to finish and review it before starting this sequence. Do not change hint
selection or tune on held-out outputs. Resume an interrupted stage with identical
settings/output; do not launch a second seed/cohort after seeing results.

Frozen pipeline: v11_fair + exactly the v7_vp class-method fix; all four fairness
flags true; v7 hint ranking; seven arms (`plain`, `concept`, `toolinput`, `gen-plain`,
`concept-hybrid`, `placebo-hybrid`, `plain-hybrid`); K=3; <=8 logical calls and
<=20 assertions/sample; real strict round 2; matched placebo; shared tolerant
scorer. Ref only: ten spec-only Qwen programs/task, base filtering, >=3 survivors
and unanimous outputs. No B1, postconditions, B4 judge, released DPP/TC pools, or
CPU `strict` reconstruction. Reference generation is a shared scoring cost,
outside generation caps. Witness-only uses the bundle witnesses directly, zero
generation calls, and the same ref programs (no expected-value LLM request).
TrickCatcher-full uses the registered per-task exception described below.

## Before the online run

Two dataset roots already exist; do not rebuild/select subsets:

- VibePass: `trickcatcher_linefacts/out/heldout_vibepass_real/he`, 66 PUTs,
  24 question clusters. Each public entry wraps `Solution().method(...)`.
- MBPP+ real-12: `trickcatcher_linefacts/out/heldout_mbpp_real12/he`, the exact
  cohort reported in RESULTS §11.32. Statistics cluster by task (12).

**Final protocol amendment 1 (PREREG, 2026-10-14 ~01:20):** tc_full_v2 retains
the paper's ten program variants + four input generators, generated once per task.
K=3 rows are seeded resamples of that one pool, not independent generations.
The call budget is per task: 14 <= 3 x 8 = 24; the <=20 assertion cap per sample
is unchanged. `final_run` fixes 10+4 and rejects reduced-allocation options.
It preserves the original templates, sampling parameters, generation/draw seeds,
repr input transport and pool multiplicities. Base filtering and voting use the
shared scorer and aligned crash/timeout accounting; scoring occurs separately.
One shared request ledger is partitioned across the three exported rows (5/5/4)
solely to count each request/token once. Mean calls/sample = 14/3 = 4.7; these
row charges do not represent independent sample budgets. Each row records the
shared generation/pool id and its resample seed/positions. The prior 4+4 dry
allocation is superseded and is not available as a production mode.

The production baseline settings are explicit: SymPrompt 8 path/call slots,
20 assertions; ACH 8 calls, 3 fault attempts, `--filter run`, 20 assertions;
CoverUp 8 calls/20 assertions; MuTAP 8 calls/20 assertions, max 32 pooled mutants,
max 7 base-surviving mutants. Syntax repair/retries consume the logical budget.
SymPrompt/ACH now export in generation order and reject budgets above the caps;
their historical CLI defaults remain 6 calls/10 assertions, so use these commands.
Native empty pools/no new assertions stay empty; no fallback output is invented.

Credentials and endpoint must already be provided privately in the environment.
Never echo them, use `set -x`, save an environment dump, or put a URL in a script.
The client consumes `QWEN_BASE_URL`; none of the commands below assigns its value.

```bash
cd /home/phong/dev/ConceptTester
set -euo pipefail
source scripts/research_env.sh >/dev/null
: "${QWEN_BASE_URL:?QWEN_BASE_URL must already be exported privately}"
unset LINEFACTS_FAIR_FLAGS LINEFACTS_DATASET
export PYTHONDONTWRITEBYTECODE=1
export QWEN_MODEL=qwen2.5-coder-7b-instruct
export V4_PYTHON="$(python3 -B -c 'import json; print(json.load(open("trickcatcher_linefacts/pipelines/v11_fair_vp/config.json"))["V4_PYTHON"])')"
export PYTHONPATH=/home/phong/dev/ConceptTester
RUN_PY=/home/phong/dev/ConceptTester/CoverUp_concept/.venv/bin/python
"$RUN_PY" -B -c 'from trickcatcher_linefacts.baselines.tc_full_v2.final_run import VARIANTS,GENERATORS,K,TASK_CALLS,TASK_BUDGET; assert (VARIANTS,GENERATORS,K,TASK_CALLS,TASK_BUDGET)==(10,4,3,14,24)'
"$RUN_PY" -B -c 'from trickcatcher_linefacts.pipelines.v11_fair_vp.paths import CONFIG,FAIR_FLAGS; assert all(CONFIG[k] is True for k in FAIR_FLAGS)'
PIPE=trickcatcher_linefacts.pipelines.v11_fair_vp
LOGROOT=/home/phong/dev/ConceptTester/trickcatcher_linefacts/out/runlogs_heldout_final
mkdir -p "$LOGROOT"

# Read-only/offline checks; no endpoint test is needed here.
"$RUN_PY" -B -m unittest "$PIPE.test_vp" "$PIPE.test_fair" \
  "$PIPE.test_heldout_support" "$PIPE.test_final_analysis" \
  trickcatcher_linefacts.baselines.tc_full_v2.test_final -q
"$RUN_PY" -B -c 'from trickcatcher_linefacts.pipelines.v11_fair_vp.v4_runtime import interpreter; assert interpreter().exists()'
"$V4_PYTHON" -B -c 'from trickcatcher_linefacts.pipelines.v11_fair_vp.v4_runtime import require_versions; from importlib.metadata import version; require_versions(); assert version("cyaron")=="0.7.0"'
# Freeze non-secret source hashes with the run; vendor and protected runs stay untouched.
sha256sum trickcatcher_linefacts/pipelines/v11_fair_vp/config.json \
  trickcatcher_linefacts/pipelines/v11_fair_vp/run_v4.py \
  trickcatcher_linefacts/pipelines/v11_fair_vp/facts.py \
  trickcatcher_linefacts/pipelines/v11_fair_vp/tracer.py \
  trickcatcher_linefacts/pipelines/v11_fair_vp/scorer.py \
  trickcatcher_linefacts/pipelines/v11_fair_vp/{heldout_support,final_analysis}.py \
  trickcatcher_linefacts/baselines/{symprompt,ach}/run.py \
  trickcatcher_linefacts/baselines/tc_full_v2/{final_run,final_worker}.py \
  > "$LOGROOT/frozen_sources.sha256"
```

## Execute VibePass, then MBPP+ real-12, once each

The helper derives each output path from this copy's VERSION and dataset hash.
Existing offline readiness artifacts are reused. Production generation paths
must be fresh for the first invocation. On an interrupted run, remove only the
freshness check after confirming the same manifests/settings; every runner
resumes the existing cohort rather than creating another run.

```bash
run_heldout_once() {
  local dataset_root="$1" dataset_label="$2" cluster_unit="$3"
  local dataout bundle generation oracle baseline_root logdir
  dataout="$("$RUN_PY" -B -c 'import sys; from trickcatcher_linefacts.pipelines.v11_fair_vp import paths; paths.set_dataset(sys.argv[1]); print(paths.DATA_OUT)' "$dataset_root")"
  bundle="$dataout/baseline_tasks.json"
  generation="$dataout/generation"
  oracle="$dataout/oracle"
  baseline_root="$dataout/baselines"
  logdir="$LOGROOT/$dataset_label"
  mkdir -p "$logdir"
  test ! -e "$generation/gen.jsonl"
  for name in symprompt ach coverup mutap tc_full_v2; do
    test ! -e "$baseline_root/$name/gen.jsonl"
  done

  # GPU: real B5 preconditions (<=3 requests) + domain strategy (<=2).
  # MBPP+ can reuse the verified original mining; never copy old generation rows.
  if [ "$dataset_label" = mbpp_real12 ]; then
    "$RUN_PY" -B -m "$PIPE.run" mine --dataset "$dataset_root" --online --workers 4 \
      --reuse-from trickcatcher_linefacts/out/heldout_mbpp_real12 \
      > "$logdir/01_mine.log" 2>&1
  else
    "$RUN_PY" -B -m "$PIPE.run" mine --dataset "$dataset_root" --online --workers 4 \
      > "$logdir/01_mine.log" 2>&1
  fi

  # CPU: mined-validity facts; deterministic specfacts; all/hybrid bundles.
  for stage in facts specfacts bundle; do
    "$RUN_PY" -B -m "$PIPE.run" "$stage" --dataset "$dataset_root" --workers 4 \
      > "$logdir/02_$stage.log" 2>&1
  done
  # Only visible fields + numeric atol/question id for all baseline adapters.
  "$RUN_PY" -B -m "$PIPE.heldout_support" visible --dataset "$dataset_root" \
    > "$logdir/03_visible.log" 2>&1

  # GPU: main seven-arm cohort, strict generation for real, K=3.
  "$RUN_PY" -B -m "$PIPE.run" arms --dataset "$dataset_root" --online --k 3 --workers 4 \
    > "$logdir/04_arms.log" 2>&1

  # GPU: four paper baselines, sequentially, identical ceilings.
  "$RUN_PY" -B -m trickcatcher_linefacts.baselines.symprompt.run \
    --tasks "$bundle" --out "$baseline_root/symprompt" --online --k 3 \
    --llm-budget 8 --max-paths 8 --max-tests 20 --workers 4 \
    > "$logdir/05_symprompt.log" 2>&1
  "$RUN_PY" -B -m trickcatcher_linefacts.baselines.ach.run \
    --tasks "$bundle" --out "$baseline_root/ach" --online --k 3 \
    --llm-budget 8 --mutants 3 --max-tests 20 --filter run --workers 4 --python "$RUN_PY" \
    > "$logdir/06_ach.log" 2>&1
  "$RUN_PY" -B -m trickcatcher_linefacts.baselines.coverup.run \
    --tasks "$bundle" --out "$baseline_root/coverup" --online --k 3 \
    --llm-budget 8 --max-tests 20 --workers 4 \
    > "$logdir/07_coverup.log" 2>&1
  "$RUN_PY" -B -m trickcatcher_linefacts.baselines.mutap.run \
    --tasks "$bundle" --out "$baseline_root/mutap" --online --k 3 \
    --llm-budget 8 --max-tests 20 --max-mutants 32 --max-surviving-mutants 7 --workers 4 \
    > "$logdir/08_mutap.log" 2>&1
  # GPU: 10 variants + 4 generators ONCE per task; CPU: K=3 shared-pool resamples.
  # Amendment 1: <=24 calls/task and <=20 assertions/sample. No reduced mode.
  "$RUN_PY" -B -m trickcatcher_linefacts.baselines.tc_full_v2.final_run \
    --tasks "$bundle" --out "$baseline_root/tc_full_v2" --online --k 3 --workers 4 \
    --python "$V4_PYTHON" \
    > "$logdir/09_tc_full_v2.log" 2>&1

  # CPU: o0 observations. GPU: one shared ten-program ref pool for every PUT,
  # including tasks whose generated assertion list is empty.
  "$RUN_PY" -B -m "$PIPE.run" evaluate --dataset "$dataset_root" \
    > "$logdir/10_evaluate.log" 2>&1
  "$RUN_PY" -B -m "$PIPE.heldout_support" references --dataset "$dataset_root" \
    --online --workers 4 > "$logdir/11_ref_llm.log" 2>&1
  # CPU only, --online deliberately absent; no judge/post/B1 requests.
  "$RUN_PY" -B -m "$PIPE.heldout_support" score --dataset "$dataset_root" \
    --run "$generation" --out "$oracle" --workers 4 --python "$V4_PYTHON" \
    > "$logdir/12_score_main.log" 2>&1
  for name in symprompt ach coverup mutap tc_full_v2; do
    "$RUN_PY" -B -m "$PIPE.heldout_support" score --dataset "$dataset_root" \
      --run "$baseline_root/$name" --out "$baseline_root/$name/oracle" \
      --ref-from "$oracle" --workers 4 --python "$V4_PYTHON" \
      > "$logdir/13_score_$name.log" 2>&1
  done
  # CPU only: witness-only, ref metrics, paired tests, seeded 100-draw RANDOM
  # equal-count subsets. VibePass clusters by question; MBPP clusters by task.
  "$V4_PYTHON" -B -m "$PIPE.final_analysis" --run "$generation" --oracle "$oracle" \
    --baselines "$baseline_root/symprompt" "$baseline_root/ach" "$baseline_root/coverup" \
      "$baseline_root/mutap" "$baseline_root/tc_full_v2" \
    --dataset "$dataset_label" --dataset-root "$dataset_root" --clusters "$cluster_unit" \
    --split heldout --workers 4 --output "$logdir/final_report.md" \
    > "$logdir/14_analysis.log" 2>&1
}
run_heldout_once trickcatcher_linefacts/out/heldout_vibepass_real/he vibepass question
run_heldout_once trickcatcher_linefacts/out/heldout_mbpp_real12/he mbpp_real12 task
```

Use a private terminal/session manager or a detached process with PID tracking for
this long sequence. Preserve the exported environment; do not serialize it.
All logs stay under `out/runlogs_heldout_final/`, all production artifacts under
`pipelines/v11_fair_vp/out/<dataset-hash>/`. No path in the ongoing v11_fair/v12_rel
runs is read for cache reuse or written by these commands.

## Call budget estimates and expected outputs

These are logical-request estimates, not promises of transport counts. Cache
hits count logically; shared round-one requests are charged to both hybrid and
round-one arms. The inherited pipeline client may retry transport failures up to
8 times (9 attempts/request); physical attempts and cache hits are logged
separately. CoverUp/MuTAP have no transport retries. Token totals come from the
actual client manifests/rows; never infer effectiveness from the fake dry run.

| Stage | Per-task bound (K=3 where applicable) | VibePass 66 | MBPP+ 12 |
| --- | ---: | ---: | ---: |
| B5 mine | <=3 | <=198 | 0 with existing cache; <=36 fresh |
| Domain strategy mine | <=2 | <=132 | 0 with existing cache; <=24 fresh |
| facts/specfacts/bundle/visible | 0 | 0 | 0 |
| Seven arms, universal cap | <=7×3×8=168 | <=11,088 | <=2,016 |
| SymPrompt | <=3×8=24 | <=1,584 | <=288 |
| ACH (run filter) | <=24 | <=1,584 | <=288 |
| CoverUp | <=24 | <=1,584 | <=288 |
| MuTAP (<=7 survivors) | <=24 | <=1,584 | <=288 |
| tc_full_v2 shared 10+4 (amendment 1) | exactly 14, budget <=24/task | 924 | 168 |
| Shared spec-only ref pool | exactly 10 | 660 | 120 |
| evaluate/score/witness-only/final analysis | 0 | 0 | 0 |
| Conservative total (MBPP cached mining) | — | <=19,338 | <=3,456 |

The pipeline's actual structure is tighter than the universal seven-arm bound:
plain/concept/toolinput <=1 call/sample; gen-plain <=3 (two strategy attempts and
one expected-value request); each hybrid <=8. Thus <=30 logical calls per
(task,sample), before shared-cache savings. Strict expected-value requests are
skipped when no verified new input survives. The conservative totals above use
the registered ceilings and the fixed 14-call shared TC pool. With the tighter
90-call/task seven-arm structural bound, totals are <=14,190 VibePass and
<=2,520 MBPP+ (cached mining), before other cache savings. A fresh MBPP+ mine
adds at most 60 requests. Combined conservative bound with cached MBPP+ mining:
<=22,794 logical requests, including <=780 shared ref-generation requests.

Main generation must contain 66×7×3=1,386 / 12×7×3=252 rows; each baseline must
contain 198 / 36 rows, including empty samples. Score with `ref_metrics.json` /
`final_report.{md,json}`: D_I, D_IO, detecting samples and bug-report precision;
false alarms share the failing-on-PUT denominator. Legacy `report.txt` can show
other empty/derived oracle columns; they are not separate ref-only results.
Primary comparisons use D_IO/ref and paired question/task clusters. Include
plain-hybrid, placebo-hybrid, toolinput and witness-only in every report. No full
oracle claim is made without the separate registered stages.

## Offline readiness evidence and remaining work

Reproduce CPU checks from the repository root without endpoint credentials:

```bash
cd /home/phong/dev/ConceptTester
export PYTHONDONTWRITEBYTECODE=1
unset LINEFACTS_FAIR_FLAGS LINEFACTS_DATASET
RUN_PY=/home/phong/dev/ConceptTester/CoverUp_concept/.venv/bin/python
PIPE=trickcatcher_linefacts.pipelines.v11_fair_vp
"$RUN_PY" -B -m unittest "$PIPE.test_vp" "$PIPE.test_fair" \
  "$PIPE.test_heldout_support" "$PIPE.test_final_analysis" \
  trickcatcher_linefacts.baselines.tc_full_v2.test_final -q
"$RUN_PY" -B -m unittest trickcatcher_linefacts.baselines.symprompt.test_symprompt \
  trickcatcher_linefacts.baselines.ach.test_ach -q
"$RUN_PY" -B -m pytest trickcatcher_linefacts/baselines/tests/test_baselines.py \
  -q -p no:cacheprovider
"$RUN_PY" -B -m "$PIPE.test_equivalence" --checks a,b --classification-timeout 30
"$RUN_PY" -B -m trickcatcher_linefacts.baselines.tests.heldout_dry_run \
  --out trickcatcher_linefacts/baselines/tests/heldout_dry_amendment1 --include-tc
```

Dry checks inspect/resume their exact scratch destination. To exercise changed
adapter code from scratch, use a new `--out` below `baselines/tests/`; never
promote fake rows or responses into production generation/oracle directories.

- `test_vp` + inherited `test_fair`: 23 CPU tests passed. HumanEval bundle check a:
  all/hybrid bundles equal v11_fair on 133 tasks, all frozen flags on. Check b
  passed 2,793 first request keys and equal 16-row paired cache replay,
  stopping at the same two genuine missing strict request keys; see the copy's
  `EQUIVALENCE.md` and ignored `out/humaneval/equivalence/equivalence.json`.
- VibePass `mine` stopped at the first real offline CacheMiss (no response created).
  `facts/specfacts/bundle` with mined validity are blocked by that missing mining.
  Supplemental embedded-contract `vp_check` (not final facts): 66/66, zero errors,
  all 66 have class non-mutant facts. Counts: BOUND 432, DECISION 682, DU 540,
  LOOP 197, LOOP-MAX 234, MUTANT 706, MUTANT-X 160, NUM 204, OUTCOME 324,
  OUTPUT 59, REL 271, SHAPE 369, STMT 172 (170 class + 2 other). Top-3:
  MUTANT 57, MUTANT-X 17, OUTCOME 40, STMT 26, BOUND 11, NUM 11, DU 7.
- MBPP+ cached mine/facts/specfacts/bundle all completed offline (12 tasks,
  2 tasks needed specfacts); no cached generation/evaluation row was adopted.
- Five adapters rerun after amendment 1: 3 VibePass PUTs (3/103/120) + 3 MBPP+
  PUTs (93/99/126), K=3, 90 rows, all within their registered caps.
  `baselines/tests/heldout_dry_amendment1/summary.json` is the current tracked
  record; other scratch files are ignored. TC has exactly 42 scripted logical
  requests/set (14/task), one shared generation/pool per PUT, and nine resample
  rows/set. The earlier `heldout_dry/` summary is archived reduced-pool adapter
  evidence and is superseded. All fake/scripted outputs
  are confined to the baseline dry-run directory.
- Baseline suites: 22 common pytest tests, 24 canonical SymPrompt/ACH unittest
  tests, 7 tc_full_v2 vote/shared-pool tests, and 2 held-out scoring adapter tests
  passed. The copied final analysis passes 13 tests, including question clusters,
  missing metadata, shared refs, read-only sources, random subsets, deterministic
  hash-seeded execution and JSON-to-Markdown rendering. Canonical unittest module names matter:
  collecting those two unittest files alongside the common pytest directory
  imports two package aliases and breaks their fake-client monkeypatch.
- Remaining GPU work: VibePass mining; seven arms on both sets; all five baseline
  generations; shared refs. Facts, specfacts, bundles, filtering/execution,
  scoring and final analysis run on CPU. Start only after dev sanity completes
  and is reviewed. The TC pool decision is resolved by registered amendment 1;
  no configuration decision remains open. Genuine VibePass mining responses
  are still absent, so its final mined facts cannot be prepared offline.
  This task edited neither PREREG
  nor any protected pipeline/run/vendor/Kaggle path and did not commit or push.
